from django.db import models

from common.models import OwnedModel, TimeStampedModel


class Customer(OwnedModel, TimeStampedModel):
    name = models.CharField(max_length=160)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [models.Index(fields=["owner", "name"])]

    def __str__(self):
        return self.name

class Project(OwnedModel, TimeStampedModel):
    name = models.CharField(max_length=120)
    customer = models.ForeignKey(
        "projects.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="projects",
    )
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        "projects.Category", null=True, blank=True, on_delete=models.SET_NULL, related_name="projects"
    )
    is_archived = models.BooleanField(default=False)

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [
            models.Index(fields=["owner", "is_archived"]),
        ]

    def __str__(self):
        return self.name


class ProjectNote(OwnedModel, TimeStampedModel):
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="notes",
    )
    content = models.TextField()
    attachment = models.FileField(
        upload_to="projects/notes/%Y/%m/",
        blank=True,
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["owner", "project", "created_at"]),
        ]

    def __str__(self):
        return f"Note #{self.id}"


class ProjectHeroActionsConfig(models.Model):
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="project_hero_actions",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="hero_actions_configs",
    )
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("user", "project")]

    def __str__(self):
        return f"HeroActionsConfig({self.user_id}, {self.project_id})"

class Category(OwnedModel, TimeStampedModel):
    """
    Categoria generica riusabile per transazioni e abbonamenti
    (es. 'Streaming', 'Casa', 'Trasporti', 'Cloud', 'Assicurazioni').
    """
    name = models.CharField(max_length=80)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [models.Index(fields=["owner", "name"])]
        db_table = "common_category"

    def __str__(self):
        return self.name
