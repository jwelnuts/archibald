from decimal import Decimal

from django import forms

from projects.models import Project

from .models import AgendaItem, WorkLog


class AgendaItemForm(forms.ModelForm):
    class Meta:
        model = AgendaItem
        fields = ("title", "item_type", "due_date", "due_time", "status", "project", "note")
        widgets = {
            "due_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "due_time": forms.TimeInput(attrs={"type": "time", "step": "900"}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        if owner is not None:
            self.fields["project"].queryset = Project.objects.filter(owner=owner, is_archived=False).order_by("name")


class WorkLogForm(forms.ModelForm):
    class Meta:
        model = WorkLog
        fields = ("work_date", "hours", "note")
        widgets = {
            "work_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "hours": forms.NumberInput(attrs={"step": "0.25", "min": "0.25", "max": "24"}),
        }

    def clean_hours(self):
        hours = self.cleaned_data["hours"]
        if hours is None:
            return hours
        if hours <= Decimal("0"):
            raise forms.ValidationError("Inserisci un numero di ore maggiore di zero.")
        if hours > Decimal("24"):
            raise forms.ValidationError("Non puoi registrare piu di 24 ore in un giorno.")
        return hours
