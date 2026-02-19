from django.db import models

from common.models import OwnedModel, TimeStampedModel

from .crypto import decrypt_text, encrypt_text


class VaultProfile(OwnedModel, TimeStampedModel):
    totp_secret_encrypted = models.TextField(blank=True)
    totp_enabled_at = models.DateTimeField(null=True, blank=True)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner"], name="vault_unique_owner_profile"),
        ]

    def set_totp_secret(self, secret: str) -> None:
        self.totp_secret_encrypted = encrypt_text(secret)

    def get_totp_secret(self) -> str:
        return decrypt_text(self.totp_secret_encrypted)

    def __str__(self):
        return f"VaultProfile({self.owner_id})"


class VaultItem(OwnedModel, TimeStampedModel):
    class Kind(models.TextChoices):
        PASSWORD = "PASSWORD", "Password"
        NOTE = "NOTE", "Nota privata"

    title = models.CharField(max_length=160)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.NOTE)
    login = models.CharField(max_length=120, blank=True)
    website_url = models.URLField(blank=True)
    secret_encrypted = models.TextField(blank=True)
    notes_encrypted = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "kind", "updated_at"]),
        ]

    def set_secret_value(self, raw_value: str) -> None:
        self.secret_encrypted = encrypt_text(raw_value or "")

    def get_secret_value(self) -> str:
        return decrypt_text(self.secret_encrypted)

    def set_notes_value(self, raw_value: str) -> None:
        self.notes_encrypted = encrypt_text(raw_value or "")

    def get_notes_value(self) -> str:
        return decrypt_text(self.notes_encrypted)

    def masked_secret(self) -> str:
        raw = self.get_secret_value()
        if not raw:
            return "-"
        if len(raw) <= 4:
            return "*" * len(raw)
        return f"{raw[:2]}{'*' * (len(raw) - 4)}{raw[-2:]}"

    def __str__(self):
        return self.title
