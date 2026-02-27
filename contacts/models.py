from decimal import Decimal, ROUND_HALF_UP

from django.db import models

from common.models import OwnedModel, TimeStampedModel


class Contact(OwnedModel, TimeStampedModel):
    class EntityType(models.TextChoices):
        PERSON = "PERSON", "Persona"
        COMPANY = "COMPANY", "Azienda"
        HYBRID = "HYBRID", "Persona + Attivita"

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
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("22.00"))
    subtotal_net = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
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

        net = _to_decimal(self.subtotal_net)
        vat = _to_decimal(self.vat_rate)
        self.subtotal_net = net.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.tax_amount = (net * vat / Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.total_amount = (self.subtotal_net + self.tax_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)

    def refresh_totals_from_items(self, *, save=True):
        total_net = Decimal("0.00")
        for row in self.items.all():
            total_net += row.line_total_net or Decimal("0.00")
        self.subtotal_net = total_net.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if save:
            self.save(update_fields=["subtotal_net", "tax_amount", "total_amount", "updated_at"])
        return self.subtotal_net

    def __str__(self):
        return self.title


class ContactPriceListItem(OwnedModel, TimeStampedModel):
    price_list = models.ForeignKey("contacts.ContactPriceList", on_delete=models.CASCADE, related_name="items")
    row_order = models.PositiveSmallIntegerField(default=0)
    code = models.CharField(max_length=60, blank=True)
    title = models.CharField(max_length=180)
    description = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit_price_net = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    line_total_net = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        indexes = [
            models.Index(fields=["owner", "price_list", "row_order"]),
        ]
        ordering = ["row_order", "id"]

    @property
    def discount_factor(self):
        pct = _to_decimal(self.discount)
        factor = Decimal("1.00") - (pct / Decimal("100.00"))
        if factor < 0:
            return Decimal("0.00")
        return factor

    def save(self, *args, **kwargs):
        refresh_price_list = kwargs.pop("refresh_price_list", True)
        if self.price_list_id and self.owner_id != self.price_list.owner_id:
            self.owner = self.price_list.owner

        quantity = _to_decimal(self.quantity, default="1.00")
        if quantity < 0:
            quantity = Decimal("0.00")
        unit_price = _to_decimal(self.unit_price_net)
        if unit_price < 0:
            unit_price = Decimal("0.00")
        discount = _to_decimal(self.discount)
        if discount < 0:
            discount = Decimal("0.00")
        if discount > 100:
            discount = Decimal("100.00")

        self.quantity = quantity.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.unit_price_net = unit_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.discount = discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.line_total_net = (
            self.quantity * self.unit_price_net * (Decimal("1.00") - (self.discount / Decimal("100.00")))
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        super().save(*args, **kwargs)
        if refresh_price_list and self.price_list_id:
            self.price_list.refresh_totals_from_items(save=True)

    def delete(self, *args, **kwargs):
        refresh_price_list = kwargs.pop("refresh_price_list", True)
        price_list = self.price_list if self.price_list_id else None
        super().delete(*args, **kwargs)
        if refresh_price_list and price_list is not None:
            price_list.refresh_totals_from_items(save=True)

    def __str__(self):
        return f"{self.title} ({self.quantity} x {self.unit_price_net})"
