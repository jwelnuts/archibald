from django import forms

from .models import Contact


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
