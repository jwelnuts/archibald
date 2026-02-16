from django import forms

from .models import Account, Currency


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ("name", "kind", "currency", "opening_balance", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
        self.fields["currency"].queryset = Currency.objects.filter(code="EUR")
        self.fields["currency"].initial = currency
