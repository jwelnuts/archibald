import json
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    TodoListForm,
    TodoItemForm,
    QuickTodoListForm,
    QuickTodoItemForm,
)
from .models import TodoList, TodoCategory, TodoItem, TodoRecurrence


def _resolve_category(user, raw_id):
    if not raw_id:
        return None
    try:
        return TodoCategory.objects.get(id=raw_id, owner=user)
    except (TodoCategory.DoesNotExist, ValueError, TypeError):
        return None


def _schema_fields(item, user):
    schema = item.schema or {}
    return schema.get("fields", [])


def _build_data_rows(fields, data):
    rows = []
    for f in fields:
        slug = f.get("slug")
        label = f.get("label", slug)
        value = data.get(slug, "")
        rows.append({"label": label, "value": value})
    return rows


def _week_stats(user, week_start):
    checks = TodoRecurrence.objects.filter(owner=user, week_start=week_start)
    return {
        "planned": checks.filter(status=TodoRecurrence.Status.PLANNED).count(),
        "done": checks.filter(status=TodoRecurrence.Status.DONE).count(),
        "skipped": checks.filter(status=TodoRecurrence.Status.SKIPPED).count(),
    }


@login_required
def dashboard(request):
    user = request.user
    today = timezone.now().date()

    week_raw = request.GET.get("week")
    if week_raw:
        try:
            week_start = date.fromisoformat(week_raw)
        except ValueError:
            week_start = today - timedelta(days=today.weekday())
    else:
        week_start = today - timedelta(days=today.weekday())

    selected_category_raw = request.POST.get("category") if request.method == "POST" else request.GET.get("category")
    selected_category = _resolve_category(user, selected_category_raw)

    tab = (request.GET.get("tab") or "todos").strip().lower()
    if tab not in ("todos", "tasks"):
        tab = "todos"

    active_quick_form = ""
    quick_todo_list_form = QuickTodoListForm(owner=user)
    quick_item_form = QuickTodoItemForm(
        owner=user,
        category=selected_category,
        initial={"weekday": str(today.weekday())}
    )

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_list":
            f = QuickTodoListForm(request.POST, owner=user)
            if f.is_valid():
                TodoList.objects.create(
                    owner=user,
                    name=f.cleaned_data["name"],
                    description=f.cleaned_data["description"],
                )
                return redirect(f"/todos/?week={week_start.isoformat()}")
            else:
                quick_todo_list_form = f
                active_quick_form = "add_list"
        elif action == "add_item":
            f = QuickTodoItemForm(request.POST, owner=user)
            if f.is_valid():
                f.save(owner=user)
                return redirect(f"/todos/?week={week_start.isoformat()}")
            else:
                quick_item_form = f
                active_quick_form = "add_item"

    categories = TodoCategory.objects.filter(owner=user, is_active=True).order_by("name")
    todo_lists = TodoList.objects.filter(owner=user, is_active=True).order_by("name")

    # Recurring items
    recurring_items = (
        TodoItem.objects.filter(owner=user, is_active=True, todo_list__in=todo_lists, is_standalone=False)
        .select_related("todo_list", "category")
        .order_by("weekday", "time_start", "time_end", "title")
    )
    if selected_category is not None:
        recurring_items = recurring_items.filter(category=selected_category)
        todo_lists = todo_lists.filter(id__in=recurring_items.values_list("todo_list_id", flat=True).distinct())

    recurrences = TodoRecurrence.objects.filter(owner=user, week_start=week_start, todo_item__in=recurring_items)
    recurrence_map = {rec.todo_item_id: rec for rec in recurrences}

    # Auto-skip past days
    current_week_start = today - timedelta(days=today.weekday())
    if week_start == current_week_start:
        past_items = [item for item in recurring_items if item.weekday < today.weekday()]
        missing = [item for item in past_items if item.id not in recurrence_map]
        if missing:
            TodoRecurrence.objects.bulk_create(
                [
                    TodoRecurrence(
                        owner=user,
                        todo_item=item,
                        week_start=week_start,
                        status=TodoRecurrence.Status.SKIPPED,
                    )
                    for item in missing
                ]
            )
            recurrences = TodoRecurrence.objects.filter(owner=user, week_start=week_start, todo_item__in=recurring_items)
            recurrence_map = {rec.todo_item_id: rec for rec in recurrences}

    weekdays = [
        (0, "Lunedì"), (1, "Martedì"), (2, "Mercoledì"),
        (3, "Giovedì"), (4, "Venerdì"), (5, "Sabato"), (6, "Domenica")
    ]

    grouped = {idx: [] for idx, _ in weekdays}
    for item in recurring_items:
        rec = recurrence_map.get(item.id)
        status = rec.status if rec else TodoRecurrence.Status.PLANNED
        schema_fields = _schema_fields(item, user)
        data = rec.data if rec else {}
        grouped[item.weekday].append({
            "item": item,
            "status": status,
            "is_todo": True,
            "data": data,
            "schema_fields": schema_fields,
            "data_rows": _build_data_rows(schema_fields, data),
        })

    # Standalone items
    standalone_items = (
        TodoItem.objects.filter(owner=user, is_active=True, is_standalone=True)
        .select_related("todo_list", "category", "project")
        .exclude(due_date__isnull=True)
        .order_by("due_date", "due_time", "title")
    )
    if selected_category is not None:
        standalone_items = standalone_items.filter(category=selected_category)

    standalone_entries = []
    for item in standalone_items:
        effective_status = item.status or "OPEN"
        is_done = effective_status in ("DONE",)
        is_overdue = (
            item.due_date is not None
            and item.due_date < today
            and not is_done
        )
        is_today_item = item.due_date == today
        standalone_entries.append({
            "item": item,
            "status": effective_status,
            "is_todo": False,
            "is_overdue": is_overdue,
            "is_today_item": is_today_item,
            "data": {},
            "schema_fields": [],
            "data_rows": [],
        })

    task_counts = {
        "total": len(standalone_entries),
        "open": sum(1 for e in standalone_entries if e["status"] == "OPEN"),
        "in_progress": sum(1 for e in standalone_entries if e["status"] == "IN_PROGRESS"),
        "done": sum(1 for e in standalone_entries if e["status"] == "DONE"),
        "overdue": sum(1 for e in standalone_entries if e["is_overdue"]),
        "today": sum(1 for e in standalone_entries if e["is_today_item"]),
    }

    stats = _week_stats(user, week_start)

    context = {
        "week_start": week_start,
        "week_end": week_start + timedelta(days=6),
        "weekdays": weekdays,
        "grouped": grouped,
        "categories": categories,
        "selected_category": selected_category,
        "todo_lists": todo_lists,
        "stats": stats,
        "quick_todo_list_form": quick_todo_list_form,
        "quick_item_form": quick_item_form,
        "active_quick_form": active_quick_form,
        "tab": tab,
        "task_counts": task_counts,
        "standalone_entries": standalone_entries,
    }
    return render(request, "todos/dashboard.html", context)


@login_required
def stats(request):
    user = request.user
    # Simplified stats for now
    return render(request, "todos/stats.html")


@login_required
def check_item(request):
    if request.method != "POST":
        return redirect("/todos/")

    item_id = request.POST.get("item_id")
    status = request.POST.get("status")
    week_raw = request.POST.get("week")

    if not item_id or not status or not week_raw:
        return redirect("/todos/")

    item = get_object_or_404(TodoItem, id=item_id, owner=request.user)
    week_start = date.fromisoformat(week_raw)

    rec, created = TodoRecurrence.objects.get_or_create(
        owner=request.user,
        todo_item=item,
        week_start=week_start,
        defaults={"status": status}
    )
    if not created:
        rec.status = status
        rec.save(update_fields=["status", "updated_at"])

    if request.headers.get("HX-Request") == "true":
        return render(request, "todos/partials/check_item_oob.html", {
            "item": item,
            "status": status,
            "week_start": week_start,
            "stats": _week_stats(request.user, week_start),
        })

    return redirect(f"/todos/?week={week_raw}")


@login_required
def add_list(request):
    if request.method == "POST":
        form = TodoListForm(request.POST, owner=request.user)
        if form.is_valid():
            lst = form.save(commit=False)
            lst.owner = request.user
            lst.save()
            return redirect("/todos/")
    else:
        form = TodoListForm(owner=request.user)
    return render(request, "todos/add_todo_list.html", {"form": form})


@login_required
def update_list(request):
    lst_id = request.GET.get("id")
    lst = get_object_or_404(TodoList, id=lst_id, owner=request.user)
    if request.method == "POST":
        form = TodoListForm(request.POST, instance=lst, owner=request.user)
        if form.is_valid():
            form.save()
            return redirect("/todos/")
    else:
        form = TodoListForm(instance=lst, owner=request.user)
    return render(request, "todos/update_todo_list.html", {"form": form, "todo_list": lst})


@login_required
def remove_list(request):
    lst_id = request.GET.get("id")
    lst = get_object_or_404(TodoList, id=lst_id, owner=request.user)
    if request.method == "POST":
        lst.delete()
        return redirect("/todos/")
    return render(request, "todos/remove_todo_list.html", {"todo_list": lst})


@login_required
def add_item(request):
    if request.method == "POST":
        form = TodoItemForm(request.POST, owner=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            return redirect("/todos/")
    else:
        form = TodoItemForm(owner=request.user)
    return render(request, "todos/add_item.html", {"form": form})


@login_required
def update_item(request):
    item_id = request.GET.get("id")
    item = get_object_or_404(TodoItem, id=item_id, owner=request.user)
    if request.method == "POST":
        form = TodoItemForm(request.POST, instance=item, owner=request.user)
        if form.is_valid():
            form.save()
            return redirect("/todos/")
    else:
        form = TodoItemForm(instance=item, owner=request.user)
    return render(request, "todos/update_item.html", {"form": form, "item": item})


@login_required
def remove_item(request):
    item_id = request.GET.get("id")
    item = get_object_or_404(TodoItem, id=item_id, owner=request.user)
    if request.method == "POST":
        item.delete()
        return redirect("/todos/")
    return render(request, "todos/remove_item.html", {"item": item})


@login_required
def api_add_task(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)

    form = TodoItemForm(request.POST, owner=request.user)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": dict(form.errors)}, status=400)

    item = form.save(commit=False)
    item.owner = request.user
    item.is_standalone = True
    item.save()

    return JsonResponse({
        "ok": True,
        "item": {
            "id": item.id,
            "title": item.title,
            "due_date": str(item.due_date) if item.due_date else None,
            "status": item.status or "OPEN",
        },
    })


@login_required
def api_update_task(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)

    item_id = request.POST.get("id")
    item = get_object_or_404(TodoItem, id=item_id, owner=request.user)
    form = TodoItemForm(request.POST, instance=item, owner=request.user)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": dict(form.errors)}, status=400)

    updated_item = form.save()
    return JsonResponse({
        "ok": True,
        "item": {
            "id": updated_item.id,
            "title": updated_item.title,
            "due_date": str(updated_item.due_date) if updated_item.due_date else None,
            "status": updated_item.status or "OPEN",
        },
    })


@login_required
def api_remove_task(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)

    item_id = request.POST.get("id")
    item = get_object_or_404(TodoItem, id=item_id, owner=request.user)
    item.delete()
    return JsonResponse({"ok": True})


@login_required
def api_set_task_status(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)

    item_id = request.POST.get("id")
    status = (request.POST.get("status") or "").strip().upper()
    allowed = {"OPEN", "IN_PROGRESS", "DONE"}
    if status not in allowed:
        return JsonResponse({"ok": False, "error": "invalid_status"}, status=400)

    item = get_object_or_404(TodoItem, id=item_id, owner=request.user)
    item.status = status
    item.save(update_fields=["status", "updated_at"])

    return JsonResponse({"ok": True, "status": status})
