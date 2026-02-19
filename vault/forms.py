from django import forms

from .models import VaultItem


class VaultSetupForm(forms.Form):
    code = forms.CharField(
        label="Codice TOTP",
        max_length=6,
        min_length=6,
        help_text="Inserisci il codice a 6 cifre del tuo Authenticator.",
    )


class VaultUnlockForm(forms.Form):
    code = forms.CharField(label="Codice TOTP", max_length=6, min_length=6)


class VaultItemForm(forms.ModelForm):
    secret_value = forms.CharField(
        label="Password / Segreto",
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    notes_value = forms.CharField(
        label="Note private",
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
    )

    class Meta:
        model = VaultItem
        fields = ("title", "kind", "login", "website_url")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["secret_value"].initial = self.instance.get_secret_value()
            self.fields["notes_value"].initial = self.instance.get_notes_value()

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        secret = (cleaned.get("secret_value") or "").strip()
        notes = (cleaned.get("notes_value") or "").strip()
        if kind == VaultItem.Kind.PASSWORD and not secret:
            self.add_error("secret_value", "Per i record password il valore e obbligatorio.")
        if kind == VaultItem.Kind.NOTE and not notes and not secret:
            self.add_error("notes_value", "Inserisci almeno una nota o un valore segreto.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.set_secret_value(self.cleaned_data.get("secret_value") or "")
        instance.set_notes_value(self.cleaned_data.get("notes_value") or "")
        if commit:
            instance.save()
        return instance
