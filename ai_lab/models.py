from django.db import models

from common.models import OwnedModel, TimeStampedModel


class LabEntry(OwnedModel, TimeStampedModel):
    class Area(models.TextChoices):
        FOUNDATIONS = "FOUNDATIONS", "Fondamentali"
        PROMPTING = "PROMPTING", "Prompting"
        EMBEDDINGS = "EMBEDDINGS", "Embeddings"
        RAG = "RAG", "RAG"
        VECTOR_DB = "VECTOR_DB", "Vector DB"
        EXPERIMENT = "EXPERIMENT", "Esperimento libero"

    class Status(models.TextChoices):
        TODO = "TODO", "Da studiare"
        LEARNING = "LEARNING", "In studio"
        TESTING = "TESTING", "In test"
        APPLIED = "APPLIED", "Applicato"

    title = models.CharField(max_length=140)
    area = models.CharField(max_length=20, choices=Area.choices, default=Area.FOUNDATIONS)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    prompt = models.TextField(blank=True)
    result = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    next_step = models.CharField(max_length=220, blank=True)
    resource_url = models.URLField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "area", "status"]),
            models.Index(fields=["owner", "updated_at"]),
        ]

    def __str__(self):
        return self.title
