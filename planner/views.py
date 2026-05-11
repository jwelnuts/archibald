from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PlannerItemForm
from .models import PlannerItem
from projects.models import Project


@login_required
def dashboard(request):
    user = request.user
    status_filter = (request.GET.get("status") or "").strip().lower()
    query = (request.GET.get("q") or "").strip()
    project_filter = (request.GET.get("project") or "").strip()

    qs = PlannerItem.objects.filter(owner=user)

    if status_filter in dict(PlannerItem.Status.choices):
        qs = qs.filter(status=status_filter.upper())

    if query:
        qs = qs.filter(
            Q(title__icontains=query)
            | Q(note__icontains=query)
            | Q(category__name__icontains=query)
            | Q(project__name__icontains=query)
        )

    if project_filter:
        qs = qs.filter(project_id=project_filter, project__owner=user)

    upcoming = qs.filter(status=PlannerItem.Status.PLANNED).order_by("due_date", "created_at")[:10]

    counts = {
        "planned": qs.filter(status=PlannerItem.Status.PLANNED).count(),
        "done": qs.filter(status=PlannerItem.Status.DONE).count(),
        "skipped": qs.filter(status=PlannerItem.Status.SKIPPED).count(),
    }

    # For project filter dropdown
    projects_with_planner = (
        Project.objects.filter(owner=user, planner_items__isnull=False)
        .distinct()
        .order_by("name")
    )

    is_htmx = request.headers.get("HX-Request") == "true"
    context = {
        "upcoming": upcoming,
        "counts": counts,
        "status_filter": status_filter,
        "query": query,
        "project_filter": project_filter,
        "projects_with_planner": projects_with_planner,
    }

    if is_htmx:
        return render(request, "planner/partials/dashboard_content.html", context)
    return render(request, "planner/dashboard.html", context)


@login_required
def add_item(request):
    if request.method == "POST":
        form = PlannerItemForm(request.POST, owner=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            if item.project_id:
                from projects.models import ProjectNote

                due = item.due_date.strftime("%d/%m/%Y") if item.due_date else "senza scadenza"
                note_parts = [
                    f"Promemoria creato: {item.title}",
                    f"Scadenza: {due}",
                    f"Stato: {item.get_status_display()}",
                ]
                if item.note:
                    note_parts.append(f"Note: {item.note}")
                ProjectNote.objects.create(
                    owner=request.user,
                    project=item.project,
                    content="<br>".join(note_parts),
                )
            is_htmx = request.headers.get("HX-Request") == "true"
            if is_htmx:
                return redirect("/planner/")
            return redirect("/planner/")
    else:
        initial = {}
        project_id = request.GET.get("project")
        if project_id:
            project = get_object_or_404(Project, id=project_id, owner=request.user)
            initial["project"] = project
        form = PlannerItemForm(owner=request.user, initial=initial)

    is_htmx = request.headers.get("HX-Request") == "true"
    ctx = {"form": form}
    if is_htmx:
        return render(request, "planner/partials/form.html", ctx)
    return render(request, "planner/add_item.html", ctx)


@login_required
def update_item(request):
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(PlannerItem, id=item_id, owner=request.user)
        if request.method == "POST":
            form = PlannerItemForm(request.POST, instance=item, owner=request.user)
            if form.is_valid():
                form.save()
                is_htmx = request.headers.get("HX-Request") == "true"
                if is_htmx:
                    return redirect("/planner/")
                return redirect("/planner/")
        else:
            form = PlannerItemForm(instance=item, owner=request.user)
        is_htmx = request.headers.get("HX-Request") == "true"
        ctx = {"form": form, "item": item}
        if is_htmx:
            return render(request, "planner/partials/form.html", ctx)
        return render(request, "planner/update_item.html", ctx)
    items = PlannerItem.objects.filter(owner=request.user).order_by("-created_at")[:20]
    return render(request, "planner/update_item.html", {"items": items})


@login_required
def remove_item(request):
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(PlannerItem, id=item_id, owner=request.user)
        if request.method == "POST":
            item.delete()
            is_htmx = request.headers.get("HX-Request") == "true"
            if is_htmx:
                return redirect("/planner/")
            return redirect("/planner/")
    items = PlannerItem.objects.filter(owner=request.user).order_by("-created_at")[:20]
    return render(request, "planner/remove_item.html", {"item": item, "items": items})


@login_required
def api_toggle_status(request):
    """AJAX endpoint to toggle planner item status."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    item_id = request.POST.get("id")
    status = (request.POST.get("status") or "").strip().upper()

    if status not in dict(PlannerItem.Status.choices):
        return JsonResponse({"error": "Invalid status"}, status=400)

    item = get_object_or_404(PlannerItem, id=item_id, owner=request.user)
    item.status = status
    item.save(update_fields=["status", "updated_at"])
    return JsonResponse({"ok": True, "id": item.id, "status": item.status})


@login_required
def api_delete_item(request):
    """AJAX endpoint to delete a planner item."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    item_id = request.POST.get("id")
    item = get_object_or_404(PlannerItem, id=item_id, owner=request.user)
    item.delete()
    return JsonResponse({"ok": True, "id": item_id})
