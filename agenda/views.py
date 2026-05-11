from calendar import Calendar
from datetime import date, timedelta
from decimal import Decimal
import json
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.models import UserNavConfig
from planner.models import PlannerItem
from planner.forms import PlannerItemForm
from projects.models import ProjectNote
from todos.models import TodoRecurrence, TodoItem
from todos.forms import TodoItemForm

from .forms import WorkLogForm
from .models import AgendaItem, WorkLog

MONTH_NAMES_IT = [
    "Gennaio",
    "Febbraio",
    "Marzo",
    "Aprile",
    "Maggio",
    "Giugno",
    "Luglio",
    "Agosto",
    "Settembre",
    "Ottobre",
    "Novembre",
    "Dicembre",
]

ROUTINE_STATUS_LABELS = {
    choice: label for choice, label in TodoRecurrence.Status.choices
}

DEFAULT_AGENDA_PREFERENCES = {
    "density": "comfortable",
    "accent": "blue",
    "sections": ["snapshot", "panel", "forms", "quick_actions"],
}
ALLOWED_AGENDA_DENSITIES = {"comfortable", "compact"}
ALLOWED_AGENDA_ACCENTS = {"blue", "green", "amber", "rose"}
ALLOWED_AGENDA_SECTIONS = {"snapshot", "panel", "forms", "quick_actions"}


def _safe_date(raw_value, default_value):
    if not raw_value:
        return default_value
    try:
        return date.fromisoformat(raw_value)
    except (ValueError, TypeError):
        return default_value


def _week_start(d):
    return d - timedelta(days=d.weekday())


def _get_agenda_preferences(user):
    nav_config, _ = UserNavConfig.objects.get_or_create(user=user)
    raw = nav_config.config or {}
    prefs = raw.get("agenda_preferences", {})
    return {
        "density": prefs.get("density", DEFAULT_AGENDA_PREFERENCES["density"]),
        "accent": prefs.get("accent", DEFAULT_AGENDA_PREFERENCES["accent"]),
        "sections": prefs.get("sections", DEFAULT_AGENDA_PREFERENCES["sections"]),
    }


def _save_agenda_preferences(user, prefs):
    nav_config, _ = UserNavConfig.objects.get_or_create(user=user)
    config = nav_config.config or {}
    config["agenda_preferences"] = prefs
    nav_config.config = config
    nav_config.save(update_fields=["config"])


@login_required
def dashboard(request):
    user = request.user
    today = date.today()

    month_raw = request.GET.get("month")
    selected_raw = request.GET.get("selected")

    if month_raw:
        try:
            month_start = date.fromisoformat(f"{month_raw}-01")
        except (ValueError, TypeError):
            month_start = today.replace(day=1)
    else:
        month_start = today.replace(day=1)

    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    month_param = month_start.strftime("%Y-%m")

    selected_default = month_start
    if month_start <= today <= month_end:
        selected_default = today
    selected_date = _safe_date(selected_raw, selected_default)
    if not (month_start <= selected_date <= month_end):
        selected_date = selected_default
    selected_param = selected_date.isoformat()

    todo_form = None
    work_form = None
    planner_form = None

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_todo_item":
            todo_form = TodoItemForm(request.POST, owner=request.user)
            if todo_form.is_valid():
                item = todo_form.save(commit=False)
                item.owner = request.user
                item.save()
                if item.due_date:
                    return _redirect_agenda(item.due_date.strftime("%Y-%m"), item.due_date.isoformat())
                return _redirect_agenda(month_param, selected_param)
        elif action == "log_hours":
            work_form = WorkLogForm(request.POST)
            if work_form.is_valid():
                log = work_form.save(commit=False)
                log.owner = request.user
                log.save()
                return _redirect_agenda(log.work_date.strftime("%Y-%m"), log.work_date.isoformat())
        elif action == "add_planner":
            planner_form = PlannerItemForm(request.POST, owner=request.user, prefix="planner")
            if planner_form.is_valid():
                item = planner_form.save(commit=False)
                item.owner = request.user
                item.save()
                if item.due_date:
                    return _redirect_agenda(item.due_date.strftime("%Y-%m"), item.due_date.isoformat())
                return _redirect_agenda(month_param, selected_param)

    if todo_form is None:
        todo_form = TodoItemForm(
            owner=user,
            initial={
                "due_date": selected_date,
                "item_type": TodoItem.ItemType.TASK,
                "status": TodoItem.Status.OPEN,
                "is_standalone": True,
            },
        )

    if work_form is None:
        selected_log = WorkLog.objects.filter(owner=user, work_date=selected_date).first()
        if selected_log:
            work_form = WorkLogForm(instance=selected_log)
        else:
            work_form = WorkLogForm(initial={"work_date": selected_date})

    if planner_form is None:
        planner_form = PlannerItemForm(
            owner=user,
            prefix="planner",
            initial={
                "due_date": selected_date,
                "status": PlannerItem.Status.PLANNED,
            },
        )

    agenda_items = (
        AgendaItem.objects.filter(owner=user, due_date__range=(month_start, month_end))
        .select_related("project")
        .order_by("due_date", "due_time", "created_at")
    )
    standalone_todos = (
        TodoItem.objects.filter(owner=user, due_date__range=(month_start, month_end), is_standalone=True)
        .exclude(status=TodoItem.Status.DONE)
        .select_related("project")
        .order_by("due_date", "due_time", "created_at")
    )
    planner_items = (
        PlannerItem.objects.filter(
            owner=user,
            due_date__range=(month_start, month_end),
            status=PlannerItem.Status.PLANNED,
        )
        .select_related("project")
        .order_by("due_date", "created_at")
    )
    work_logs = WorkLog.objects.filter(owner=user, work_date__range=(month_start, month_end)).order_by("work_date")

    events_map = {}
    summary_map = {}

    def ensure_day(day):
        if day not in events_map:
            events_map[day] = []
            summary_map[day] = {
                "agenda_activity": 0,
                "agenda_reminder": 0,
                "todo": 0,
                "planner": 0,
                "hours": Decimal("0"),
            }

    for item in agenda_items:
        ensure_day(item.due_date)
        kind = "agenda_activity" if item.item_type == AgendaItem.ItemType.ACTIVITY else "agenda_reminder"
        if item.status != AgendaItem.Status.DONE:
            summary_map[item.due_date][kind] += 1
        time_text = item.due_time.strftime("%H:%M") if item.due_time else ""
        meta_parts = [item.get_item_type_display(), item.get_status_display()]
        if item.project_id:
            meta_parts.append(item.project.name)
        events_map[item.due_date].append(
            {
                "kind": kind,
                "label": item.get_item_type_display(),
                "title": item.title,
                "time": time_text,
                "meta": " · ".join(meta_parts),
                "is_agenda_item": True,
                "item_id": item.id,
                "is_done": item.status == AgendaItem.Status.DONE,
            }
        )

    for task in standalone_todos:
        if not task.due_date:
            continue
        ensure_day(task.due_date)
        summary_map[task.due_date]["todo"] += 1
        time_text = task.due_time.strftime("%H:%M") if task.due_time else ""
        meta_parts = [task.get_item_type_display(), task.get_status_display()]
        if task.project_id:
            meta_parts.append(task.project.name)
        events_map[task.due_date].append(
            {
                "kind": "todo",
                "label": "Todo",
                "title": task.title,
                "time": time_text,
                "meta": " · ".join(meta_parts),
                "is_agenda_item": False,
            }
        )

    recurring_todos = (
        TodoItem.objects.filter(owner=user, is_active=True, todo_list__is_active=True, is_standalone=False)
        .select_related("todo_list", "project")
        .order_by("time_start", "title")
    )
    if recurring_todos:
        week_start_min = _week_start(month_start)
        week_start_max = _week_start(month_end)
        checks = TodoRecurrence.objects.filter(
            owner=user,
            todo_item__in=recurring_todos,
            week_start__range=(week_start_min, week_start_max),
        )
        check_map = {(check.todo_item_id, check.week_start): check for check in checks}
        by_weekday = {idx: [] for idx in range(7)}
        for item in recurring_todos:
            by_weekday[item.weekday].append(item)

        cursor = month_start
        while cursor <= month_end:
            day_items = by_weekday.get(cursor.weekday(), [])
            if day_items:
                ensure_day(cursor)
                week_start = _week_start(cursor)
                for item in day_items:
                    check = check_map.get((item.id, week_start))
                    status = check.status if check else TodoRecurrence.Status.PLANNED
                    status_label = ROUTINE_STATUS_LABELS.get(status, status)
                    summary_map[cursor]["todo"] += 1
                    time_parts = []
                    if item.time_start:
                        time_parts.append(item.time_start.strftime("%H:%M"))
                    if item.time_end:
                        time_parts.append(item.time_end.strftime("%H:%M"))
                    time_text = "-"
                    if len(time_parts) == 2:
                        time_text = f"{time_parts[0]}-{time_parts[1]}"
                    elif len(time_parts) == 1:
                        time_text = time_parts[0]
                    meta_parts = [item.todo_list.name, status_label]
                    if item.project_id:
                        meta_parts.append(item.project.name)
                    events_map[cursor].append(
                        {
                            "kind": "todo",
                            "label": "TodoList",
                            "title": item.title,
                            "time": "" if time_text == "-" else time_text,
                            "meta": " · ".join(meta_parts),
                            "is_agenda_item": False,
                        }
                    )
            cursor += timedelta(days=1)

    for log in work_logs:
        ensure_day(log.work_date)
        summary_map[log.work_date]["hours"] = log.hours
        time_text = ""
        if log.time_start and log.time_end:
            time_text = f"{log.time_start.strftime('%H:%M')}-{log.time_end.strftime('%H:%M')}"
        events_map[log.work_date].append(
            {
                "kind": "worklog",
                "label": "Lavoro",
                "title": f"Registrate {log.hours} ore",
                "time": time_text,
                "meta": log.note or "",
                "is_agenda_item": False,
            }
        )

    for item in planner_items:
        ensure_day(item.due_date)
        summary_map[item.due_date]["planner"] += 1
        meta_parts = [item.get_status_display()]
        if item.project_id:
            meta_parts.append(item.project.name)
        events_map[item.due_date].append(
            {
                "kind": "planner",
                "label": "Planner",
                "title": item.title,
                "time": "",
                "meta": " · ".join(meta_parts),
                "is_agenda_item": False,
            }
        )

    # Context construction
    month_total_hours = sum(log.hours for log in work_logs)
    month_logged_days = work_logs.count()
    agenda_counts = {
        "planned": agenda_items.exclude(status=AgendaItem.Status.DONE).count(),
        "done": agenda_items.filter(status=AgendaItem.Status.DONE).count(),
    }
    todo_open_month = standalone_todos.count()
    planner_open_month = planner_items.count()
    todo_month_total = sum(summary["todo"] for summary in summary_map.values())

    cal = Calendar(firstweekday=0)
    weeks_raw = cal.monthdayscalendar(month_start.year, month_start.month)
    calendar_weeks = []
    for week in weeks_raw:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                d = date(month_start.year, month_start.month, day)
                summary = summary_map.get(d, {})
                chips = []
                for kind in ["agenda_activity", "agenda_reminder", "todo", "planner", "worklog"]:
                    val = summary.get(kind, 0)
                    if kind == "worklog" and summary.get("hours", 0) > 0:
                        chips.append({"kind": "worklog", "label": "Lavoro", "value": f"{summary['hours']}h"})
                    elif val > 0:
                        label = "Agenda" if "agenda" in kind else kind.capitalize()
                        chips.append({"kind": kind, "label": label, "value": val})

                week_data.append(
                    {
                        "day": day,
                        "iso": d.isoformat(),
                        "is_today": d == today,
                        "is_selected": d == selected_date,
                        "items_count": len(events_map.get(d, [])),
                        "chips": chips,
                    }
                )
        calendar_weeks.append(week_data)

    selected_events = events_map.get(selected_date, [])
    selected_events_total = len(selected_events)

    context = {
        "today": today,
        "selected_date": selected_date,
        "selected_param": selected_param,
        "month_start": month_start,
        "month_end": month_end,
        "month_param": month_param,
        "month_label": f"{MONTH_NAMES_IT[month_start.month - 1]} {month_start.year}",
        "prev_month_param": (month_start - timedelta(days=1)).strftime("%Y-%m"),
        "next_month_param": (month_start + timedelta(days=32)).replace(day=1).strftime("%Y-%m"),
        "weekday_labels": ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"],
        "calendar_weeks": calendar_weeks,
        "selected_events": selected_events,
        "selected_events_total": selected_events_total,
        "month_total_hours": month_total_hours,
        "month_logged_days": month_logged_days,
        "agenda_counts": agenda_counts,
        "todo_open_month": todo_open_month,
        "planner_open_month": planner_open_month,
        "todo_month_total": todo_month_total,
        "todo_form": todo_form,
        "work_form": work_form,
        "planner_form": planner_form,
        "prefs": _get_agenda_preferences(user),
    }

    return render(request, "agenda/dashboard.html", context)


@login_required
@require_http_methods(["POST"])
def agenda_item_action(request):
    user = request.user
    action = request.POST.get("action")
    item_id = request.POST.get("item_id")
    month_param = request.POST.get("month")
    selected_param = request.POST.get("selected")

    item = get_object_or_404(AgendaItem, id=item_id, owner=user)

    if action == "toggle_item":
        if item.status == AgendaItem.Status.DONE:
            item.status = AgendaItem.Status.PLANNED
        else:
            item.status = AgendaItem.Status.DONE
        item.save(update_fields=["status", "updated_at"])
    elif action == "remove_item":
        item.delete()

    if request.headers.get("HX-Request") == "true":
        return panel(request)

    return _redirect_agenda(month_param, selected_param)


@login_required
def panel(request):
    # This is a helper to return only the panel partial for HTMX requests
    # We can reuse the logic from dashboard or extract it.
    # For now, let's just call dashboard but render a different template if it's a sub-request.
    # Actually, the panel.html needs all the context from dashboard.
    # So we call dashboard(request) but we need to intercept the render.
    # A better way is to move common logic to a function.
    # But for a quick fix, let's just make panel() do what it needs.
    return dashboard(request)


def _redirect_agenda(month, selected):
    return redirect(f"/agenda/?month={month}&selected={selected}")


@login_required
@require_http_methods(["POST"])
def update_preferences(request):
    user = request.user
    density = request.POST.get("density")
    accent = request.POST.get("accent")
    sections = request.POST.getlist("sections")

    prefs = _get_agenda_preferences(user)
    if density in ALLOWED_AGENDA_DENSITIES:
        prefs["density"] = density
    if accent in ALLOWED_AGENDA_ACCENTS:
        prefs["accent"] = accent
    if sections:
        prefs["sections"] = [s for s in sections if s in ALLOWED_AGENDA_SECTIONS]

    _save_agenda_preferences(user, prefs)
    return _redirect_agenda(request.POST.get("month"), request.POST.get("selected"))
