from django.db import models

from common.models import OwnedModel, TimeStampedModel


class Payee(OwnedModel, TimeStampedModel):
    """
    Beneficiario/Controparte: Netflix, Enel, AWS, Cliente X.
    """
    name = models.CharField(max_length=160)
    website = models.URLField(blank=True)

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [models.Index(fields=["owner", "name"])]

    def __str__(self):
        return self.name


class UserHeroActionsConfig(models.Model):
    user = models.OneToOneField(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="hero_actions_config",
    )
    config = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"HeroActionsConfig({self.user_id})"
