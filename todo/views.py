from datetime import timedelta, date

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Case, F, IntegerField, Value, When
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from planner.models import PlannerItem

from .forms import TaskForm
from .models import Task


def _todo_counts(user, today=None):
    if today is None:
        today = date.today()
    base_qs = Task.objects.filter(owner=user)
    return {
        "open": base_qs.filter(status=Task.Status.OPEN).count(),
        "in_progress": base_qs.filter(status=Task.Status.IN_PROGRESS).count(),
        "done": base_qs.filter(status=Task.Status.DONE).count(),
        "overdue": base_qs.exclude(status=Task.Status.DONE).filter(due_date__lt=today).count(),
        "today": base_qs.exclude(status=Task.Status.DONE).filter(due_date=today).count(),
    }


@login_required
def dashboard(request):
    user = request.user
    today = date.today()
    task_rows = (
        Task.objects.filter(owner=user)
        .select_related("project", "category")
        .annotate(
            status_rank=Case(
                When(status=Task.Status.OPEN, then=Value(0)),
                When(status=Task.Status.IN_PROGRESS, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("status_rank", F("due_date").asc(nulls_last=True), F("due_time").asc(nulls_last=True), "-created_at")[:80]
    )
    counts = _todo_counts(user, today=today)
    next_week = today + timedelta(days=7)
    planner_upcoming = (
        PlannerItem.objects.filter(owner=user, status=PlannerItem.Status.PLANNED)
        .order_by("due_date", "created_at")[:5]
    )
    planner_counts = {
        "planned": PlannerItem.objects.filter(owner=user, status=PlannerItem.Status.PLANNED).count(),
        "due_soon": PlannerItem.objects.filter(
            owner=user, status=PlannerItem.Status.PLANNED, due_date__range=(today, next_week)
        ).count(),
    }
    return render(
        request,
        "todo/dashboard.html",
        {
            "task_rows": task_rows,
            "counts": counts,
            "today": today,
            "planner_upcoming": planner_upcoming,
            "planner_counts": planner_counts,
        },
    )


@login_required
def add_task(request):
    if request.method == "POST":
        form = TaskForm(request.POST, owner=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.owner = request.user
            task.save()
            return redirect("/todo/")
    else:
        form = TaskForm(owner=request.user)
    return render(request, "todo/add_task.html", {"form": form})


@login_required
def remove_task(request):
    task_id = request.GET.get("id")
    task = None
    if task_id:
        task = get_object_or_404(Task, id=task_id, owner=request.user)
        if request.method == "POST":
            task.delete()
            return redirect("/todo/")
    tasks = Task.objects.filter(owner=request.user).order_by("-created_at")[:20]
    return render(request, "todo/remove_task.html", {"task": task, "tasks": tasks})


@login_required
def update_task(request):
    task_id = request.GET.get("id")
    task = None
    if task_id:
        task = get_object_or_404(Task, id=task_id, owner=request.user)
        if request.method == "POST":
            form = TaskForm(request.POST, instance=task, owner=request.user)
            if form.is_valid():
                form.save()
                return redirect("/todo/")
        else:
            form = TaskForm(instance=task, owner=request.user)
        return render(request, "todo/update_task.html", {"form": form, "task": task})
    tasks = Task.objects.filter(owner=request.user).order_by("-created_at")[:20]
    return render(request, "todo/update_task.html", {"tasks": tasks})


@login_required
def transfer_to_planner(request):
    if request.method != "POST":
        return redirect("/todo/")

    task_id = request.POST.get("id")
    task = get_object_or_404(Task, id=task_id, owner=request.user)

    status_map = {
        Task.Status.OPEN: PlannerItem.Status.PLANNED,
        Task.Status.IN_PROGRESS: PlannerItem.Status.PLANNED,
        Task.Status.DONE: PlannerItem.Status.DONE,
    }
    planner_status = status_map.get(task.status, PlannerItem.Status.PLANNED)

    note_parts = []
    if task.note:
        note_parts.append(task.note)
    note_parts.append(f"[Da Todo] Tipo: {task.get_item_type_display()}")
    note_parts.append(f"[Da Todo] Priorita: {task.get_priority_display()}")
    if task.status == Task.Status.IN_PROGRESS:
        note_parts.append("[Da Todo] Stato origine: In progress")
    if task.category_id:
        note_parts.append(f"[Da Todo] Categoria: {task.category.name}")
    note = "\n".join(note_parts)

    with transaction.atomic():
        PlannerItem.objects.create(
            owner=request.user,
            title=task.title,
            due_date=task.due_date,
            project=task.project,
            category=task.category,
            status=planner_status,
            note=note,
        )
        task.delete()

    return redirect("/planner/")


@login_required
def set_status(request):
    is_htmx = request.headers.get("HX-Request") == "true"
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if request.method != "POST":
        if is_htmx:
            return HttpResponse(status=405)
        if is_ajax:
            return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)
        return redirect("/todo/")

    task_id = request.POST.get("id")
    status = (request.POST.get("status") or "").strip()
    allowed_statuses = {Task.Status.OPEN, Task.Status.IN_PROGRESS, Task.Status.DONE}
    if status not in allowed_statuses:
        if is_ajax:
            return JsonResponse({"ok": False, "error": "invalid_status"}, status=400)
        return redirect("/todo/")

    task = get_object_or_404(Task, id=task_id, owner=request.user)
    task.status = status
    task.save(update_fields=["status"])

    counts = _todo_counts(request.user)
    if is_htmx:
        context = {
            "task": task,
            "counts": counts,
        }
        return render(request, "todo/partials/task_status_oob.html", context)

    if is_ajax:
        return JsonResponse(
            {
                "ok": True,
                "task_id": task.id,
                "status": task.status,
                "counts": counts,
            }
        )

    return redirect("/todo/")
