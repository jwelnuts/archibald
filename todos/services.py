from .models import TodoList, TodoCategory, TodoItem


class TodoListCrudError(Exception):
    def __init__(self, code, message=None):
        self.code = code
        self.message = message
        super().__init__(message or code)


def parse_weekday(value):
    if value is None:
        return
    try:
        val = int(value)
    except (TypeError, ValueError):
        raise TodoListCrudError("invalid_weekday")
    if val < 0 or val > 6:
        raise TodoListCrudError("invalid_weekday")


def get_todo_for_owner(*, owner, todo_id, active_only: bool = True) -> TodoList:
    qs = TodoList.objects.filter(owner=owner, id=todo_id)
    if active_only:
        qs = qs.filter(is_active=True)
    lst = qs.first()
    if lst is None:
        raise TodoListCrudError("todo_list_not_found")
    return lst


def get_category_for_owner(*, owner, category_id, active_only: bool = True) -> TodoCategory:
    qs = TodoCategory.objects.filter(owner=owner, id=category_id)
    if active_only:
        qs = qs.filter(is_active=True)
    category = qs.first()
    if category is None:
        raise TodoListCrudError("category_not_found")
    return category


def create_todo_item(
    *,
    owner,
    todo_list,
    title,
    weekday=0,
    time_start=None,
    time_end=None,
    category=None,
    project=None,
    note="",
    is_standalone=False,
) -> TodoItem:
    if not title:
        raise TodoListCrudError("missing_title")
    parse_weekday(weekday)

    return TodoItem.objects.create(
        owner=owner,
        todo_list=todo_list,
        category=category,
        project=project,
        title=title,
        weekday=weekday,
        time_start=time_start,
        time_end=time_end,
        note=note,
        is_standalone=is_standalone,
    )


def update_todo_item(
    *,
    item: TodoItem,
    todo_list,
    title,
    weekday=0,
    time_start=None,
    time_end=None,
    category=None,
    project=None,
    note="",
    is_standalone=False,
) -> TodoItem:
    if not title:
        raise TodoListCrudError("missing_title")
    parse_weekday(weekday)

    item.todo_list = todo_list
    item.category = category
    item.project = project
    item.title = title
    item.weekday = weekday
    item.time_start = time_start
    item.time_end = time_end
    item.note = note
    item.is_standalone = is_standalone

    item.save(update_fields=[
        "todo_list",
        "category",
        "project",
        "title",
        "weekday",
        "time_start",
        "time_end",
        "note",
        "is_standalone",
        "updated_at",
    ])
    return item


def delete_todo_item(*, item: TodoItem):
    item.delete()
