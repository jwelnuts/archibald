from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Project, SubProject, SubProjectActivity
from todo.models import Task
from planner.models import PlannerItem

STATUS_COLORS = {
    "planned": "#f59e0b",
    "in_progress": "#3b82f6",
    "blocked": "#ef4444",
    "done": "#22c55e",
    "todo": "#f59e0b",
}


def _build_timeline_data(user, project_filter=None, scope="active"):
    projects_qs = Project.objects.filter(owner=user)
    if scope == "active":
        projects_qs = projects_qs.filter(is_archived=False)
    elif scope == "archived":
        projects_qs = projects_qs.filter(is_archived=True)
    if project_filter:
        projects_qs = projects_qs.filter(id__in=project_filter)

    projects_qs = projects_qs.order_by("is_archived", "name")

    today = timezone.now().date()
    projects_payload = []
    global_min = None
    global_max = None

    for proj in projects_qs:
        sub_qs = SubProject.objects.filter(owner=user, project=proj)
        task_qs = Task.objects.filter(owner=user, project=proj).exclude(
            Q(due_date__isnull=True) | Q(status=Task.Status.DONE)
        )
        planner_qs = PlannerItem.objects.filter(
            owner=user, project=proj
        ).exclude(
            Q(due_date__isnull=True) | Q(status=PlannerItem.Status.DONE) | Q(status=PlannerItem.Status.SKIPPED)
        )

        bars = []
        for sp in sub_qs:
            start = sp.start_date or today
            end = sp.due_date or (start + timedelta(days=7))
            if end < start:
                end = start + timedelta(days=1)
            color = STATUS_COLORS.get(sp.status, "#6b7280")
            bars.append({
                "id": f"sp-{sp.id}",
                "title": sp.title,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "progress": sp.completion_percent,
                "color": color,
                "status": sp.status,
                "kind": "subproject",
                "url": f"/projects/subprojects/view?id={sp.id}",
            })
            if global_min is None or start < global_min:
                global_min = start
            if global_max is None or end > global_max:
                global_max = end

        for task in task_qs:
            due = task.due_date or today
            start = due - timedelta(days=1)
            bars.append({
                "id": f"tk-{task.id}",
                "title": task.title,
                "start": start.isoformat(),
                "end": due.isoformat(),
                "progress": 0 if task.status == Task.Status.OPEN else 50,
                "color": STATUS_COLORS.get(task.status, STATUS_COLORS["todo"]),
                "status": task.status,
                "kind": "task",
                "url": f"/todo/api/update?id={task.id}",
            })
            if global_min is None or start < global_min:
                global_min = start
            if global_max is None or due > global_max:
                global_max = due

        for item in planner_qs:
            due = item.due_date or today
            start = due - timedelta(days=1)
            bars.append({
                "id": f"pl-{item.id}",
                "title": item.title,
                "start": start.isoformat(),
                "end": due.isoformat(),
                "progress": 0,
                "color": STATUS_COLORS.get(item.status, "#8b5cf6"),
                "status": item.status,
                "kind": "planner",
                "url": f"/planner/update?id={item.id}",
            })
            if global_min is None or start < global_min:
                global_min = start
            if global_max is None or due > global_max:
                global_max = due

        project_bars_count = len(bars)
        if project_bars_count > 0:
            projects_payload.append({
                "id": f"proj-{proj.id}",
                "title": proj.name,
                "is_archived": proj.is_archived,
                "bars_count": project_bars_count,
                "bars": bars,
            })

    if global_min is None:
        global_min = today
    if global_max is None:
        global_max = today + timedelta(days=30)

    global_min = global_min - timedelta(days=2)
    global_max = global_max + timedelta(days=2)

    return {
        "projects": projects_payload,
        "today": today.isoformat(),
        "range_start": global_min.isoformat(),
        "range_end": global_max.isoformat(),
        "project_count": len(projects_payload),
        "bar_count": sum(p["bars_count"] for p in projects_payload),
    }


@login_required
def timeline_dashboard(request):
    project_ids = request.GET.getlist("project")
    scope = (request.GET.get("scope") or "active").strip().lower()
    if scope not in {"active", "archived", "all"}:
        scope = "active"

    timeline_data = _build_timeline_data(
        request.user,
        project_filter=project_ids if project_ids else None,
        scope=scope,
    )

    projects_qs = Project.objects.filter(owner=request.user).order_by("name")
    if scope in {"active", "archived"}:
        is_archived = scope == "archived"
        projects_qs = projects_qs.filter(is_archived=is_archived)

    return render(
        request,
        "projects/timeline.html",
        {
            "timeline_data": timeline_data,
            "projects": projects_qs,
            "scope": scope,
            "project_count": timeline_data["project_count"],
            "bar_count": timeline_data["bar_count"],
        },
    )


@login_required
def timeline_data(request):
    project_ids = request.GET.getlist("project")
    scope = (request.GET.get("scope") or "active").strip().lower()
    if scope not in {"active", "archived", "all"}:
        scope = "active"

    timeline_data = _build_timeline_data(
        request.user,
        project_filter=project_ids if project_ids else None,
        scope=scope,
    )
    return JsonResponse(timeline_data)
