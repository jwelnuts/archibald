from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    QuickRoutineForm,
    QuickRoutineItemForm,
    RoutineForm,
    RoutineItemForm,
)
from .models import Routine, RoutineCategory, RoutineCheck, RoutineItem
from projects.models import Project


def _week_start_for(value: str | None) -> date:
    today = date.today()
    if value:
        try:
            parsed = date.fromisoformat(value)
            return parsed - timedelta(days=parsed.weekday())
        except ValueError:
            pass
    return today - timedelta(days=today.weekday())


def _schema_fields(item, user):
    schema = item.schema or {}
    fields = schema.get("fields") if isinstance(schema, dict) else None
    if not isinstance(fields, list):
        return []

    normalized = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        name = field.get("name")
        ftype = field.get("type", "text")
        label = field.get("label") or name
        if not name:
            continue
        options = field.get("options") or []
        if field.get("source") == "projects":
            options = list(
                Project.objects.filter(owner=user, is_archived=False)
                .order_by("name")
                .values_list("id", "name")
            )
        elif isinstance(options, list) and options and not isinstance(options[0], (list, tuple)):
            options = [(opt, opt) for opt in options]
        normalized.append(
            {
                "name": name,
                "type": ftype,
                "label": label,
                "required": bool(field.get("required")),
                "placeholder": field.get("placeholder") or "",
                "options": options,
            }
        )
    return normalized


def _extract_schema_data(item, user, data):
    fields = _schema_fields(item, user)
    if not fields:
        return {}
    result = {}
    for field in fields:
        key = f"data_{field['name']}"
        raw = data.get(key)
        if raw is None:
            continue
        if field["type"] == "number":
            try:
                result[field["name"]] = float(raw)
            except ValueError:
                continue
        elif field["type"] == "checkbox":
            result[field["name"]] = raw in {"on", "true", "1"}
        else:
            result[field["name"]] = raw.strip() if isinstance(raw, str) else raw
    return result


def _format_data_value(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return "Si" if value else "No"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value)
    if isinstance(value, (list, tuple)):
        cleaned = [str(entry).strip() for entry in value if str(entry).strip()]
        return ", ".join(cleaned) if cleaned else None
    text = str(value).strip()
    return text or None


def _build_data_rows(schema_fields, data):
    if not isinstance(data, dict) or not data:
        return []

    rows = []
    handled_keys = set()
    for field in schema_fields:
        name = field.get("name")
        if not name or name not in data:
            continue
        formatted = _format_data_value(data.get(name))
        if formatted is None:
            continue
        rows.append({"label": field.get("label") or name, "value": formatted})
        handled_keys.add(name)

    for key, raw in data.items():
        if key in handled_keys:
            continue
        formatted = _format_data_value(raw)
        if formatted is None:
            continue
        rows.append({"label": key.replace("_", " ").capitalize(), "value": formatted})

    return rows


def _resolve_category(user, raw_value):
    raw = (raw_value or "").strip()
    if not raw.isdigit():
        return None
    return RoutineCategory.objects.filter(owner=user, is_active=True, id=int(raw)).first()


def _dashboard_redirect_url(week_start: date, category: RoutineCategory | None):
    query = f"week={week_start.isoformat()}"
    if category is not None:
        query += f"&category={category.id}"
    return f"/routines/?{query}"


def _week_stats(owner, week_start: date):
    counts = (
        RoutineCheck.objects.filter(owner=owner, week_start=week_start)
        .values("status")
        .annotate(total=Count("id"))
    )
    count_map = {row["status"]: row["total"] for row in counts}
    return {
        "planned": count_map.get(RoutineCheck.Status.PLANNED, 0),
        "done": count_map.get(RoutineCheck.Status.DONE, 0),
        "skipped": count_map.get(RoutineCheck.Status.SKIPPED, 0),
    }


def _completion_rate(done: int, total: int):
    if total <= 0:
        return 0.0
    return round((done * 100.0) / total, 1)

@login_required
def dashboard(request):
    user = request.user
    requested_week = request.POST.get("week") if request.method == "POST" else request.GET.get("week")
    week_start = _week_start_for(requested_week)
    week_end = week_start + timedelta(days=6)
    today = date.today()
    selected_category_raw = request.POST.get("category") if request.method == "POST" else request.GET.get("category")
    selected_category = _resolve_category(user, selected_category_raw)

    active_quick_form = ""
    quick_routine_form = QuickRoutineForm(owner=user)
    quick_item_form = QuickRoutineItemForm(
        owner=user,
        category=selected_category,
        initial={"weekday": str(today.weekday())},
    )

    if request.method == "POST":
        quick_action = (request.POST.get("quick_action") or "").strip()
        if quick_action == "add_routine":
            active_quick_form = "routine"
            quick_routine_form = QuickRoutineForm(request.POST, owner=user)
            quick_item_form = QuickRoutineItemForm(
                owner=user,
                category=selected_category,
                initial={"weekday": str(today.weekday())},
            )
            if quick_routine_form.is_valid():
                name = (quick_routine_form.cleaned_data.get("name") or "").strip()
                description = (quick_routine_form.cleaned_data.get("description") or "").strip()
                routine, created = Routine.objects.get_or_create(
                    owner=user,
                    name=name,
                    defaults={
                        "description": description,
                        "is_active": True,
                    },
                )
                if not created:
                    updates = []
                    if description and routine.description != description:
                        routine.description = description
                        updates.append("description")
                    if not routine.is_active:
                        routine.is_active = True
                        updates.append("is_active")
                    if updates:
                        routine.save(update_fields=updates)
                return redirect(_dashboard_redirect_url(week_start, selected_category))

        elif quick_action == "add_item":
            active_quick_form = "item"
            quick_item_form = QuickRoutineItemForm(request.POST, owner=user, category=selected_category)
            quick_routine_form = QuickRoutineForm(owner=user)
            if quick_item_form.is_valid():
                quick_item_form.save(owner=user)
                return redirect(_dashboard_redirect_url(week_start, selected_category))

    categories = RoutineCategory.objects.filter(owner=user, is_active=True).order_by("name")
    routines = Routine.objects.filter(owner=user, is_active=True).order_by("name")

    items = (
        RoutineItem.objects.filter(owner=user, is_active=True, routine__in=routines)
        .select_related("routine", "category")
        .order_by("weekday", "time_start", "time_end", "title")
    )
    if selected_category is not None:
        items = items.filter(category=selected_category)
        routines = routines.filter(id__in=items.values_list("routine_id", flat=True).distinct())

    checks = RoutineCheck.objects.filter(owner=user, week_start=week_start, item__in=items)
    check_map = {check.item_id: check for check in checks}

    # Auto-skip past days for current week (only if no check exists yet)
    current_week_start = today - timedelta(days=today.weekday())
    if week_start == current_week_start:
        past_items = [item for item in items if item.weekday < today.weekday()]
        missing = [item for item in past_items if item.id not in check_map]
        if missing:
            RoutineCheck.objects.bulk_create(
                [
                    RoutineCheck(
                        owner=user,
                        item=item,
                        week_start=week_start,
                        status=RoutineCheck.Status.SKIPPED,
                    )
                    for item in missing
                ]
            )
            checks = RoutineCheck.objects.filter(owner=user, week_start=week_start, item__in=items)
            check_map = {check.item_id: check for check in checks}

    weekdays = [
        (0, "Lun"),
        (1, "Mar"),
        (2, "Mer"),
        (3, "Gio"),
        (4, "Ven"),
        (5, "Sab"),
        (6, "Dom"),
    ]
    week_days = [
        {
            "index": idx,
            "label": label,
            "date": week_start + timedelta(days=idx),
        }
        for idx, label in weekdays
    ]

    grouped = {idx: [] for idx, _ in weekdays}
    for item in items:
        check = check_map.get(item.id)
        status = check.status if check else RoutineCheck.Status.PLANNED
        schema_fields = _schema_fields(item, user)
        data = check.data if check else {}
        grouped[item.weekday].append({
            "item": item,
            "status": status,
            "data": data,
            "schema_fields": schema_fields,
            "data_rows": _build_data_rows(schema_fields, data),
        })

    stats = _week_stats(user, week_start)
    today_stats = {
        "total": 0,
        "planned": 0,
        "done": 0,
        "skipped": 0,
    }
    if week_start <= today <= week_end:
        today_items = grouped.get(today.weekday(), [])
        today_stats["total"] = len(today_items)
        for entry in today_items:
            status = (entry.get("status") or "").upper()
            if status == RoutineCheck.Status.DONE:
                today_stats["done"] += 1
            elif status == RoutineCheck.Status.SKIPPED:
                today_stats["skipped"] += 1
            else:
                today_stats["planned"] += 1

    context = {
        "week_start": week_start,
        "week_end": week_end,
        "today": today,
        "week_days": week_days,
        "grouped": grouped,
        "routines": routines,
        "categories": categories,
        "selected_category": selected_category,
        "category_query": f"&category={selected_category.id}" if selected_category is not None else "",
        "stats": stats,
        "today_stats": today_stats,
        "prev_week": (week_start - timedelta(days=7)).isoformat(),
        "next_week": (week_start + timedelta(days=7)).isoformat(),
        "quick_routine_form": quick_routine_form,
        "quick_item_form": quick_item_form,
        "active_quick_form": active_quick_form,
    }
    return render(request, "routines/dashboard.html", context)


@login_required
def check_item(request):
    is_htmx = request.headers.get("HX-Request") == "true"
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if request.method != "POST":
        if is_htmx:
            return HttpResponse(status=405)
        if is_ajax:
            return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)
        return redirect("/routines/")

    item_id = request.POST.get("item_id")
    week_start = _week_start_for(request.POST.get("week"))
    status = (request.POST.get("status") or "").strip()

    item = get_object_or_404(RoutineItem, id=item_id, owner=request.user)
    check, _ = RoutineCheck.objects.get_or_create(
        owner=request.user,
        item=item,
        week_start=week_start,
        defaults={"status": RoutineCheck.Status.PLANNED},
    )

    allowed_statuses = {RoutineCheck.Status.PLANNED, RoutineCheck.Status.DONE, RoutineCheck.Status.SKIPPED}
    if status not in allowed_statuses:
        if is_ajax:
            return JsonResponse({"ok": False, "error": "invalid_status"}, status=400)
        return redirect(f"/routines/?week={week_start.isoformat()}")

    check.status = status
    check.data = _extract_schema_data(item, request.user, request.POST)
    check.save(update_fields=["status", "data"])

    stats = _week_stats(request.user, week_start)
    schema_fields = _schema_fields(item, request.user)
    data_rows = _build_data_rows(schema_fields, check.data)

    if is_htmx:
        context = {
            "item": item,
            "status": check.status,
            "stats": stats,
            "data": check.data,
            "data_rows": data_rows,
        }
        return render(request, "routines/partials/check_item_oob.html", context)

    if is_ajax:
        return JsonResponse(
            {
                "ok": True,
                "item_id": item.id,
                "status": check.status,
                "stats": stats,
            }
        )

    return redirect(f"/routines/?week={week_start.isoformat()}")


@login_required
def stats(request):
    user = request.user
    week_start = _week_start_for(request.GET.get("week"))
    week_end = week_start + timedelta(days=6)

    routine_options = Routine.objects.filter(owner=user).order_by("name")
    selected_routine = None
    selected_routine_raw = (request.GET.get("routine") or "").strip()
    if selected_routine_raw.isdigit():
        selected_routine = routine_options.filter(id=int(selected_routine_raw)).first()

    checks_qs = RoutineCheck.objects.filter(owner=user).select_related("item__routine")
    if selected_routine is not None:
        checks_qs = checks_qs.filter(item__routine=selected_routine)

    stats_agg = {
        "total": Count("id"),
        "done": Count("id", filter=Q(status=RoutineCheck.Status.DONE)),
        "planned": Count("id", filter=Q(status=RoutineCheck.Status.PLANNED)),
        "skipped": Count("id", filter=Q(status=RoutineCheck.Status.SKIPPED)),
    }

    overall_raw = checks_qs.aggregate(**stats_agg)
    overall_total = overall_raw.get("total") or 0
    overall_done = overall_raw.get("done") or 0
    overall_planned = overall_raw.get("planned") or 0
    overall_skipped = overall_raw.get("skipped") or 0
    overall_stats = {
        "total": overall_total,
        "done": overall_done,
        "planned": overall_planned,
        "skipped": overall_skipped,
        "completion_rate": _completion_rate(overall_done, overall_total),
    }

    week_raw = checks_qs.filter(week_start=week_start).aggregate(**stats_agg)
    week_total = week_raw.get("total") or 0
    week_done = week_raw.get("done") or 0
    week_planned = week_raw.get("planned") or 0
    week_skipped = week_raw.get("skipped") or 0
    week_stats = {
        "total": week_total,
        "done": week_done,
        "planned": week_planned,
        "skipped": week_skipped,
        "completion_rate": _completion_rate(week_done, week_total),
    }

    trend_weeks = 8
    trend_start = week_start - timedelta(days=7 * (trend_weeks - 1))
    weekly_rows = (
        checks_qs.filter(week_start__range=(trend_start, week_start))
        .values("week_start")
        .annotate(**stats_agg)
        .order_by("week_start")
    )
    weekly_map = {row["week_start"]: row for row in weekly_rows}
    trend = []
    for idx in range(trend_weeks):
        current_week = trend_start + timedelta(days=7 * idx)
        row = weekly_map.get(current_week) or {}
        total = row.get("total") or 0
        done = row.get("done") or 0
        planned = row.get("planned") or 0
        skipped = row.get("skipped") or 0
        trend.append(
            {
                "week_start": current_week,
                "week_end": current_week + timedelta(days=6),
                "total": total,
                "done": done,
                "planned": planned,
                "skipped": skipped,
                "completion_rate": _completion_rate(done, total),
            }
        )

    routine_rows = (
        checks_qs.values("item__routine__name")
        .annotate(**stats_agg)
        .order_by("-done", "-total", "item__routine__name")
    )
    routine_stats = []
    for row in routine_rows:
        total = row.get("total") or 0
        done = row.get("done") or 0
        routine_stats.append(
            {
                "name": row.get("item__routine__name") or "Routine",
                "total": total,
                "done": done,
                "planned": row.get("planned") or 0,
                "skipped": row.get("skipped") or 0,
                "completion_rate": _completion_rate(done, total),
            }
        )

    context = {
        "week_start": week_start,
        "week_end": week_end,
        "prev_week": (week_start - timedelta(days=7)).isoformat(),
        "next_week": (week_start + timedelta(days=7)).isoformat(),
        "routine_query": f"&routine={selected_routine.id}" if selected_routine is not None else "",
        "routine_options": routine_options,
        "selected_routine": selected_routine,
        "overall_stats": overall_stats,
        "week_stats": week_stats,
        "trend": trend,
        "routine_stats": routine_stats,
        "active_routines": Routine.objects.filter(owner=user, is_active=True).count(),
        "active_items": RoutineItem.objects.filter(owner=user, is_active=True).count(),
    }
    return render(request, "routines/stats.html", context)


@login_required
def add_routine(request):
    if request.method == "POST":
        form = RoutineForm(request.POST, owner=request.user)
        if form.is_valid():
            routine = form.save(commit=False)
            routine.owner = request.user
            routine.save()
            return redirect("/routines/")
    else:
        form = RoutineForm(owner=request.user)
    return render(request, "routines/add_routine.html", {"form": form})


@login_required
def update_routine(request):
    routine_id = request.GET.get("id")
    routine = None
    if routine_id:
        routine = get_object_or_404(Routine, id=routine_id, owner=request.user)
        if request.method == "POST":
            form = RoutineForm(request.POST, instance=routine, owner=request.user)
            if form.is_valid():
                form.save()
                return redirect("/routines/")
        else:
            form = RoutineForm(instance=routine, owner=request.user)
        return render(request, "routines/update_routine.html", {"form": form, "routine": routine})

    routines = Routine.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "routines/update_routine.html", {"routines": routines})


@login_required
def remove_routine(request):
    routine_id = request.GET.get("id")
    routine = None
    if routine_id:
        routine = get_object_or_404(Routine, id=routine_id, owner=request.user)
        if request.method == "POST":
            routine.delete()
            return redirect("/routines/")
    routines = Routine.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "routines/remove_routine.html", {"routine": routine, "routines": routines})


@login_required
def add_item(request):
    if request.method == "POST":
        form = RoutineItemForm(request.POST, owner=request.user)
        if form.is_valid():
            weekday = form.cleaned_data["weekday"]
            if getattr(form, "_weekday_all", False):
                routine = form.resolve_routine()
                if routine is None:
                    form.add_error("routine_choice", "Seleziona una routine valida.")
                    return render(request, "routines/add_item.html", {"form": form})
                category = form.resolve_category()
                project = form.resolve_project()
                items = []
                for value, _label in RoutineItem.Weekday.choices:
                    items.append(
                        RoutineItem(
                            owner=request.user,
                            routine=routine,
                            category=category,
                            project=project,
                            title=form.cleaned_data["title"],
                            weekday=value,
                            time_start=form.cleaned_data.get("time_start"),
                            time_end=form.cleaned_data.get("time_end"),
                            note=form.cleaned_data.get("note", ""),
                            schema=form.cleaned_data.get("schema") or {},
                            is_active=form.cleaned_data.get("is_active", True),
                        )
                    )
                RoutineItem.objects.bulk_create(items)
            else:
                item = form.save(commit=False)
                item.owner = request.user
                item.weekday = weekday
                item.save()
            return redirect("/routines/")
    else:
        initial = {}
        project_id = request.GET.get("project")
        if project_id:
            project = get_object_or_404(Project, id=project_id, owner=request.user)
            initial["project"] = project
        form = RoutineItemForm(owner=request.user, initial=initial)
    return render(request, "routines/add_item.html", {"form": form})


@login_required
def update_item(request):
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(RoutineItem, id=item_id, owner=request.user)
        if request.method == "POST":
            form = RoutineItemForm(request.POST, instance=item, owner=request.user)
            if form.is_valid():
                updated = form.save(commit=False)
                updated.weekday = int(form.cleaned_data["weekday"])
                updated.save()
                return redirect("/routines/")
        else:
            form = RoutineItemForm(instance=item, owner=request.user)
        return render(request, "routines/update_item.html", {"form": form, "item": item})

    items = RoutineItem.objects.filter(owner=request.user).order_by("-created_at")[:20]
    return render(request, "routines/update_item.html", {"items": items})


@login_required
def remove_item(request):
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(RoutineItem, id=item_id, owner=request.user)
        if request.method == "POST":
            item.delete()
            return redirect("/routines/")
    items = RoutineItem.objects.filter(owner=request.user).order_by("-created_at")[:20]
    return render(request, "routines/remove_item.html", {"item": item, "items": items})
