from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory

from .models import Contact, ContactDeliveryAddress, ContactPriceList, ContactPriceListItem, ContactToolbox


class ContactForm(forms.ModelForm):
    _ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
    _MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024

    class Meta:
        model = Contact
        fields = (
            "display_name",
            "entity_type",
            "person_name",
            "business_name",
            "profile_image",
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
        widgets = {
            "profile_image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def clean_display_name(self):
        return (self.cleaned_data.get("display_name") or "").strip()

    def clean_profile_image(self):
        image = self.cleaned_data.get("profile_image")
        if not image:
            return image

        ext = f".{image.name.rsplit('.', 1)[-1].lower()}" if "." in image.name else ""
        if ext not in self._ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationError("Formato immagine non supportato.")

        content_type = (getattr(image, "content_type", "") or "").lower()
        if content_type and not content_type.startswith("image/"):
            raise ValidationError("Tipo file non valido. Carica un'immagine.")

        if image.size > self._MAX_IMAGE_SIZE_BYTES:
            raise ValidationError("Immagine troppo grande. Dimensione massima: 5 MB.")

        return image


class ContactToolboxForm(forms.ModelForm):
    class Meta:
        model = ContactToolbox
        fields = ("internal_notes",)
        widgets = {
            "internal_notes": forms.Textarea(attrs={"rows": 5}),
        }


class ContactDeliveryAddressForm(forms.ModelForm):
    class Meta:
        model = ContactDeliveryAddress
        fields = (
            "row_order",
            "label",
            "recipient_name",
            "line1",
            "line2",
            "postal_code",
            "city",
            "province",
            "country",
            "notes",
            "is_default",
            "is_active",
        )
        widgets = {
            "row_order": forms.HiddenInput(),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["row_order"].required = False

    def clean_label(self):
        return (self.cleaned_data.get("label") or "").strip()

    def clean_recipient_name(self):
        return (self.cleaned_data.get("recipient_name") or "").strip()

    def clean_line1(self):
        return (self.cleaned_data.get("line1") or "").strip()

    def clean_line2(self):
        return (self.cleaned_data.get("line2") or "").strip()

    def clean_postal_code(self):
        return (self.cleaned_data.get("postal_code") or "").strip()

    def clean_city(self):
        return (self.cleaned_data.get("city") or "").strip()

    def clean_province(self):
        return (self.cleaned_data.get("province") or "").strip()

    def clean_country(self):
        return (self.cleaned_data.get("country") or "").strip() or "Italia"

    def clean_notes(self):
        return (self.cleaned_data.get("notes") or "").strip()


class ContactPriceListForm(forms.ModelForm):
    class Meta:
        model = ContactPriceList
        fields = ("title", "currency_code", "pricing_notes", "is_active", "note")
        widgets = {
            "currency_code": forms.TextInput(attrs={"maxlength": "3"}),
            "pricing_notes": forms.Textarea(attrs={"rows": 4}),
            "note": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_title(self):
        return (self.cleaned_data.get("title") or "").strip()

    def clean_currency_code(self):
        value = (self.cleaned_data.get("currency_code") or "EUR").strip().upper()
        if len(value) != 3:
            raise forms.ValidationError("La valuta deve essere un codice di 3 lettere (es. EUR).")
        return value


class ContactPriceListItemForm(forms.ModelForm):
    class Meta:
        model = ContactPriceListItem
        fields = ("row_order", "code", "title", "description", "min_quantity", "max_quantity", "unit_price", "is_active")
        widgets = {
            "row_order": forms.HiddenInput(),
            "description": forms.TextInput(attrs={"placeholder": "Descrizione articolo"}),
            "min_quantity": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "max_quantity": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "unit_price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["row_order"].required = False

    def clean_title(self):
        return (self.cleaned_data.get("title") or "").strip()

    def clean(self):
        cleaned = super().clean()
        min_quantity = cleaned.get("min_quantity")
        max_quantity = cleaned.get("max_quantity")
        unit_price = cleaned.get("unit_price")
        if min_quantity is not None and min_quantity < 0:
            self.add_error("min_quantity", "La quantita minima non puo essere negativa.")
        if max_quantity is not None and max_quantity < 0:
            self.add_error("max_quantity", "La quantita massima non puo essere negativa.")
        if min_quantity is not None and max_quantity is not None and max_quantity < min_quantity:
            self.add_error("max_quantity", "La quantita massima deve essere maggiore o uguale alla minima.")
        if unit_price is not None and unit_price < 0:
            self.add_error("unit_price", "Il prezzo unitario non puo essere negativo.")
        return cleaned


ContactPriceListItemFormSet = inlineformset_factory(
    ContactPriceList,
    ContactPriceListItem,
    form=ContactPriceListItemForm,
    extra=1,
    can_delete=True,
)


ContactDeliveryAddressFormSet = inlineformset_factory(
    Contact,
    ContactDeliveryAddress,
    form=ContactDeliveryAddressForm,
    extra=1,
    can_delete=True,
)
