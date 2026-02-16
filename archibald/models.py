from django.db import models

from common.models import OwnedModel, TimeStampedModel


class ArchibaldThread(OwnedModel, TimeStampedModel):
    title = models.CharField(max_length=120, default="Archibald")
    is_active = models.BooleanField(default=True)

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

    class Meta:
        indexes = [
            models.Index(fields=["owner", "thread", "created_at"]),
        ]

    def __str__(self):
        return f"{self.role} @ {self.created_at}"
