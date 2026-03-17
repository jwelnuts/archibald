from __future__ import annotations

from datetime import time

from projects.models import Project

from .models import Routine, RoutineCategory, RoutineItem


class RoutineCrudError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def parse_weekday(value) -> int:
    try:
        weekday = int(value)
    except (TypeError, ValueError):
        raise RoutineCrudError("invalid_weekday")
    if weekday < 0 or weekday > 6:
        raise RoutineCrudError("invalid_weekday")
    return weekday


def parse_time_or_none(value) -> time | None:
    if value in (None, ""):
        return None
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    try:
        parsed = time.fromisoformat(str(value).strip())
    except ValueError:
        return None
    return parsed.replace(second=0, microsecond=0)


def get_routine_for_owner(*, owner, routine_id, active_only: bool = True) -> Routine:
    qs = Routine.objects.filter(owner=owner, id=routine_id)
    if active_only:
        qs = qs.filter(is_active=True)
    routine = qs.first()
    if routine is None:
        raise RoutineCrudError("routine_not_found")
    return routine


def get_category_for_owner(*, owner, category_id, active_only: bool = True):
    if category_id in (None, "", 0, "0"):
        return None
    qs = RoutineCategory.objects.filter(owner=owner, id=category_id)
    if active_only:
        qs = qs.filter(is_active=True)
    category = qs.first()
    if category is None:
        raise RoutineCrudError("category_not_found")
    return category


def get_project_for_owner(*, owner, project_id, active_only: bool = True):
    if project_id in (None, "", 0, "0"):
        return None
    qs = Project.objects.filter(owner=owner, id=project_id)
    if active_only:
        qs = qs.filter(is_archived=False)
    project = qs.first()
    if project is None:
        raise RoutineCrudError("project_not_found")
    return project


def create_routine_item(
    *,
    owner,
    routine,
    title,
    weekday,
    category=None,
    project=None,
    time_start=None,
    time_end=None,
    note="",
    schema=None,
    is_active=True,
) -> RoutineItem:
    normalized_title = (title or "").strip()
    if not normalized_title:
        raise RoutineCrudError("missing_title")

    normalized_weekday = parse_weekday(weekday)
    normalized_time_start = parse_time_or_none(time_start)
    normalized_time_end = parse_time_or_none(time_end)

    return RoutineItem.objects.create(
        owner=owner,
        routine=routine,
        category=category,
        project=project,
        title=normalized_title,
        weekday=normalized_weekday,
        time_start=normalized_time_start,
        time_end=normalized_time_end,
        note=(note or "").strip(),
        schema=schema or {},
        is_active=bool(is_active),
    )


def update_routine_item(
    *,
    item: RoutineItem,
    routine,
    title,
    weekday,
    category=None,
    project=None,
    time_start=None,
    time_end=None,
    note="",
    schema=None,
    is_active=None,
) -> RoutineItem:
    normalized_title = (title or "").strip()
    if not normalized_title:
        raise RoutineCrudError("missing_title")

    item.routine = routine
    item.category = category
    item.project = project
    item.title = normalized_title
    item.weekday = parse_weekday(weekday)
    item.time_start = parse_time_or_none(time_start)
    item.time_end = parse_time_or_none(time_end)
    item.note = (note or "").strip()
    if schema is not None:
        item.schema = schema
    if is_active is not None:
        item.is_active = bool(is_active)

    update_fields = [
        "routine",
        "category",
        "project",
        "title",
        "weekday",
        "time_start",
        "time_end",
        "note",
        "updated_at",
    ]
    if schema is not None:
        update_fields.append("schema")
    if is_active is not None:
        update_fields.append("is_active")
    item.save(update_fields=update_fields)
    return item


def delete_routine_item(*, item: RoutineItem):
    item.delete()
