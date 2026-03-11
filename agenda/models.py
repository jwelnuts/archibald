from django.db import models

from common.models import OwnedModel, TimeStampedModel


class AgendaItem(OwnedModel, TimeStampedModel):
    class ItemType(models.TextChoices):
        ACTIVITY = "ACTIVITY", "Attivita"
        REMINDER = "REMINDER", "Reminder"

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Pianificata"
        DONE = "DONE", "Completata"

    title = models.CharField(max_length=200)
    item_type = models.CharField(max_length=10, choices=ItemType.choices, default=ItemType.ACTIVITY)
    due_date = models.DateField()
    due_time = models.TimeField(null=True, blank=True)
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="agenda_items",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PLANNED)
    note = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "due_date"]),
            models.Index(fields=["owner", "item_type"]),
            models.Index(fields=["owner", "status"]),
        ]

    def __str__(self):
        return self.title


class WorkLog(OwnedModel, TimeStampedModel):
    work_date = models.DateField()
    time_start = models.TimeField(null=True, blank=True)
    time_end = models.TimeField(null=True, blank=True)
    lunch_break_minutes = models.PositiveSmallIntegerField(default=0)
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "work_date"], name="agenda_one_worklog_per_day"),
        ]
        indexes = [
            models.Index(fields=["owner", "work_date"]),
        ]

    def __str__(self):
        return f"{self.owner_id} {self.work_date} ({self.hours})"
