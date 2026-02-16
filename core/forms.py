from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from subscriptions.models import Account


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ("name", "kind", "currency", "opening_balance", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        currency = self.fields["currency"].queryset.filter(code="EUR").first()
        if currency:
            self.fields["currency"].queryset = self.fields["currency"].queryset.filter(code="EUR")
            self.fields["currency"].initial = currency
