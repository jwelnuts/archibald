from django.contrib import admin

from .models import VaultItem, VaultProfile


@admin.register(VaultProfile)
class VaultProfileAdmin(admin.ModelAdmin):
    list_display = ("owner", "totp_enabled_at", "failed_attempts", "locked_until")
    search_fields = ("owner__username",)


@admin.register(VaultItem)
class VaultItemAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "title", "kind", "updated_at")
    list_filter = ("kind",)
    search_fields = ("title", "login")
