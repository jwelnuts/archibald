from django import forms

from core.models import Payee
from subscriptions.models import Currency
from transactions.models import Transaction


class OutcomeForm(forms.ModelForm):
    payee_name = forms.CharField(label="Beneficiario", max_length=160, required=False)

    class Meta:
        model = Transaction
        fields = ("date", "amount", "currency", "account", "project", "category", "note", "tags")
        widgets = {
            "date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        self._owner = owner
        if owner is not None:
            self.fields["account"].queryset = self.fields["account"].queryset.filter(owner=owner)
            self.fields["project"].queryset = self.fields["project"].queryset.filter(owner=owner)
            self.fields["category"].queryset = self.fields["category"].queryset.filter(owner=owner)
            self.fields["tags"].queryset = self.fields["tags"].queryset.filter(owner=owner)
        currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
        self.fields["currency"].queryset = Currency.objects.filter(code="EUR")
        self.fields["currency"].initial = currency
        if self.instance and self.instance.pk and self.instance.payee:
            self.fields["payee_name"].initial = self.instance.payee.name

    def save(self, commit=True):
        instance = super().save(commit=False)
        payee_name = (self.cleaned_data.get("payee_name") or "").strip()
        if payee_name and self._owner is not None:
            payee, _ = Payee.objects.get_or_create(owner=self._owner, name=payee_name)
            instance.payee = payee
        elif not payee_name:
            instance.payee = None
        if commit:
            instance.save()
            self.save_m2m()
        return instance
