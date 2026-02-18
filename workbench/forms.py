from django import forms

from .models import WorkbenchItem


class WorkbenchItemForm(forms.ModelForm):
    class Meta:
        model = WorkbenchItem
        fields = ("title", "kind", "status", "note")


class AppGeneratorForm(forms.Form):
    app_name = forms.CharField(
        max_length=40,
        label="Nome app",
        help_text="Solo lettere minuscole, numeri e underscore.",
        widget=forms.TextInput(attrs={"placeholder": "es: sales_hub"}),
    )
    prompt = forms.CharField(
        label="Richiesta funzionale",
        help_text="Descrivi obiettivi, campi principali e flusso CRUD.",
        widget=forms.Textarea(
            attrs={
                "rows": 6,
                "placeholder": (
                    "Esempio: app per gestire lead commerciali con stato, "
                    "importo stimato, data prossimo contatto e note."
                ),
            }
        ),
    )
