from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RoutineForm, RoutineItemForm, WEEKDAY_ALL
from .models import Routine, RoutineCheck, RoutineItem
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

@login_required
def dashboard(request):
    user = request.user
    week_start = _week_start_for(request.GET.get("week"))
    week_end = week_start + timedelta(days=6)
    today = date.today()

    routines = Routine.objects.filter(owner=user, is_active=True).order_by("name")
    items = (
        RoutineItem.objects.filter(owner=user, is_active=True, routine__in=routines)
        .select_related("routine")
        .order_by("weekday", "time_start", "time_end", "title")
    )

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
        grouped[item.weekday].append({
            "item": item,
            "status": status,
            "data": check.data if check else {},
            "schema_fields": _schema_fields(item, user),
        })

    counts = RoutineCheck.objects.filter(owner=user, week_start=week_start).values("status").annotate(total=Count("id"))
    count_map = {row["status"]: row["total"] for row in counts}
    stats = {
        "planned": count_map.get(RoutineCheck.Status.PLANNED, 0),
        "done": count_map.get(RoutineCheck.Status.DONE, 0),
        "skipped": count_map.get(RoutineCheck.Status.SKIPPED, 0),
    }

    context = {
        "week_start": week_start,
        "week_end": week_end,
        "today": today,
        "week_days": week_days,
        "grouped": grouped,
        "routines": routines,
        "stats": stats,
        "prev_week": (week_start - timedelta(days=7)).isoformat(),
        "next_week": (week_start + timedelta(days=7)).isoformat(),
    }
    return render(request, "routines/dashboard.html", context)


@login_required
def check_item(request):
    if request.method != "POST":
        return redirect("/routines/")
    item_id = request.POST.get("item_id")
    week_start = _week_start_for(request.POST.get("week"))
    status = request.POST.get("status")

    item = get_object_or_404(RoutineItem, id=item_id, owner=request.user)
    check, _ = RoutineCheck.objects.get_or_create(
        owner=request.user,
        item=item,
        week_start=week_start,
        defaults={"status": RoutineCheck.Status.PLANNED},
    )
    if status in {RoutineCheck.Status.PLANNED, RoutineCheck.Status.DONE, RoutineCheck.Status.SKIPPED}:
        check.status = status
        check.data = _extract_schema_data(item, request.user, request.POST)
        check.save(update_fields=["status", "data"])
    return redirect(f"/routines/?week={week_start.isoformat()}")


@login_required
def add_routine(request):
    if request.method == "POST":
        form = RoutineForm(request.POST)
        if form.is_valid():
            routine = form.save(commit=False)
            routine.owner = request.user
            routine.save()
            return redirect("/routines/")
    else:
        form = RoutineForm()
    return render(request, "routines/add_routine.html", {"form": form})


@login_required
def update_routine(request):
    routine_id = request.GET.get("id")
    routine = None
    if routine_id:
        routine = get_object_or_404(Routine, id=routine_id, owner=request.user)
        if request.method == "POST":
            form = RoutineForm(request.POST, instance=routine)
            if form.is_valid():
                form.save()
                return redirect("/routines/")
        else:
            form = RoutineForm(instance=routine)
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
                items = []
                for value, _label in RoutineItem.Weekday.choices:
                    items.append(
                        RoutineItem(
                            owner=request.user,
                            routine=routine,
                            project=form.cleaned_data.get("project"),
                            title=form.cleaned_data["title"],
                            weekday=value,
                            time_start=form.cleaned_data.get("time_start"),
                            time_end=form.cleaned_data.get("time_end"),
                            note=form.cleaned_data.get("note", ""),
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
