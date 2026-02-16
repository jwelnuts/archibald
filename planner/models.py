from django.db import models

from common.models import OwnedModel, TimeStampedModel


class PlannerItem(OwnedModel, TimeStampedModel):
    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        DONE = "DONE", "Done"
        SKIPPED = "SKIPPED", "Skipped"

    title = models.CharField(max_length=200)
    due_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    category = models.ForeignKey(
        "projects.Category", null=True, blank=True, on_delete=models.SET_NULL, related_name="planner_items"
    )
    project = models.ForeignKey(
        "projects.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="planner_items"
    )
    note = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PLANNED)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["owner", "due_date"]),
        ]

    def __str__(self):
        return self.title
