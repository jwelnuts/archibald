from django.contrib import admin

from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "display_name",
        "entity_type",
        "role_customer",
        "role_supplier",
        "role_payee",
        "role_income_source",
        "is_active",
    )
    list_filter = ("entity_type", "is_active", "role_customer", "role_supplier", "role_payee", "role_income_source")
    search_fields = ("display_name", "person_name", "business_name", "email", "phone")
