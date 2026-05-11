from django.db import models

from common.models import OwnedModel, TimeStampedModel


class TodoCategory(OwnedModel, TimeStampedModel):
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
        ]

    def __str__(self):
        return self.name


class TodoList(OwnedModel, TimeStampedModel):
    category = models.ForeignKey(
        "todos.TodoCategory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="todo_lists",
    )
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
            models.Index(fields=["owner", "category"]),
        ]

    def __str__(self):
        return self.name


class TodoItem(OwnedModel, TimeStampedModel):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Lun"
        TUESDAY = 1, "Mar"
        WEDNESDAY = 2, "Mer"
        THURSDAY = 3, "Gio"
        FRIDAY = 4, "Ven"
        SATURDAY = 5, "Sab"
        SUNDAY = 6, "Dom"

    class ItemType(models.TextChoices):
        TASK = "TASK", "Task"
        REMINDER = "REMINDER", "Reminder"
        APPOINTMENT = "APPOINTMENT", "Appuntamento"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        DONE = "DONE", "Done"

    todo_list = models.ForeignKey(
        "todos.TodoList",
        on_delete=models.CASCADE,
        related_name="items",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        "todos.TodoCategory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="todo_items",
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="todo_items",
    )
    title = models.CharField(max_length=200)
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices, default=Weekday.MONDAY)
    time_start = models.TimeField(null=True, blank=True)
    time_end = models.TimeField(null=True, blank=True)
    note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    schema = models.JSONField(default=dict, blank=True)

    item_type = models.CharField(
        max_length=12,
        choices=ItemType.choices,
        default=ItemType.TASK,
    )
    due_date = models.DateField(null=True, blank=True)
    due_time = models.TimeField(null=True, blank=True)
    priority = models.CharField(
        max_length=8,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.OPEN,
    )
    is_standalone = models.BooleanField(
        default=False,
    )

    class Meta:
        indexes = [
            models.Index(fields=["owner", "weekday"]),
            models.Index(fields=["owner", "todo_list", "weekday"]),
            models.Index(fields=["owner", "category"]),
            models.Index(fields=["owner", "due_date"]),
            models.Index(fields=["owner", "item_type"]),
        ]

    def __str__(self):
        return self.title


class TodoRecurrence(OwnedModel, TimeStampedModel):
    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        DONE = "DONE", "Done"
        SKIPPED = "SKIPPED", "Skipped"

    todo_item = models.ForeignKey(
        "todos.TodoItem",
        on_delete=models.CASCADE,
        related_name="recurrences",
    )
    week_start = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PLANNED)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("owner", "todo_item", "week_start")]
        indexes = [
            models.Index(fields=["owner", "week_start"]),
            models.Index(fields=["owner", "todo_item", "week_start"]),
        ]

    def __str__(self):
        return f"{self.todo_item.title} ({self.week_start})"
