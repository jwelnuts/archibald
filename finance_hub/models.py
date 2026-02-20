from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.utils import timezone

from common.models import OwnedModel, TimeStampedModel


class VatCode(OwnedModel, TimeStampedModel):
    code = models.CharField(max_length=20)
    description = models.CharField(max_length=120, blank=True)
    rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("22.00"))
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("owner", "code")]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
            models.Index(fields=["owner", "rate"]),
        ]
        ordering = ["rate", "code"]

    def __str__(self):
        if self.description:
            return f"{self.code} - {self.description} ({self.rate}%)"
        return f"{self.code} ({self.rate}%)"


class Quote(OwnedModel, TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Bozza"
        SENT = "SENT", "Inviato"
        APPROVED = "APPROVED", "Approvato"
        REJECTED = "REJECTED", "Rifiutato"
        EXPIRED = "EXPIRED", "Scaduto"

    code = models.CharField(max_length=40, blank=True)
    title = models.CharField(max_length=180)
    customer = models.ForeignKey(
        "projects.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="finance_quotes",
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="finance_quotes",
    )
    issue_date = models.DateField(default=timezone.now)
    valid_until = models.DateField(null=True, blank=True)
    currency = models.ForeignKey("subscriptions.Currency", on_delete=models.PROTECT)
    vat_code = models.ForeignKey(
        "finance_hub.VatCode",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quotes",
    )
    amount_net = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "code"],
                condition=~Q(code=""),
                name="finance_quote_owner_code_unique_non_empty",
            )
        ]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["owner", "valid_until"]),
        ]

    def save(self, *args, **kwargs):
        net_amount = self.amount_net or Decimal("0.00")
        vat_rate = self.vat_code.rate if self.vat_code_id else Decimal("0.00")
        self.tax_amount = (net_amount * vat_rate / Decimal("100.00")).quantize(Decimal("0.01"))
        self.total_amount = (net_amount + self.tax_amount).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

    def refresh_totals_from_lines(self, *, save=True):
        lines = self.lines.all()
        if not lines.exists():
            return

        total_net = Decimal("0.00")
        for line in lines:
            total_net += line.net_total

        self.amount_net = total_net
        if save:
            self.save(update_fields=["amount_net", "tax_amount", "total_amount", "updated_at"])

    def __str__(self):
        return self.code or self.title


class Invoice(OwnedModel, TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Bozza"
        ISSUED = "ISSUED", "Emessa"
        PAID = "PAID", "Pagata"
        OVERDUE = "OVERDUE", "Scaduta"
        CANCELED = "CANCELED", "Annullata"

    code = models.CharField(max_length=40, blank=True)
    title = models.CharField(max_length=180)
    quote = models.ForeignKey(
        "finance_hub.Quote",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoices",
    )
    customer = models.ForeignKey(
        "projects.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="finance_invoices",
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="finance_invoices",
    )
    account = models.ForeignKey(
        "subscriptions.Account",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="finance_invoices",
    )
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)
    currency = models.ForeignKey("subscriptions.Currency", on_delete=models.PROTECT)
    amount_net = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "code"],
                condition=~Q(code=""),
                name="finance_invoice_owner_code_unique_non_empty",
            )
        ]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["owner", "due_date"]),
        ]

    def save(self, *args, **kwargs):
        self.total_amount = (self.amount_net or Decimal("0.00")) + (self.tax_amount or Decimal("0.00"))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code or self.title


class QuoteLine(OwnedModel, TimeStampedModel):
    quote = models.ForeignKey(
        "finance_hub.Quote",
        on_delete=models.CASCADE,
        related_name="lines",
    )
    row_order = models.PositiveSmallIntegerField(default=0)
    code = models.CharField(max_length=60)
    description = models.CharField(max_length=255)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    vat_code = models.CharField(max_length=20)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "quote", "row_order"]),
        ]
        ordering = ["row_order", "id"]

    @property
    def discount_factor(self):
        pct = self.discount or Decimal("0.00")
        factor = Decimal("1.00") - (pct / Decimal("100.00"))
        if factor < 0:
            return Decimal("0.00")
        return factor

    @property
    def net_total(self):
        return (self.net_amount or Decimal("0.00")) * (self.quantity or Decimal("0.00")) * self.discount_factor

    @property
    def gross_total(self):
        return (self.gross_amount or Decimal("0.00")) * (self.quantity or Decimal("0.00")) * self.discount_factor

    def __str__(self):
        return f"{self.code} · {self.description}"


class WorkOrder(OwnedModel, TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Aperto"
        IN_PROGRESS = "IN_PROGRESS", "In corso"
        WAITING = "WAITING", "In attesa"
        DONE = "DONE", "Completato"
        CANCELED = "CANCELED", "Annullato"

    code = models.CharField(max_length=40, blank=True)
    title = models.CharField(max_length=180)
    customer = models.ForeignKey(
        "projects.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="finance_work_orders",
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="finance_work_orders",
    )
    account = models.ForeignKey(
        "subscriptions.Account",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="finance_work_orders",
    )
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    currency = models.ForeignKey("subscriptions.Currency", on_delete=models.PROTECT)
    estimated_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_billable = models.BooleanField(default=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "code"],
                condition=~Q(code=""),
                name="finance_work_order_owner_code_unique_non_empty",
            )
        ]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["owner", "start_date"]),
        ]

    def __str__(self):
        return self.code or self.title
