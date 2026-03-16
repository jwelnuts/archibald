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


class UserNavConfig(models.Model):
    user = models.OneToOneField(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="nav_config",
    )
    config = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"UserNavConfig({self.user_id})"


class MobileApiSession(TimeStampedModel):
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="mobile_api_sessions",
    )
    access_token_hash = models.CharField(max_length=64, unique=True)
    refresh_token_hash = models.CharField(max_length=64, unique=True)
    access_expires_at = models.DateTimeField()
    refresh_expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    device_label = models.CharField(max_length=120, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "revoked_at"]),
            models.Index(fields=["access_expires_at"]),
            models.Index(fields=["refresh_expires_at"]),
        ]

    def __str__(self):
        return f"MobileApiSession(user={self.user_id}, revoked={bool(self.revoked_at)})"
