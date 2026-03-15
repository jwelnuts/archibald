import os
import re

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.models import OwnedModel, TimeStampedModel


DEFAULT_ARCHIBALD_INBOX = "archibald@miorganizzo.ovh"


def default_inbox_address() -> str:
    return (os.getenv("ARCHIBALD_MAIL_DEFAULT_INBOX") or DEFAULT_ARCHIBALD_INBOX).strip()


def default_timezone_name() -> str:
    return str(getattr(settings, "TIME_ZONE", "UTC") or "UTC")


def _env_first(*keys: str) -> str:
    for key in keys:
        value = (os.getenv(key) or "").strip()
        if value:
            return value
    return ""


FLAG_TOKEN_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{0,31}$")


class ArchibaldMailboxConfig(OwnedModel, TimeStampedModel):
    inbox_address = models.EmailField(default=default_inbox_address)
    timezone_name = models.CharField(max_length=64, default=default_timezone_name)

    is_enabled = models.BooleanField(default=False)
    auto_reply_enabled = models.BooleanField(default=True)
    auto_reply_subject_prefix = models.CharField(max_length=24, default="Re:")
    auto_reply_signature = models.TextField(blank=True)
    allowed_sender_regex = models.CharField(max_length=180, blank=True)

    imap_host = models.CharField(max_length=120, blank=True)
    imap_port = models.PositiveIntegerField(default=993)
    imap_use_ssl = models.BooleanField(default=True)
    imap_username = models.CharField(max_length=180, blank=True)
    imap_password = models.CharField(max_length=255, blank=True)
    imap_mailbox = models.CharField(max_length=80, default="INBOX")

    smtp_host = models.CharField(max_length=120, blank=True)
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_use_tls = models.BooleanField(default=True)
    smtp_use_ssl = models.BooleanField(default=False)
    smtp_username = models.CharField(max_length=180, blank=True)
    smtp_password = models.CharField(max_length=255, blank=True)
    smtp_from_email = models.EmailField(blank=True)
    smtp_reply_to = models.EmailField(blank=True)

    max_inbox_emails_per_run = models.PositiveSmallIntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
    )

    notifications_enabled = models.BooleanField(default=False)
    notification_recipient = models.EmailField(blank=True)
    notification_hour = models.PositiveSmallIntegerField(
        default=8,
        validators=[MinValueValidator(0), MaxValueValidator(23)],
    )
    notification_minute = models.PositiveSmallIntegerField(
        default=30,
        validators=[MinValueValidator(0), MaxValueValidator(59)],
    )
    notification_days_ahead = models.PositiveSmallIntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(14)],
    )
    notification_include_tasks = models.BooleanField(default=True)
    notification_include_planner = models.BooleanField(default=True)
    notification_include_subscriptions = models.BooleanField(default=True)
    notification_include_routines = models.BooleanField(default=True)

    latest_poll_at = models.DateTimeField(null=True, blank=True)
    latest_poll_status = models.CharField(max_length=32, blank=True)
    latest_poll_error = models.TextField(blank=True)
    last_notification_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner"],
                name="archibald_mail_config_owner_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "is_enabled"]),
            models.Index(fields=["owner", "notifications_enabled"]),
        ]

    def __str__(self):
        return f"ArchibaldMailboxConfig({self.owner_id})"

    def resolved_imap_host(self) -> str:
        return (self.imap_host or _env_first("ARCHIBALD_MAIL_IMAP_HOST", "IMAP_HOST")).strip()

    def resolved_imap_port(self) -> int:
        raw = _env_first("ARCHIBALD_MAIL_IMAP_PORT", "IMAP_PORT")
        if raw.isdigit() and (not self.imap_port or self.imap_port == 993):
            return int(raw)
        return self.imap_port or 993

    def resolved_imap_username(self) -> str:
        return (self.imap_username or _env_first("ARCHIBALD_MAIL_IMAP_USERNAME", "IMAP_USERNAME")).strip()

    def resolved_imap_password(self) -> str:
        return (self.imap_password or _env_first("ARCHIBALD_MAIL_IMAP_PASSWORD", "IMAP_PASSWORD")).strip()

    def resolved_smtp_host(self) -> str:
        return (self.smtp_host or _env_first("ARCHIBALD_MAIL_SMTP_HOST", "SMTP_HOST")).strip()

    def resolved_smtp_port(self) -> int:
        raw = _env_first("ARCHIBALD_MAIL_SMTP_PORT", "SMTP_PORT")
        if raw.isdigit() and (not self.smtp_port or self.smtp_port == 587):
            return int(raw)
        return self.smtp_port or 587

    def resolved_smtp_username(self) -> str:
        return (self.smtp_username or _env_first("ARCHIBALD_MAIL_SMTP_USERNAME", "SMTP_USERNAME")).strip()

    def resolved_smtp_password(self) -> str:
        return (self.smtp_password or _env_first("ARCHIBALD_MAIL_SMTP_PASSWORD", "SMTP_PASSWORD")).strip()

    def smtp_sender(self) -> str:
        sender = _env_first("ARCHIBALD_MAIL_SMTP_FROM", "SMTP_FROM")
        return (self.smtp_from_email or sender or self.inbox_address or self.resolved_smtp_username()).strip()

    def notification_target(self) -> str:
        return (self.notification_recipient or self.owner.email or self.inbox_address).strip()

    def is_imap_configured(self) -> bool:
        return bool(self.resolved_imap_host() and self.resolved_imap_username() and self.resolved_imap_password())

    def is_smtp_configured(self) -> bool:
        return bool(
            self.resolved_smtp_host()
            and self.resolved_smtp_username()
            and self.resolved_smtp_password()
            and self.smtp_sender()
        )


class ArchibaldEmailFlagRule(OwnedModel, TimeStampedModel):
    class ActionKey(models.TextChoices):
        MEMORY_STOCK_SAVE = "memory_stock.save", "Memory Stock"
        TODO_CAPTURE = "todo.capture", "Todo (fallback Memory Stock)"
        TRANSACTION_CAPTURE = "transaction.capture", "Transaction (fallback Memory Stock)"
        REMINDER_CAPTURE = "reminder.capture", "Reminder (fallback Memory Stock)"

    label = models.CharField(max_length=60)
    flag_token = models.CharField(max_length=32)
    action_key = models.CharField(max_length=64, choices=ActionKey.choices, default=ActionKey.MEMORY_STOCK_SAVE)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "flag_token"],
                name="archibald_mail_flag_owner_token_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "is_active", "flag_token"]),
            models.Index(fields=["owner", "action_key", "is_active"]),
        ]

    def save(self, *args, **kwargs):
        token = (self.flag_token or "").strip().upper()
        token = token.strip("[]# ")
        if token.startswith("ACTION:"):
            token = token.split(":", 1)[1].strip()
        token = token.replace(" ", "_")
        self.flag_token = token
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.flag_token} -> {self.action_key}"

    @staticmethod
    def is_valid_token(value: str) -> bool:
        return bool(FLAG_TOKEN_RE.fullmatch((value or "").strip().upper()))


class ArchibaldInboundCategory(OwnedModel, TimeStampedModel):
    label = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "label"],
                name="archibald_mail_inbound_category_owner_label_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "is_active", "label"]),
        ]

    def save(self, *args, **kwargs):
        self.label = (self.label or "").strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.label


class ArchibaldEmailMessage(OwnedModel, TimeStampedModel):
    class Direction(models.TextChoices):
        INBOUND = "INBOUND", "Inbound"
        OUTBOUND = "OUTBOUND", "Outbound"
        NOTIFICATION = "NOTIFICATION", "Notification"
        TEST = "TEST", "Test"

    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Received"
        REPLIED = "REPLIED", "Replied"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        SKIPPED = "SKIPPED", "Skipped"

    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPLIED = "APPLIED", "Applied"
        IGNORED = "IGNORED", "Ignored"

    config = models.ForeignKey(
        "archibald_mail.ArchibaldMailboxConfig",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    related_message = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="followups",
        null=True,
        blank=True,
    )
    direction = models.CharField(max_length=16, choices=Direction.choices)
    status = models.CharField(max_length=16, choices=Status.choices)

    message_id = models.CharField(max_length=255, blank=True)
    in_reply_to = models.CharField(max_length=255, blank=True)
    external_ref = models.CharField(max_length=120, blank=True)

    sender = models.EmailField(blank=True)
    recipient = models.EmailField(blank=True)
    subject = models.CharField(max_length=255, blank=True)
    body_text = models.TextField(blank=True)
    ai_response_text = models.TextField(blank=True)
    raw_headers = models.TextField(blank=True)
    error_text = models.TextField(blank=True)
    classification_category = models.ForeignKey(
        "archibald_mail.ArchibaldInboundCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages",
    )
    classification_label = models.CharField(max_length=80, blank=True)
    selected_action_key = models.CharField(max_length=64, blank=True)
    review_status = models.CharField(
        max_length=16,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )
    review_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    processed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "config", "direction", "created_at"]),
            models.Index(fields=["owner", "message_id"]),
            models.Index(fields=["owner", "status", "created_at"]),
            models.Index(fields=["owner", "direction", "review_status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.direction} {self.status} ({self.owner_id})"
