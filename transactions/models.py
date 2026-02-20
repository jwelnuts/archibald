from django.db import models
from django.utils import timezone

from common.models import OwnedModel, TimeStampedModel


class Transaction(OwnedModel, TimeStampedModel):
    class Type(models.TextChoices):
        INCOME = "IN", "Income"
        EXPENSE = "OUT", "Expense"
        TRANSFER = "XFER", "Transfer"

    tx_type = models.CharField(max_length=4, choices=Type.choices)
    date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.ForeignKey("subscriptions.Currency", on_delete=models.PROTECT)

    account = models.ForeignKey("subscriptions.Account", on_delete=models.PROTECT, related_name="transactions")
    project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    category = models.ForeignKey("projects.Category", null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    payee = models.ForeignKey("core.Payee", null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    income_source = models.ForeignKey(
        "income.IncomeSource",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions",
    )

    note = models.TextField(blank=True)
    attachment = models.FileField(upload_to="transactions/attachments/%Y/%m/", blank=True, null=True)
    tags = models.ManyToManyField("subscriptions.Tag", blank=True, related_name="transactions")

    source_subscription = models.ForeignKey(
        "subscriptions.Subscription",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_transactions",
    )

    class Meta:
        indexes = [
            models.Index(fields=["owner", "date"]),
            models.Index(fields=["owner", "tx_type", "date"]),
            models.Index(fields=["owner", "project", "date"]),
        ]

    def __str__(self):
        return f"{self.get_tx_type_display()} {self.amount} {self.currency.code} ({self.date})"
