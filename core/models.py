from django.db import models
from django.utils import timezone

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


class DavAccount(TimeStampedModel):
    user = models.OneToOneField(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="dav_account",
    )
    dav_username = models.CharField(max_length=150, unique=True)
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    password_rotated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["is_active", "dav_username"]),
        ]

    def __str__(self):
        return f"DavAccount(user={self.user_id}, username={self.dav_username})"


class DavExternalAccount(TimeStampedModel):
    owner = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="dav_external_accounts",
    )
    label = models.CharField(max_length=120, blank=True)
    dav_username = models.CharField(max_length=150, unique=True)
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    password_rotated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "is_active", "dav_username"]),
        ]

    def __str__(self):
        return f"DavExternalAccount(owner={self.owner_id}, username={self.dav_username})"


class DavTeam(OwnedModel, TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("owner", "slug")]
        indexes = [
            models.Index(fields=["owner", "is_active", "slug"]),
        ]

    def __str__(self):
        return f"DavTeam(owner={self.owner_id}, slug={self.slug})"


class DavManagedCalendar(TimeStampedModel):
    owner = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="dav_managed_calendars",
    )
    principal = models.CharField(max_length=150, default="team")
    calendar_slug = models.CharField(max_length=120)
    display_name = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("owner", "principal", "calendar_slug")]
        indexes = [
            models.Index(fields=["owner", "is_active", "principal", "calendar_slug"]),
        ]

    @property
    def collection_path(self) -> str:
        return f"{self.principal}/{self.calendar_slug}"

    def __str__(self):
        return f"DavManagedCalendar(owner={self.owner_id}, path={self.collection_path})"


class DavCalendarGrant(TimeStampedModel):
    ACCESS_READONLY = "ro"
    ACCESS_READWRITE = "rw"
    ACCESS_CHOICES = [
        (ACCESS_READONLY, "Sola lettura"),
        (ACCESS_READWRITE, "Lettura e scrittura"),
    ]

    owner = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="dav_calendar_grants",
    )
    external_account = models.ForeignKey(
        DavExternalAccount,
        on_delete=models.CASCADE,
        related_name="grants",
    )
    calendar = models.ForeignKey(
        DavManagedCalendar,
        on_delete=models.CASCADE,
        related_name="grants",
    )
    access_level = models.CharField(max_length=2, choices=ACCESS_CHOICES, default=ACCESS_READONLY)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("owner", "external_account", "calendar")]
        indexes = [
            models.Index(fields=["owner", "is_active", "access_level"]),
        ]

    def __str__(self):
        return (
            "DavCalendarGrant("
            f"owner={self.owner_id}, ext={self.external_account_id}, "
            f"calendar={self.calendar_id}, access={self.access_level}"
            ")"
        )
