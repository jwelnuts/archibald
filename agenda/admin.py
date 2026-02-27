from django.contrib import admin

from .models import AgendaItem, WorkLog


@admin.register(AgendaItem)
class AgendaItemAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "item_type", "due_date", "due_time", "status")
    list_filter = ("item_type", "status", "due_date")
    search_fields = ("title", "note")


@admin.register(WorkLog)
class WorkLogAdmin(admin.ModelAdmin):
    list_display = ("owner", "work_date", "time_start", "time_end", "hours")
    list_filter = ("work_date",)
    search_fields = ("note",)
