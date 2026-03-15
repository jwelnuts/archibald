from django.contrib import admin

from .models import (
    ArchibaldEmailFlagRule,
    ArchibaldEmailMessage,
    ArchibaldInboundCategory,
    ArchibaldMailboxConfig,
)


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
        "review_status",
        "classification_category",
        "selected_action_key",
        "sender",
        "recipient",
        "subject",
    )
    search_fields = (
        "owner__username",
        "sender",
        "recipient",
        "subject",
        "message_id",
        "classification_category__label",
        "classification_label",
        "selected_action_key",
    )
    list_filter = ("direction", "status", "review_status")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ArchibaldEmailFlagRule)
class ArchibaldEmailFlagRuleAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "flag_token",
        "label",
        "action_key",
        "is_active",
        "updated_at",
    )
    list_filter = ("action_key", "is_active")
    search_fields = ("owner__username", "flag_token", "label", "action_key")


@admin.register(ArchibaldInboundCategory)
class ArchibaldInboundCategoryAdmin(admin.ModelAdmin):
    list_display = ("owner", "label", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("owner__username", "label")
