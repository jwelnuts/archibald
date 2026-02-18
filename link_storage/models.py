from django.db import models

from common.models import OwnedModel, TimeStampedModel


class Link(OwnedModel, TimeStampedModel):
    url = models.CharField(max_length=160)
    CATEGORY_CHOICES = [
        ("TECNOLOGIA", "Tecnologia"),
        ("SALUTE", "Salute"),
        ("SPORT", "Sport"),
        ("INTRATTENIMENTO", "Intrattenimento"),
    ]
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, blank=True)
    importance = models.IntegerField()
    note = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "created_at"]),
        ]

    def __str__(self):
        return str(self.url)
