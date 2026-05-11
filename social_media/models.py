from django.db import models

from common.models import OwnedModel, TimeStampedModel


def social_post_media_upload_to(instance, filename):
    return f"social_media/{instance.owner_id}/{instance.project_id}/{filename}"


class SocialChannel(OwnedModel, TimeStampedModel):
    class Platform(models.TextChoices):
        INSTAGRAM = "instagram", "Instagram"
        LINKEDIN = "linkedin", "LinkedIn"
        FACEBOOK = "facebook", "Facebook"
        TWITTER = "twitter", "X (Twitter)"
        TIKTOK = "tiktok", "TikTok"
        YOUTUBE = "youtube", "YouTube"
        PINTEREST = "pinterest", "Pinterest"
        THREADS = "threads", "Threads"
        OTHER = "other", "Altro"

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="social_channels",
    )
    platform = models.CharField(max_length=20, choices=Platform.choices, default=Platform.INSTAGRAM)
    name = models.CharField(max_length=120)
    handle = models.CharField(max_length=120, blank=True)
    url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("owner", "project", "platform", "name")]
        indexes = [
            models.Index(fields=["owner", "project", "is_active"]),
            models.Index(fields=["owner", "project", "platform"]),
        ]
        ordering = ["platform", "name"]

    def __str__(self):
        return f"{self.get_platform_display()} – {self.name}"


class SocialPost(OwnedModel, TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Bozza"
        SCHEDULED = "scheduled", "Programmato"
        PUBLISHED = "published", "Pubblicato"
        ARCHIVED = "archived", "Archiviato"

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="social_posts",
    )
    channel = models.ForeignKey(
        "social_media.SocialChannel",
        on_delete=models.CASCADE,
        related_name="posts",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    content = models.TextField()
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    media_urls = models.JSONField(default=list, blank=True)
    media_file = models.FileField(upload_to=social_post_media_upload_to, blank=True, null=True)
    engagement_data = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "project", "status", "scheduled_at"]),
            models.Index(fields=["owner", "project", "status", "published_at"]),
            models.Index(fields=["owner", "project", "created_at"]),
        ]
        ordering = ["-scheduled_at", "-created_at"]

    def __str__(self):
        return f"{self.channel} – {self.content[:40]}"
