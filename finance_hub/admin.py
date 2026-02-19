from django.contrib import admin

from .models import Invoice, Quote, QuoteLine, WorkOrder


class QuoteLineInline(admin.TabularInline):
    model = QuoteLine
    extra = 0
    fields = ("row_order", "code", "description", "net_amount", "gross_amount", "quantity", "discount", "vat_code")
    ordering = ("row_order", "id")


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "code", "title", "status", "valid_until", "total_amount")
    list_filter = ("status",)
    search_fields = ("code", "title", "customer__name", "project__name")
    inlines = [QuoteLineInline]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "code", "title", "status", "due_date", "total_amount")
    list_filter = ("status",)
    search_fields = ("code", "title", "customer__name", "project__name")


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "code", "title", "status", "start_date", "final_amount")
    list_filter = ("status", "is_billable")
    search_fields = ("code", "title", "customer__name", "project__name")
