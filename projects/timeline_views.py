from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Project, SubProject, SubProjectActivity
from planner.models import PlannerItem
from todos.models import TodoItem

STATUS_COLORS = {
    "planned": "#f59e0b",
    "in_progress": "#3b82f6",
    "blocked": "#ef4444",
    "done": "#22c55e",
    "todo": "#f59e0b",
    "skipped": "#9ca3af",
}

STATUS_LABELS = {
    "planned": "Pianificato",
    "in_progress": "In corso",
    "blocked": "Bloccato",
    "done": "Completato",
    "todo": "Da fare",
    "open": "Aperto",
    "skipped": "Saltato",
}


def _get_week_range(ref_date):
    """Return (monday, sunday) of the week containing ref_date."""
    monday = ref_date - timedelta(days=ref_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _build_week_data(user, week_start, project_filter=None, scope="active"):
    week_end = week_start + timedelta(days=6)

    projects_qs = Project.objects.filter(owner=user)
    if scope == "active":
        projects_qs = projects_qs.filter(is_archived=False)
    elif scope == "archived":
        projects_qs = projects_qs.filter(is_archived=True)
    if project_filter:
        projects_qs = projects_qs.filter(id__in=project_filter)

    projects_qs = projects_qs.order_by("is_archived", "name")

    projects_payload = []
    total_items = 0

    for proj in projects_qs:
        items = []

        # SubProjects
        sub_qs = SubProject.objects.filter(owner=user, project=proj)
        for sp in sub_qs:
            start = sp.start_date or week_start
            end = sp.due_date or (start + timedelta(days=7))
            if end < start:
                end = start + timedelta(days=1)
            # Check overlap with week
            if start <= week_end and end >= week_start:
                items.append({
                    "id": f"sp-{sp.id}",
                    "title": sp.title,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "progress": sp.completion_percent,
                    "status": sp.status,
                    "kind": "subproject",
                    "kind_label": "Sub-progetto",
                    "color": STATUS_COLORS.get(sp.status, "#6b7280"),
                    "url": f"/projects/subprojects/view?id={sp.id}",
                    "all_day": True,
                })

        # Tasks (non-done, with due_date in range or no due_date)
        task_qs = TodoItem.objects.filter(owner=user, project=proj).exclude(
            Q(due_date__isnull=True) | Q(status=TodoItem.Status.DONE)
        )
        for task in task_qs:
            due = task.due_date
            if due and week_start <= due <= week_end:
                start = due
                end = due + timedelta(days=1)
                items.append({
                    "id": f"tk-{task.id}",
                    "title": task.title,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "progress": 0 if task.status == TodoItem.Status.OPEN else 50,
                    "status": task.status,
                    "kind": "task",
                    "kind_label": "Task",
                    "color": STATUS_COLORS.get(task.status, STATUS_COLORS["todo"]),
                    "url": f"/projects/view?id={proj.id}#task-{task.id}",
                    "all_day": True,
                })

        # PlannerItems
        planner_qs = PlannerItem.objects.filter(owner=user, project=proj).exclude(
            Q(due_date__isnull=True) | Q(status=PlannerItem.Status.DONE) | Q(status=PlannerItem.Status.SKIPPED)
        )
        for item in planner_qs:
            due = item.due_date
            if due and week_start <= due <= week_end:
                start = due
                end = due + timedelta(days=1)
                items.append({
                    "id": f"pl-{item.id}",
                    "title": item.title,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "progress": 0,
                    "status": item.status,
                    "kind": "planner",
                    "kind_label": "Planner",
                    "color": STATUS_COLORS.get(item.status, "#8b5cf6"),
                    "url": f"/planner/update?id={item.id}",
                    "all_day": True,
                })

        if items:
            total_items += len(items)
            projects_payload.append({
                "id": f"proj-{proj.id}",
                "title": proj.name,
                "is_archived": proj.is_archived,
                "items_count": len(items),
                "items": items,
            })

    return {
        "projects": projects_payload,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "project_count": len(projects_payload),
        "item_count": total_items,
    }


def _week_options():
    """Generate week label options for the selector."""
    today = timezone.now().date()
    monday = today - timedelta(days=today.weekday())
    options = []
    for i in range(-4, 5):
        week_start = monday + timedelta(weeks=i)
        week_end = week_start + timedelta(days=6)
        label = f"{week_start.day} {week_start.strftime('%b')} — {week_end.day} {week_end.strftime('%b')}"
        if week_start == monday:
            label += " (questa settimana)"
        options.append({
            "value": week_start.isoformat(),
            "label": label,
            "is_current": i == 0,
        })
    return options


@login_required
def timeline_dashboard(request):
    project_ids = request.GET.getlist("project")
    scope = (request.GET.get("scope") or "active").strip().lower()
    if scope not in {"active", "archived", "all"}:
        scope = "active"

    # Parse week parameter, default to current week
    week_raw = (request.GET.get("week") or "").strip()
    try:
        week_start = date.fromisoformat(week_raw) if week_raw else None
    except ValueError:
        week_start = None
    if week_start is None:
        week_start = timezone.now().date()
        week_start = week_start - timedelta(days=week_start.weekday())

    week_data = _build_week_data(
        request.user,
        week_start=week_start,
        project_filter=project_ids if project_ids else None,
        scope=scope,
    )

    projects_qs = Project.objects.filter(owner=request.user).order_by("name")
    if scope in {"active", "archived"}:
        is_archived = scope == "archived"
        projects_qs = projects_qs.filter(is_archived=is_archived)

    week_days = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        week_days.append({
            "iso": d.isoformat(),
            "name": d.strftime("%a").upper(),
            "date": d.strftime("%d/%m"),
            "is_today": d == timezone.now().date(),
        })

    return render(
        request,
        "projects/timeline.html",
        {
            "week_data": week_data,
            "projects": projects_qs,
            "scope": scope,
            "week_start": week_start,
            "week_end": week_start + timedelta(days=6),
            "week_options": _week_options(),
            "week_days": week_days,
            "project_count": week_data["project_count"],
            "item_count": week_data["item_count"],
        },
    )


@login_required
def timeline_data(request):
    project_ids = request.GET.getlist("project")
    scope = (request.GET.get("scope") or "active").strip().lower()
    if scope not in {"active", "archived", "all"}:
        scope = "active"

    week_raw = (request.GET.get("week") or "").strip()
    try:
        week_start = date.fromisoformat(week_raw) if week_raw else None
    except ValueError:
        week_start = None
    if week_start is None:
        week_start = timezone.now().date()
        week_start = week_start - timedelta(days=week_start.weekday())

    week_data = _build_week_data(
        request.user,
        week_start=week_start,
        project_filter=project_ids if project_ids else None,
        scope=scope,
    )
    return JsonResponse(week_data)