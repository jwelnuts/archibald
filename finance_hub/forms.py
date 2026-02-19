from django import forms
from django.forms import inlineformset_factory

from subscriptions.models import Currency

from .models import Invoice, Quote, QuoteLine, WorkOrder


class _OwnedFinanceFormMixin:
    def _init_common(self, owner):
        self._owner = owner
        if owner is not None:
            if "customer" in self.fields:
                self.fields["customer"].queryset = self.fields["customer"].queryset.filter(owner=owner).order_by("name")
            if "project" in self.fields:
                self.fields["project"].queryset = self.fields["project"].queryset.filter(owner=owner).order_by("name")
            if "account" in self.fields:
                self.fields["account"].queryset = self.fields["account"].queryset.filter(owner=owner).order_by("name")
            if "quote" in self.fields:
                self.fields["quote"].queryset = self.fields["quote"].queryset.filter(owner=owner).order_by("-issue_date", "-id")

        currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
        self.fields["currency"].queryset = Currency.objects.filter(code="EUR")
        self.fields["currency"].initial = currency


class QuoteForm(_OwnedFinanceFormMixin, forms.ModelForm):
    class Meta:
        model = Quote
        fields = (
            "code",
            "title",
            "customer",
            "project",
            "issue_date",
            "valid_until",
            "currency",
            "amount_net",
            "tax_amount",
            "status",
            "note",
        )
        widgets = {
            "issue_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "valid_until": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        self._init_common(owner)


class InvoiceForm(_OwnedFinanceFormMixin, forms.ModelForm):
    class Meta:
        model = Invoice
        fields = (
            "code",
            "title",
            "quote",
            "customer",
            "project",
            "account",
            "issue_date",
            "due_date",
            "paid_date",
            "currency",
            "amount_net",
            "tax_amount",
            "status",
            "note",
        )
        widgets = {
            "issue_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "due_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "paid_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        self._init_common(owner)


class WorkOrderForm(_OwnedFinanceFormMixin, forms.ModelForm):
    class Meta:
        model = WorkOrder
        fields = (
            "code",
            "title",
            "customer",
            "project",
            "account",
            "start_date",
            "end_date",
            "currency",
            "estimated_amount",
            "final_amount",
            "is_billable",
            "status",
            "note",
        )
        widgets = {
            "start_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "end_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        self._init_common(owner)


class QuoteLineForm(forms.ModelForm):
    class Meta:
        model = QuoteLine
        fields = (
            "row_order",
            "code",
            "description",
            "net_amount",
            "gross_amount",
            "quantity",
            "discount",
            "vat_code",
        )
        widgets = {
            "row_order": forms.HiddenInput(),
            "description": forms.TextInput(attrs={"placeholder": "Descrizione articolo"}),
            "discount": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}),
            "quantity": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "net_amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "gross_amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["row_order"].required = False


QuoteLineFormSet = inlineformset_factory(
    Quote,
    QuoteLine,
    form=QuoteLineForm,
    extra=1,
    can_delete=True,
)
