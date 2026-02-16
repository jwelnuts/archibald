from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PlannerItemForm
from .models import PlannerItem
from projects.models import Project, ProjectNote


@login_required
def dashboard(request):
    user = request.user
    upcoming = (
        PlannerItem.objects.filter(owner=user, status=PlannerItem.Status.PLANNED)
        .order_by("due_date", "created_at")[:10]
    )
    counts = {
        "planned": PlannerItem.objects.filter(owner=user, status=PlannerItem.Status.PLANNED).count(),
        "done": PlannerItem.objects.filter(owner=user, status=PlannerItem.Status.DONE).count(),
        "skipped": PlannerItem.objects.filter(owner=user, status=PlannerItem.Status.SKIPPED).count(),
    }
    return render(request, "planner/dashboard.html", {"upcoming": upcoming, "counts": counts})


@login_required
def add_item(request):
    if request.method == "POST":
        form = PlannerItemForm(request.POST, owner=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            if item.project_id:
                due = item.due_date.strftime("%d/%m/%Y") if item.due_date else "senza scadenza"
                note_parts = [f"Promemoria creato: {item.title}", f"Scadenza: {due}", f"Stato: {item.get_status_display()}"]
                if item.note:
                    note_parts.append(f"Note: {item.note}")
                ProjectNote.objects.create(
                    owner=request.user,
                    project=item.project,
                    content="<br>".join(note_parts),
                )
            return redirect("/planner/")
    else:
        initial = {}
        project_id = request.GET.get("project")
        if project_id:
            project = get_object_or_404(Project, id=project_id, owner=request.user)
            initial["project"] = project
        form = PlannerItemForm(owner=request.user, initial=initial)
    return render(request, "planner/add_item.html", {"form": form})


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
                return redirect("/planner/")
        else:
            form = PlannerItemForm(instance=item, owner=request.user)
        return render(request, "planner/update_item.html", {"form": form, "item": item})
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
            return redirect("/planner/")
    items = PlannerItem.objects.filter(owner=request.user).order_by("-created_at")[:20]
    return render(request, "planner/remove_item.html", {"item": item, "items": items})
