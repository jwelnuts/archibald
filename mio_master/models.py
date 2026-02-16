class Currency(models.Model):
    """
    Se ti basta una sola valuta ora, puoi comunque tenerlo leggero.
    """
    code = models.CharField(max_length=3, unique=True)  # EUR, USD...
    name = models.CharField(max_length=64, blank=True)
    symbol = models.CharField(max_length=8, blank=True)

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

    def __str__(self):
        return f"{self.name} ({self.currency.code})"


class Payee(OwnedModel, TimeStampedModel):
    """
    Beneficiario/Controparte: Netflix, Enel, AWS, Cliente X.
    """
    name = models.CharField(max_length=160)
    website = models.URLField(blank=True)

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [models.Index(fields=["owner", "name"])]

    def __str__(self):
        return self.name


class Transaction(OwnedModel, TimeStampedModel):
    class Type(models.TextChoices):
        INCOME = "IN", "Income"
        EXPENSE = "OUT", "Expense"
        TRANSFER = "XFER", "Transfer"  # opzionale, se vuoi gestire giroconti

    tx_type = models.CharField(max_length=4, choices=Type.choices)
    date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # sempre positivo; segno dato da tx_type
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="transactions")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    payee = models.ForeignKey(Payee, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")

    note = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="transactions")

    # per collegare origine: abbonamento, import, ecc.
    source_subscription = models.ForeignKey(
        "Subscription", null=True, blank=True, on_delete=models.SET_NULL, related_name="generated_transactions"
    )

    class Meta:
        indexes = [
            models.Index(fields=["owner", "date"]),
            models.Index(fields=["owner", "tx_type", "date"]),
            models.Index(fields=["owner", "project", "date"]),
        ]

    def __str__(self):
        return f"{self.get_tx_type_display()} {self.amount} {self.currency.code} ({self.date})"