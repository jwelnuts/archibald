from django.db import models

from common.models import OwnedModel, TimeStampedModel


class Routine(OwnedModel, TimeStampedModel):
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
        ]

    def __str__(self):
        return self.name


class RoutineItem(OwnedModel, TimeStampedModel):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Lun"
        TUESDAY = 1, "Mar"
        WEDNESDAY = 2, "Mer"
        THURSDAY = 3, "Gio"
        FRIDAY = 4, "Ven"
        SATURDAY = 5, "Sab"
        SUNDAY = 6, "Dom"

    routine = models.ForeignKey(
        "routines.Routine",
        on_delete=models.CASCADE,
        related_name="items",
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="routine_items",
    )
    title = models.CharField(max_length=200)
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices, default=Weekday.MONDAY)
    time_start = models.TimeField(null=True, blank=True)
    time_end = models.TimeField(null=True, blank=True)
    note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    schema = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "weekday"]),
            models.Index(fields=["owner", "routine", "weekday"]),
        ]

    def __str__(self):
        return self.title


class RoutineCheck(OwnedModel, TimeStampedModel):
    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        DONE = "DONE", "Done"
        SKIPPED = "SKIPPED", "Skipped"

    item = models.ForeignKey(
        "routines.RoutineItem",
        on_delete=models.CASCADE,
        related_name="checks",
    )
    week_start = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PLANNED)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("owner", "item", "week_start")]
        indexes = [
            models.Index(fields=["owner", "week_start"]),
            models.Index(fields=["owner", "item", "week_start"]),
        ]

    def __str__(self):
        return f"{self.item.title} ({self.week_start})"
