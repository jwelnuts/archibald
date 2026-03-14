from django.contrib import admin

from .models import ArchibaldEmailMessage, ArchibaldMailboxConfig


@admin.register(ArchibaldMailboxConfig)
class ArchibaldMailboxConfigAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "inbox_address",
        "is_enabled",
        "auto_reply_enabled",
        "notifications_enabled",
        "latest_poll_status",
        "latest_poll_at",
        "last_notification_sent_at",
    )
    search_fields = ("owner__username", "inbox_address", "smtp_username", "imap_username")
    list_filter = ("is_enabled", "auto_reply_enabled", "notifications_enabled", "latest_poll_status")


@admin.register(ArchibaldEmailMessage)
class ArchibaldEmailMessageAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "owner",
        "direction",
        "status",
        "sender",
        "recipient",
        "subject",
    )
    search_fields = ("owner__username", "sender", "recipient", "subject", "message_id")
    list_filter = ("direction", "status")
    readonly_fields = ("created_at", "updated_at")
