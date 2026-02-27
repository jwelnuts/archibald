from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

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
        activity_only = kwargs.pop("activity_only", False)
        super().__init__(*args, **kwargs)
        if owner is not None:
            self.fields["project"].queryset = Project.objects.filter(owner=owner, is_archived=False).order_by("name")
        if activity_only:
            self.fields["item_type"].choices = [(AgendaItem.ItemType.ACTIVITY, "Attivita")]
            self.fields["item_type"].initial = AgendaItem.ItemType.ACTIVITY


class WorkLogForm(forms.ModelForm):
    class Meta:
        model = WorkLog
        fields = ("work_date", "time_start", "time_end", "note")
        widgets = {
            "work_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "time_start": forms.TimeInput(attrs={"type": "time", "step": "300"}),
            "time_end": forms.TimeInput(attrs={"type": "time", "step": "300"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        time_start = cleaned_data.get("time_start")
        time_end = cleaned_data.get("time_end")

        if not time_start:
            self.add_error("time_start", "Inserisci l'orario di inizio.")
        if not time_end:
            self.add_error("time_end", "Inserisci l'orario di fine.")
        if not time_start or not time_end:
            return cleaned_data

        if time_end <= time_start:
            self.add_error("time_end", "L'orario di fine deve essere successivo all'orario di inizio.")
            return cleaned_data

        start_dt = datetime.combine(datetime.min.date(), time_start)
        end_dt = datetime.combine(datetime.min.date(), time_end)
        total_minutes = int((end_dt - start_dt).total_seconds() // 60)
        hours = (Decimal(total_minutes) / Decimal("60")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if hours <= Decimal("0"):
            self.add_error("time_end", "Inserisci un intervallo orario valido.")
            return cleaned_data
        if hours > Decimal("24"):
            self.add_error("time_end", "Non puoi registrare piu di 24 ore in un giorno.")
            return cleaned_data

        cleaned_data["hours"] = hours
        return cleaned_data
