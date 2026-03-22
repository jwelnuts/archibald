from django.contrib import admin

from .models import Contact, ContactDeliveryAddress, ContactPriceList, ContactPriceListItem, ContactToolbox


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


@admin.register(ContactToolbox)
class ContactToolboxAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "contact", "updated_at")
    search_fields = ("contact__display_name",)


class ContactPriceListItemInline(admin.TabularInline):
    model = ContactPriceListItem
    extra = 0


@admin.register(ContactPriceList)
class ContactPriceListAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "title", "toolbox", "currency_code", "is_active")
    list_filter = ("is_active", "currency_code")
    search_fields = ("title", "toolbox__contact__display_name")
    inlines = [ContactPriceListItemInline]


@admin.register(ContactDeliveryAddress)
class ContactDeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "contact", "label", "city", "is_default", "is_active")
    list_filter = ("is_default", "is_active", "country")
    search_fields = ("contact__display_name", "label", "recipient_name", "line1", "city", "postal_code")
