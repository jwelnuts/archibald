from django.contrib import admin

from .models import MemoryStockItem


@admin.register(MemoryStockItem)
class MemoryStockItemAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "owner",
        "title",
        "source_url",
        "source_action",
        "is_archived",
    )
    list_filter = ("is_archived", "source_action")
    search_fields = ("owner__username", "title", "source_url", "source_sender", "source_subject")
