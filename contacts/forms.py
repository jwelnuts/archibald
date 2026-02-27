from django import forms

from .models import Contact, ContactPriceItem, ContactPriceTier, ContactWorkspace


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


class ContactWorkspaceForm(forms.ModelForm):
    class Meta:
        model = ContactWorkspace
        fields = ("internal_notes",)
        widgets = {
            "internal_notes": forms.Textarea(attrs={"rows": 4}),
        }


class ContactPriceItemForm(forms.ModelForm):
    class Meta:
        model = ContactPriceItem
        fields = ("title", "code", "description", "vat_rate", "is_active", "sort_order")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_title(self):
        return (self.cleaned_data.get("title") or "").strip()


class ContactPriceTierForm(forms.ModelForm):
    item = forms.ModelChoiceField(queryset=ContactPriceItem.objects.none(), label="Articolo")

    class Meta:
        model = ContactPriceTier
        fields = ("item", "min_qty", "max_qty", "unit_price_net")

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        contact = kwargs.pop("contact", None)
        super().__init__(*args, **kwargs)
        qs = ContactPriceItem.objects.none()
        if owner is not None and contact is not None:
            qs = ContactPriceItem.objects.filter(owner=owner, contact=contact).order_by("sort_order", "title")
        self.fields["item"].queryset = qs

    def clean(self):
        cleaned = super().clean()
        min_qty = cleaned.get("min_qty")
        max_qty = cleaned.get("max_qty")
        if min_qty is not None and min_qty <= 0:
            self.add_error("min_qty", "La quantita minima deve essere maggiore di zero.")
        if max_qty is not None and min_qty is not None and max_qty < min_qty:
            self.add_error("max_qty", "La quantita massima deve essere >= quantita minima.")
        return cleaned


class ContactPriceCalculatorForm(forms.Form):
    item = forms.ModelChoiceField(queryset=ContactPriceItem.objects.none(), label="Articolo")
    quantity = forms.DecimalField(label="Quantita", max_digits=10, decimal_places=2, min_value=0.01)

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        contact = kwargs.pop("contact", None)
        super().__init__(*args, **kwargs)
        qs = ContactPriceItem.objects.none()
        if owner is not None and contact is not None:
            qs = ContactPriceItem.objects.filter(owner=owner, contact=contact, is_active=True).order_by("sort_order", "title")
        self.fields["item"].queryset = qs
