from django.db import models

from common.models import OwnedModel, TimeStampedModel


class ArchibaldThread(OwnedModel, TimeStampedModel):
    class Kind(models.TextChoices):
        DIARY = "DIARY", "Diario"
        TEMPORARY = "TEMPORARY", "Temporanea"

    title = models.CharField(max_length=120, default="Archibald")
    is_active = models.BooleanField(default=True)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.DIARY)
    openai_conversation_id = models.CharField(max_length=128, blank=True, default="")
    openai_last_response_id = models.CharField(max_length=128, blank=True, default="")
    openai_model = models.CharField(max_length=64, blank=True, default="")

    def __str__(self):
        return self.title


class ArchibaldMessage(OwnedModel, TimeStampedModel):
    class Role(models.TextChoices):
        SYSTEM = "SYSTEM", "System"
        USER = "USER", "User"
        ASSISTANT = "ASSISTANT", "Assistant"

    thread = models.ForeignKey(
        "archibald.ArchibaldThread",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    is_favorite = models.BooleanField(default=False)
    openai_response_id = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["owner", "thread", "created_at"]),
        ]

    def __str__(self):
        return f"{self.role} @ {self.created_at}"
