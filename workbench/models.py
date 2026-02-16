from django.conf import settings
from django.db import models

from common.models import OwnedModel, TimeStampedModel


class WorkbenchItem(OwnedModel, TimeStampedModel):
    class Kind(models.TextChoices):
        IMPORT = "IMPORT", "Import"
        REPORT = "REPORT", "Report"
        DEBUG = "DEBUG", "Debug"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        DONE = "DONE", "Done"

    title = models.CharField(max_length=160)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.DEBUG)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    note = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["owner", "kind"]),
        ]

    def __str__(self):
        return self.title


class DebugChangeLog(models.Model):
    """
    Storico cambiamenti per il Workbench.
    Usato solo quando il middleware debug e attivo.
    """
    class Action(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        CUSTOM = "CUSTOM", "Custom"

    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="debug_change_logs",
    )
    source = models.CharField(max_length=120, blank=True)
    action = models.CharField(max_length=10, choices=Action.choices, default=Action.UPDATE)
    app_label = models.CharField(max_length=80, blank=True)
    model_name = models.CharField(max_length=80, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["app_label", "model_name", "object_id"]),
        ]

    def __str__(self):
        return f"{self.action} {self.app_label}.{self.model_name}#{self.object_id}"
