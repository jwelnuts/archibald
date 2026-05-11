from django.contrib import admin

from .models import SocialChannel, SocialPost


@admin.register(SocialChannel)
class SocialChannelAdmin(admin.ModelAdmin):
    list_display = ["name", "platform", "project", "handle", "is_active", "owner"]
    list_filter = ["platform", "is_active", "project"]
    search_fields = ["name", "handle", "notes"]


@admin.register(SocialPost)
class SocialPostAdmin(admin.ModelAdmin):
    list_display = ["channel", "status", "scheduled_at", "published_at", "project", "owner"]
    list_filter = ["status", "channel__platform", "project"]
    search_fields = ["content", "notes"]
