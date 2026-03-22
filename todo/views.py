from datetime import date
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Case, F, IntegerField, Value, When
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .dav_sync import (
    delete_task_from_vtodo,
    sync_all_tasks_to_vtodo,
    todo_collection_path_for_user,
    todo_collection_slug,
    todo_collection_url_for_user,
    push_task_to_vtodo,
)
from .forms import TaskForm
from .models import Task

logger = logging.getLogger(__name__)


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
    dav_collection_path = todo_collection_path_for_user(user)
    dav_collection_url = todo_collection_url_for_user(user)
    return render(
        request,
        "todo/dashboard.html",
        {
            "task_rows": task_rows,
            "counts": counts,
            "today": today,
            "dav_vtodo_collection_slug": todo_collection_slug(),
            "dav_vtodo_collection_path": dav_collection_path,
            "dav_vtodo_collection_url": dav_collection_url,
        },
    )


def _sync_task_quiet(task: Task) -> None:
    result = push_task_to_vtodo(task)
    if result.ok:
        return
    logger.warning("Todo DAV sync failed for task=%s user=%s: %s", task.id, task.owner_id, result.message)


def _delete_task_quiet(task: Task) -> None:
    result = delete_task_from_vtodo(task)
    if result.ok:
        return
    logger.warning("Todo DAV delete sync failed for task=%s user=%s: %s", task.id, task.owner_id, result.message)


@login_required
def add_task(request):
    if request.method == "POST":
        form = TaskForm(request.POST, owner=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.owner = request.user
            task.save()
            _sync_task_quiet(task)
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
            _delete_task_quiet(task)
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
                task = form.save()
                _sync_task_quiet(task)
                return redirect("/todo/")
        else:
            form = TaskForm(instance=task, owner=request.user)
        return render(request, "todo/update_task.html", {"form": form, "task": task})
    tasks = Task.objects.filter(owner=request.user).order_by("-created_at")[:20]
    return render(request, "todo/update_task.html", {"tasks": tasks})


@login_required
def sync_vtodo(request):
    if request.method != "POST":
        return redirect("/todo/")

    stats = sync_all_tasks_to_vtodo(request.user)
    if stats["failed"]:
        messages.warning(
            request,
            (
                f"Sincronizzazione parziale completata: {stats['synced']}/{stats['total']} task."
                + (f" Errore: {stats['error']}" if stats["error"] else "")
            ),
        )
    else:
        messages.success(request, f"Sync VTODO completata: {stats['synced']} task allineate.")
    return redirect("/todo/")


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
    _sync_task_quiet(task)

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
