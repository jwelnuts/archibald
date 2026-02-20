from django import forms
from django.core.exceptions import ValidationError

from contacts.models import Contact
from contacts.services import ensure_legacy_records_for_contact, upsert_contact
from core.models import Payee
from subscriptions.models import Currency
from transactions.models import Transaction


class OutcomeForm(forms.ModelForm):
    payee_name = forms.CharField(label="Beneficiario", max_length=160, required=False)
    _ALLOWED_ATTACHMENT_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".bmp",
        ".tif",
        ".tiff",
        ".pdf",
    }
    _MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024

    class Meta:
        model = Transaction
        fields = ("date", "amount", "currency", "account", "project", "category", "note", "attachment", "tags")
        widgets = {
            "date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "attachment": forms.ClearableFileInput(attrs={"accept": "image/*,.pdf"}),
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
            contact = upsert_contact(
                self._owner,
                payee_name,
                entity_type=Contact.EntityType.HYBRID,
                roles={"role_payee", "role_supplier"},
            )
            ensure_legacy_records_for_contact(contact)
        elif not payee_name:
            instance.payee = None
        if commit:
            instance.save()
            self.save_m2m()
        return instance

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")
        if not attachment:
            return attachment

        ext = f".{attachment.name.rsplit('.', 1)[-1].lower()}" if "." in attachment.name else ""
        if ext not in self._ALLOWED_ATTACHMENT_EXTENSIONS:
            raise ValidationError("Formato file non supportato. Carica un'immagine o un PDF.")

        content_type = (getattr(attachment, "content_type", "") or "").lower()
        if content_type and not (content_type.startswith("image/") or content_type == "application/pdf"):
            raise ValidationError("Tipo di file non valido. Sono ammessi solo immagini o PDF.")

        if attachment.size > self._MAX_ATTACHMENT_SIZE_BYTES:
            raise ValidationError("File troppo grande. Dimensione massima: 10 MB.")

        return attachment
