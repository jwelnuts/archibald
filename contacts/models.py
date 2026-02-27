from decimal import Decimal, ROUND_HALF_UP

from django.db import models

from common.models import OwnedModel, TimeStampedModel


class Contact(OwnedModel, TimeStampedModel):
    class EntityType(models.TextChoices):
        PERSON = "PERSON", "Persona"
        HYBRID = "HYBRID", "Persona + Attivita"
        ENTITY = "ENTITY", "Ente"
        COMPANY = "COMPANY", "Azienda"

    display_name = models.CharField(max_length=160)
    entity_type = models.CharField(max_length=10, choices=EntityType.choices, default=EntityType.PERSON)
    person_name = models.CharField(max_length=160, blank=True)
    business_name = models.CharField(max_length=160, blank=True)

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    website = models.URLField(blank=True)
    city = models.CharField(max_length=120, blank=True)

    role_customer = models.BooleanField(default=False)
    role_supplier = models.BooleanField(default=False)
    role_payee = models.BooleanField(default=False)
    role_income_source = models.BooleanField(default=False)

    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("owner", "display_name")]
        indexes = [
            models.Index(fields=["owner", "display_name"]),
            models.Index(fields=["owner", "is_active"]),
            models.Index(fields=["owner", "role_customer"]),
            models.Index(fields=["owner", "role_supplier"]),
            models.Index(fields=["owner", "role_payee"]),
            models.Index(fields=["owner", "role_income_source"]),
        ]

    def __str__(self):
        return self.display_name


def _to_decimal(value, default="0.00"):
    raw = value if value is not None else default
    return Decimal(str(raw))


class ContactToolbox(OwnedModel, TimeStampedModel):
    contact = models.OneToOneField("contacts.Contact", on_delete=models.CASCADE, related_name="toolbox")
    internal_notes = models.TextField(blank=True)
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "contact"]),
        ]

    def save(self, *args, **kwargs):
        if self.contact_id and self.owner_id != self.contact.owner_id:
            self.owner = self.contact.owner
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Toolbox - {self.contact.display_name}"


class ContactPriceList(OwnedModel, TimeStampedModel):
    toolbox = models.ForeignKey("contacts.ContactToolbox", on_delete=models.CASCADE, related_name="price_lists")
    title = models.CharField(max_length=180)
    currency_code = models.CharField(max_length=3, default="EUR")
    pricing_notes = models.TextField(blank=True)
    note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "toolbox", "is_active"]),
            models.Index(fields=["owner", "toolbox", "updated_at"]),
        ]

    @property
    def contact(self):
        return self.toolbox.contact

    def save(self, *args, **kwargs):
        if self.toolbox_id and self.owner_id != self.toolbox.owner_id:
            self.owner = self.toolbox.owner
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ContactPriceListItem(OwnedModel, TimeStampedModel):
    price_list = models.ForeignKey("contacts.ContactPriceList", on_delete=models.CASCADE, related_name="items")
    row_order = models.PositiveSmallIntegerField(default=0)
    code = models.CharField(max_length=60, blank=True)
    title = models.CharField(max_length=180)
    description = models.CharField(max_length=255, blank=True)
    min_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    max_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "price_list", "row_order"]),
            models.Index(fields=["owner", "price_list", "is_active"]),
        ]
        ordering = ["row_order", "id"]

    def save(self, *args, **kwargs):
        if self.price_list_id and self.owner_id != self.price_list.owner_id:
            self.owner = self.price_list.owner

        min_quantity = _to_decimal(self.min_quantity, default="1.00")
        if min_quantity < 0:
            min_quantity = Decimal("0.00")
        unit_price = _to_decimal(self.unit_price)
        if unit_price < 0:
            unit_price = Decimal("0.00")
        max_quantity = _to_decimal(self.max_quantity) if self.max_quantity is not None else None
        if max_quantity is not None and max_quantity < 0:
            max_quantity = Decimal("0.00")
        if max_quantity is not None and max_quantity < min_quantity:
            max_quantity = min_quantity

        self.min_quantity = min_quantity.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.max_quantity = (
            max_quantity.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if max_quantity is not None else None
        )
        self.unit_price = unit_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        super().save(*args, **kwargs)

    def matches_quantity(self, quantity):
        qty = _to_decimal(quantity)
        if qty < self.min_quantity:
            return False
        if self.max_quantity is not None and qty > self.max_quantity:
            return False
        return True

    @property
    def range_label(self):
        if self.max_quantity is None:
            return f"{self.min_quantity}+"
        return f"{self.min_quantity} - {self.max_quantity}"

    def __str__(self):
        return f"{self.title} [{self.range_label}]"
