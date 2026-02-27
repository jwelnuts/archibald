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


class ContactWorkspace(OwnedModel, TimeStampedModel):
    contact = models.OneToOneField("contacts.Contact", on_delete=models.CASCADE, related_name="workspace")
    internal_notes = models.TextField(blank=True)
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "contact"]),
        ]

    def __str__(self):
        return f"Workspace({self.contact.display_name})"


class ContactPriceItem(OwnedModel, TimeStampedModel):
    contact = models.ForeignKey("contacts.Contact", on_delete=models.CASCADE, related_name="price_items")
    title = models.CharField(max_length=160)
    code = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("22.00"))
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "contact", "is_active"]),
            models.Index(fields=["owner", "contact", "sort_order"]),
        ]
        unique_together = [("owner", "contact", "title")]

    def tier_for_quantity(self, quantity: Decimal):
        qty = Decimal(str(quantity or 0))
        for tier in self.tiers.all().order_by("-min_qty"):
            if tier.matches_quantity(qty):
                return tier
        return None

    def calculate_totals(self, quantity: Decimal):
        qty = Decimal(str(quantity or 0))
        tier = self.tier_for_quantity(qty)
        unit_net = tier.unit_price_net if tier else Decimal("0.00")
        total_net = (qty * unit_net).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        vat_multiplier = Decimal("1.00") + (self.vat_rate / Decimal("100.00"))
        total_gross = (total_net * vat_multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {
            "item": self,
            "tier": tier,
            "quantity": qty.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "unit_net": unit_net.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "total_net": total_net,
            "vat_rate": self.vat_rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "total_gross": total_gross,
        }

    def __str__(self):
        return self.title


class ContactPriceTier(OwnedModel, TimeStampedModel):
    item = models.ForeignKey("contacts.ContactPriceItem", on_delete=models.CASCADE, related_name="tiers")
    min_qty = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    max_qty = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit_price_net = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "item", "min_qty"]),
        ]
        ordering = ["min_qty"]

    def matches_quantity(self, quantity: Decimal) -> bool:
        qty = Decimal(str(quantity or 0))
        if qty < self.min_qty:
            return False
        if self.max_qty is not None and qty > self.max_qty:
            return False
        return True

    def range_label(self):
        if self.max_qty is None:
            return f"{self.min_qty}+"
        return f"{self.min_qty}-{self.max_qty}"

    def __str__(self):
        return f"{self.item.title} [{self.range_label()}]"
