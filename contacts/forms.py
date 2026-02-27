from django import forms
from django.forms import inlineformset_factory

from .models import Contact, ContactPriceList, ContactPriceListItem, ContactToolbox


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = (
            "display_name",
            "entity_type",
            "person_name",
            "business_name",
            "email",
            "phone",
            "website",
            "city",
            "role_customer",
            "role_supplier",
            "role_payee",
            "role_income_source",
            "notes",
            "is_active",
        )

    def clean_display_name(self):
        return (self.cleaned_data.get("display_name") or "").strip()


class ContactToolboxForm(forms.ModelForm):
    class Meta:
        model = ContactToolbox
        fields = ("internal_notes",)
        widgets = {
            "internal_notes": forms.Textarea(attrs={"rows": 5}),
        }


class ContactPriceListForm(forms.ModelForm):
    class Meta:
        model = ContactPriceList
        fields = ("title", "currency_code", "vat_rate", "is_active", "note")
        widgets = {
            "vat_rate": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "currency_code": forms.TextInput(attrs={"maxlength": "3"}),
            "note": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_title(self):
        return (self.cleaned_data.get("title") or "").strip()

    def clean_currency_code(self):
        value = (self.cleaned_data.get("currency_code") or "EUR").strip().upper()
        if len(value) != 3:
            raise forms.ValidationError("La valuta deve essere un codice di 3 lettere (es. EUR).")
        return value

    def clean_vat_rate(self):
        vat = self.cleaned_data.get("vat_rate")
        if vat is None:
            return vat
        if vat < 0:
            raise forms.ValidationError("L'aliquota IVA non puo essere negativa.")
        return vat


class ContactPriceListItemForm(forms.ModelForm):
    class Meta:
        model = ContactPriceListItem
        fields = ("row_order", "code", "title", "description", "quantity", "unit_price_net", "discount")
        widgets = {
            "row_order": forms.HiddenInput(),
            "description": forms.TextInput(attrs={"placeholder": "Descrizione articolo"}),
            "quantity": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "unit_price_net": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "discount": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["row_order"].required = False

    def clean_title(self):
        return (self.cleaned_data.get("title") or "").strip()

    def clean(self):
        cleaned = super().clean()
        quantity = cleaned.get("quantity")
        unit_price = cleaned.get("unit_price_net")
        discount = cleaned.get("discount")
        if quantity is not None and quantity < 0:
            self.add_error("quantity", "La quantita non puo essere negativa.")
        if unit_price is not None and unit_price < 0:
            self.add_error("unit_price_net", "Il prezzo unitario non puo essere negativo.")
        if discount is not None and (discount < 0 or discount > 100):
            self.add_error("discount", "Lo sconto deve essere tra 0 e 100.")
        return cleaned


ContactPriceListItemFormSet = inlineformset_factory(
    ContactPriceList,
    ContactPriceListItem,
    form=ContactPriceListItemForm,
    extra=1,
    can_delete=True,
)
