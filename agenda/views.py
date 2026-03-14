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
from routines.models import RoutineCheck, RoutineItem
from todo.forms import TaskForm
from todo.models import Task

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
    choice: label for choice, label in RoutineCheck.Status.choices
}

DEFAULT_AGENDA_PREFERENCES = {
    "density": "comfortable",
    "accent": "blue",
    "sections": ["snapshot", "panel", "forms", "quick_actions"],
}
ALLOWED_AGENDA_DENSITIES = {"comfortable", "compact"}
ALLOWED_AGENDA_ACCENTS = {"blue", "green", "amber", "rose"}
ALLOWED_AGENDA_SECTIONS = {"snapshot", "panel", "forms", "quick_actions"}


def _month_start_end(month_raw: str | None):
    today = date.today()
    if month_raw:
        try:
            year, month = month_raw.split("-")
            current = date(int(year), int(month), 1)
        except Exception:
            current = today.replace(day=1)
    else:
        current = today.replace(day=1)
    if current.month == 12:
        next_month = current.replace(year=current.year + 1, month=1, day=1)
    else:
        next_month = current.replace(month=current.month + 1, day=1)
    month_end = next_month - timedelta(days=1)
    return current, month_end


def _safe_date(raw_value: str | None, fallback: date):
    if not raw_value:
        return fallback
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return fallback


def _hours_label(hours):
    if hours in (None, Decimal("0"), 0):
        return "0"
    normalized = hours.quantize(Decimal("0.01")).normalize()
    return format(normalized, "f").rstrip("0").rstrip(".") or "0"


def _week_start(day: date):
    return day - timedelta(days=day.weekday())


def _redirect_agenda(month_value: str | None, selected_value: str | None):
    params = {}
    if month_value:
        params["month"] = month_value
    if selected_value:
        params["selected"] = selected_value
    query = urlencode(params)
    return redirect(f"/agenda/{'?' + query if query else ''}")


def _normalize_agenda_preferences(raw_config):
    if not isinstance(raw_config, dict):
        raw_config = {}

    density = (raw_config.get("density") or DEFAULT_AGENDA_PREFERENCES["density"]).strip().lower()
    if density not in ALLOWED_AGENDA_DENSITIES:
        density = DEFAULT_AGENDA_PREFERENCES["density"]

    accent = (raw_config.get("accent") or DEFAULT_AGENDA_PREFERENCES["accent"]).strip().lower()
    if accent not in ALLOWED_AGENDA_ACCENTS:
        accent = DEFAULT_AGENDA_PREFERENCES["accent"]

    sections_raw = raw_config.get("sections", [])
    sections = []
    if isinstance(sections_raw, list):
        for row in sections_raw:
            key = (str(row) or "").strip().lower()
            if key in ALLOWED_AGENDA_SECTIONS and key not in sections:
                sections.append(key)

    if not sections:
        sections = list(DEFAULT_AGENDA_PREFERENCES["sections"])

    return {
        "density": density,
        "accent": accent,
        "sections": sections,
    }


def _agenda_preferences_for_user(user):
    nav_config, _ = UserNavConfig.objects.get_or_create(user=user)
    raw = nav_config.config or {}
    return _normalize_agenda_preferences(raw.get("agenda_preferences", {}))


def _build_agenda_context(
    user,
    month_raw: str | None,
    selected_raw: str | None,
    todo_form=None,
    work_form=None,
    planner_form=None,
):
    month_start, month_end = _month_start_end(month_raw)
    month_param = month_start.strftime("%Y-%m")

    selected_default = month_start
    if month_start <= date.today() <= month_end:
        selected_default = date.today()
    selected_date = _safe_date(selected_raw, selected_default)
    if not (month_start <= selected_date <= month_end):
        selected_date = selected_default
    selected_param = selected_date.isoformat()

    if todo_form is None:
        todo_form = TaskForm(
            owner=user,
            initial={
                "due_date": selected_date,
                "item_type": Task.ItemType.REMINDER,
                "status": Task.Status.OPEN,
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
    todo_items = (
        Task.objects.filter(owner=user, due_date__range=(month_start, month_end))
        .exclude(status=Task.Status.DONE)
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
                "routine": 0,
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

    for task in todo_items:
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

    for item in planner_items:
        if not item.due_date:
            continue
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

    routine_items = (
        RoutineItem.objects.filter(owner=user, is_active=True, routine__is_active=True)
        .select_related("routine", "project")
        .order_by("time_start", "title")
    )
    if routine_items:
        week_start_min = _week_start(month_start)
        week_start_max = _week_start(month_end)
        checks = RoutineCheck.objects.filter(
            owner=user,
            item__in=routine_items,
            week_start__range=(week_start_min, week_start_max),
        )
        check_map = {(check.item_id, check.week_start): check for check in checks}
        by_weekday = {idx: [] for idx in range(7)}
        for item in routine_items:
            by_weekday.setdefault(item.weekday, []).append(item)

        cursor = month_start
        while cursor <= month_end:
            day_items = by_weekday.get(cursor.weekday(), [])
            if day_items:
                ensure_day(cursor)
                week_start = _week_start(cursor)
                for item in day_items:
                    check = check_map.get((item.id, week_start))
                    status = check.status if check else RoutineCheck.Status.PLANNED
                    status_label = ROUTINE_STATUS_LABELS.get(status, status)
                    summary_map[cursor]["routine"] += 1
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
                    meta_parts = [item.routine.name, status_label]
                    if item.project_id:
                        meta_parts.append(item.project.name)
                    events_map[cursor].append(
                        {
                            "kind": "routine",
                            "label": "Routine",
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
        meta = f"{_hours_label(log.hours)}h"
        if log.lunch_break_minutes:
            meta = f"{meta} · pausa {log.lunch_break_minutes}m"
        events_map[log.work_date].append(
            {
                "kind": "worklog",
                "label": "Ore lavoro",
                "title": "Ore lavorate",
                "time": time_text,
                "meta": meta,
                "is_agenda_item": False,
            }
        )

    for day in events_map:
        events_map[day].sort(key=lambda row: (row["time"] == "", row["time"], row["title"].lower()))

    month_total_hours = work_logs.aggregate(total=Sum("hours")).get("total") or Decimal("0")
    month_logged_days = work_logs.count()
    routine_month_total = sum(summary["routine"] for summary in summary_map.values())

    weeks = []
    calendar = Calendar(firstweekday=0)
    for week_dates in calendar.monthdatescalendar(month_start.year, month_start.month):
        week_cells = []
        for cell_date in week_dates:
            if cell_date.month != month_start.month:
                week_cells.append(None)
                continue
            summary = summary_map.get(
                cell_date,
                {
                    "agenda_activity": 0,
                    "agenda_reminder": 0,
                    "todo": 0,
                    "planner": 0,
                    "routine": 0,
                    "hours": Decimal("0"),
                },
            )
            chips = []
            if summary["agenda_activity"]:
                chips.append({"kind": "agenda_activity", "label": "Attivita", "value": summary["agenda_activity"]})
            if summary["agenda_reminder"]:
                chips.append({"kind": "agenda_reminder", "label": "Reminder", "value": summary["agenda_reminder"]})
            if summary["todo"]:
                chips.append({"kind": "todo", "label": "Todo", "value": summary["todo"]})
            if summary["planner"]:
                chips.append({"kind": "planner", "label": "Planner", "value": summary["planner"]})
            if summary["routine"]:
                chips.append({"kind": "routine", "label": "Routine", "value": summary["routine"]})
            if summary["hours"] > 0:
                chips.append({"kind": "worklog", "label": "Ore", "value": f"{_hours_label(summary['hours'])}h"})
            week_cells.append(
                {
                    "date": cell_date,
                    "iso": cell_date.isoformat(),
                    "day": cell_date.day,
                    "is_today": cell_date == date.today(),
                    "is_selected": cell_date == selected_date,
                    "chips": chips,
                    "items_count": len(events_map.get(cell_date, [])),
                }
            )
        weeks.append(week_cells)

    if month_start.month == 1:
        prev_month = month_start.replace(year=month_start.year - 1, month=12, day=1)
    else:
        prev_month = month_start.replace(month=month_start.month - 1, day=1)
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1, day=1)

    selected_events = events_map.get(selected_date, [])

    context = {
        "month_start": month_start,
        "month_end": month_end,
        "month_label": f"{MONTH_NAMES_IT[month_start.month - 1]} {month_start.year}",
        "month_param": month_param,
        "selected_param": selected_param,
        "selected_date": selected_date,
        "prev_month_param": prev_month.strftime("%Y-%m"),
        "next_month_param": next_month.strftime("%Y-%m"),
        "calendar_weeks": weeks,
        "weekday_labels": ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"],
        "selected_events": selected_events,
        "month_total_hours": _hours_label(month_total_hours),
        "month_logged_days": month_logged_days,
        "agenda_counts": {
            "planned": agenda_items.filter(status=AgendaItem.Status.PLANNED).count(),
            "done": agenda_items.filter(status=AgendaItem.Status.DONE).count(),
        },
        "todo_open_month": todo_items.count(),
        "planner_open_month": planner_items.count(),
        "routine_month_total": routine_month_total,
        "selected_events_total": len(selected_events),
        "todo_form": todo_form,
        "work_form": work_form,
        "planner_form": planner_form,
    }
    return context


@login_required
def dashboard(request):
    month_raw = request.GET.get("month")
    selected_raw = request.GET.get("selected")
    todo_form = None
    work_form = None
    planner_form = None

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        posted_month = request.POST.get("month") or month_raw
        posted_selected = request.POST.get("selected") or selected_raw

        if action == "add_todo_item":
            todo_form = TaskForm(request.POST, owner=request.user)
            if todo_form.is_valid():
                task = todo_form.save(commit=False)
                task.owner = request.user
                task.save()
                if task.due_date:
                    return _redirect_agenda(task.due_date.strftime("%Y-%m"), task.due_date.isoformat())
                return _redirect_agenda(posted_month, posted_selected)
        elif action == "log_hours":
            work_form = WorkLogForm(request.POST)
            if work_form.is_valid():
                work_date = work_form.cleaned_data["work_date"]
                WorkLog.objects.update_or_create(
                    owner=request.user,
                    work_date=work_date,
                    defaults={
                        "time_start": work_form.cleaned_data["time_start"],
                        "time_end": work_form.cleaned_data["time_end"],
                        "lunch_break_minutes": work_form.cleaned_data["lunch_break_minutes"],
                        "hours": work_form.cleaned_data["hours"],
                        "note": work_form.cleaned_data["note"],
                    },
                )
                return _redirect_agenda(work_date.strftime("%Y-%m"), work_date.isoformat())
        elif action == "add_planner_item":
            planner_form = PlannerItemForm(request.POST, owner=request.user, prefix="planner")
            if planner_form.is_valid():
                item = planner_form.save(commit=False)
                item.owner = request.user
                item.save()
                if item.project_id:
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
                if item.due_date:
                    return _redirect_agenda(item.due_date.strftime("%Y-%m"), item.due_date.isoformat())
                return _redirect_agenda(posted_month, posted_selected)
        elif action == "toggle_item":
            item = get_object_or_404(AgendaItem, id=request.POST.get("item_id"), owner=request.user)
            item.status = AgendaItem.Status.DONE if item.status != AgendaItem.Status.DONE else AgendaItem.Status.PLANNED
            item.save(update_fields=["status", "updated_at"])
            return _redirect_agenda(posted_month, posted_selected)
        elif action == "remove_item":
            item = get_object_or_404(AgendaItem, id=request.POST.get("item_id"), owner=request.user)
            item.delete()
            return _redirect_agenda(posted_month, posted_selected)

        month_raw = posted_month
        selected_raw = posted_selected

    context = _build_agenda_context(
        user=request.user,
        month_raw=month_raw,
        selected_raw=selected_raw,
        todo_form=todo_form,
        work_form=work_form,
        planner_form=planner_form,
    )
    context["agenda_preferences"] = _agenda_preferences_for_user(request.user)
    return render(request, "agenda/dashboard.html", context)


@login_required
@require_http_methods(["GET"])
def panel(request):
    context = _build_agenda_context(
        user=request.user,
        month_raw=request.GET.get("month"),
        selected_raw=request.GET.get("selected"),
    )
    return render(request, "agenda/partials/panel.html", context)


@login_required
@require_http_methods(["GET"])
def snapshot(request):
    context = _build_agenda_context(
        user=request.user,
        month_raw=request.GET.get("month"),
        selected_raw=request.GET.get("selected"),
    )
    return render(request, "agenda/partials/snapshot.html", context)


@login_required
@require_http_methods(["POST"])
def item_action(request):
    action = (request.POST.get("action") or "").strip()
    month_value = request.POST.get("month") or request.GET.get("month")
    selected_value = request.POST.get("selected") or request.GET.get("selected")

    if action == "toggle_item":
        item = get_object_or_404(AgendaItem, id=request.POST.get("item_id"), owner=request.user)
        item.status = AgendaItem.Status.DONE if item.status != AgendaItem.Status.DONE else AgendaItem.Status.PLANNED
        item.save(update_fields=["status", "updated_at"])
    elif action == "remove_item":
        item = get_object_or_404(AgendaItem, id=request.POST.get("item_id"), owner=request.user)
        item.delete()

    if request.headers.get("HX-Request"):
        context = _build_agenda_context(
            user=request.user,
            month_raw=month_value,
            selected_raw=selected_value,
        )
        response = render(request, "agenda/partials/panel.html", context)
        response["HX-Trigger"] = "agenda:refresh-snapshot"
        return response

    return _redirect_agenda(month_value, selected_value)


@login_required
@require_http_methods(["POST"])
def preferences(request):
    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    normalized = _normalize_agenda_preferences(payload)

    nav_config, _ = UserNavConfig.objects.get_or_create(user=request.user)
    config = nav_config.config if isinstance(nav_config.config, dict) else {}
    config["agenda_preferences"] = normalized
    nav_config.config = config
    nav_config.save(update_fields=["config"])

    return JsonResponse({"ok": True, "agenda_preferences": normalized})
