from django.contrib import admin

from .models import Link


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ("url", "category", "importance", "note", "owner", "created_at")
    search_fields = ("owner__username",)
