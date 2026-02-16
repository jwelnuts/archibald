from decimal import Decimal

from django.db import models

from common.models import OwnedModel, TimeStampedModel


class Currency(models.Model):
    """
    Se ti basta una sola valuta ora, puoi comunque tenerlo leggero.
    """
    code = models.CharField(max_length=3, unique=True)  # EUR, USD...
    name = models.CharField(max_length=64, blank=True)
    symbol = models.CharField(max_length=8, blank=True)

    class Meta:
        db_table = "common_currency"

    def __str__(self):
        return self.code


class Tag(OwnedModel, TimeStampedModel):
    name = models.CharField(max_length=50)

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [models.Index(fields=["owner", "name"])]

    def __str__(self):
        return self.name


class Account(OwnedModel, TimeStampedModel):
    class Kind(models.TextChoices):
        BANK = "BANK", "Bank"
        CARD = "CARD", "Card"
        CASH = "CASH", "Cash"
        INVEST = "INVEST", "Investment"
        OTHER = "OTHER", "Other"

    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.BANK)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
        ]
        db_table = "core_accounts"

    def __str__(self):
        return f"{self.name} ({self.currency.code})"


class Subscription(OwnedModel, TimeStampedModel):
    """
    Definizione dell'abbonamento (ricorrenza).
    Le scadenze vere stanno in SubscriptionOccurrence.
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PAUSED = "PAUSED", "Paused"
        CANCELED = "CANCELED", "Canceled"

    class IntervalUnit(models.TextChoices):
        DAY = "DAY", "Day"
        WEEK = "WEEK", "Week"
        MONTH = "MONTH", "Month"
        YEAR = "YEAR", "Year"

    name = models.CharField(max_length=160)
    payee = models.ForeignKey("core.Payee", null=True, blank=True, on_delete=models.SET_NULL, related_name="subscriptions")
    category = models.ForeignKey("projects.Category", null=True, blank=True, on_delete=models.SET_NULL, related_name="subscriptions")
    project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="subscriptions")

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="subscriptions")
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    start_date = models.DateField()
    next_due_date = models.DateField()  # utile per query rapide
    end_date = models.DateField(null=True, blank=True)

    interval = models.PositiveSmallIntegerField(default=1)  # es. 1 mese, 3 mesi, 12 mesi
    interval_unit = models.CharField(max_length=8, choices=IntervalUnit.choices, default=IntervalUnit.MONTH)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    autopay = models.BooleanField(default=False)
    note = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="subscriptions")

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [
            models.Index(fields=["owner", "status", "next_due_date"]),
            models.Index(fields=["owner", "project", "status"]),
        ]

    def __str__(self):
        return self.name


class SubscriptionOccurrence(OwnedModel, TimeStampedModel):
    """
    Una singola scadenza dello scadenziario.
    La puoi generare in batch (es. prossimi 12 mesi) oppure "on-demand".
    """

    class State(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        PAID = "PAID", "Paid"
        SKIPPED = "SKIPPED", "Skipped"
        FAILED = "FAILED", "Failed"

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="occurrences")
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)

    state = models.CharField(max_length=10, choices=State.choices, default=State.PLANNED)

    # quando la paghi, la colleghi alla transazione reale
    transaction = models.OneToOneField(
        "transactions.Transaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subscription_occurrence",
    )

    class Meta:
        unique_together = [("subscription", "due_date")]
        indexes = [
            models.Index(fields=["owner", "due_date", "state"]),
            models.Index(fields=["owner", "subscription", "due_date"]),
        ]

    def __str__(self):
        return f"{self.subscription.name} - {self.due_date}"
