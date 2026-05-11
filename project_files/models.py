from django.db import models

from common.models import OwnedModel, TimeStampedModel


def project_file_upload_to(instance, filename):
    return f"project_files/{instance.owner_id}/{instance.project_id}/{filename}"


class ProjectFile(OwnedModel, TimeStampedModel):
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="files",
    )
    file = models.FileField(upload_to=project_file_upload_to)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "project", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
