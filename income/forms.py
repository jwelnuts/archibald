from django import forms

from subscriptions.models import Currency
from transactions.models import Transaction
from .models import IncomeSource


class IncomeForm(forms.ModelForm):
    source_choice = forms.ChoiceField(label="Fonte del denaro", required=False)
    source_name = forms.CharField(label="Fonte del denaro", max_length=160, required=False)

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
        choices = [("", "Seleziona..."), ("__new__", "Nuova fonte...")]
        if owner is not None:
            sources = IncomeSource.objects.filter(owner=owner).order_by("name")
            choices += [(str(source.id), source.name) for source in sources]
        self.fields["source_choice"].choices = choices
        if self.instance and self.instance.pk and self.instance.income_source:
            self.fields["source_choice"].initial = str(self.instance.income_source.id)

    def save(self, commit=True):
        instance = super().save(commit=False)
        source_choice = (self.cleaned_data.get("source_choice") or "").strip()
        source_name = (self.cleaned_data.get("source_name") or "").strip()
        if source_choice and source_choice not in {"__new__"}:
            try:
                instance.income_source = IncomeSource.objects.get(id=source_choice, owner=self._owner)
            except IncomeSource.DoesNotExist:
                instance.income_source = None
        elif source_name and self._owner is not None:
            source_obj, _ = IncomeSource.objects.get_or_create(owner=self._owner, name=source_name)
            instance.income_source = source_obj
        elif not source_choice:
            instance.income_source = None
        if commit:
            instance.save()
            self.save_m2m()
        return instance
