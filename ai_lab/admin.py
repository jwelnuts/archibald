from django.contrib import admin

from .models import LabEntry


@admin.register(LabEntry)
class LabEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "title", "area", "status", "updated_at")
    list_filter = ("area", "status")
    search_fields = ("title", "prompt", "notes", "result")
