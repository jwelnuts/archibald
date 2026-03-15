from django.db import models

from common.models import OwnedModel, TimeStampedModel


class MemoryStockItem(OwnedModel, TimeStampedModel):
    title = models.CharField(max_length=220)
    source_url = models.URLField(blank=True)
    note = models.TextField(blank=True)

    source_sender = models.EmailField(blank=True)
    source_subject = models.CharField(max_length=255, blank=True)
    source_message_id = models.CharField(max_length=255, blank=True)
    source_action = models.CharField(max_length=64, blank=True)

    metadata = models.JSONField(default=dict, blank=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "is_archived", "created_at"]),
            models.Index(fields=["owner", "source_message_id"]),
            models.Index(fields=["owner", "updated_at"]),
        ]

    def __str__(self):
        return self.title
