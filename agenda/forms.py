from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django import forms

from projects.models import Project
from projects.quick_create import create_quick_project

from .models import AgendaItem, WorkLog


class AgendaItemForm(forms.ModelForm):
    project_choice = forms.ChoiceField(label="Progetto", required=False)
    project_name = forms.CharField(label="Nuovo progetto", max_length=120, required=False)

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
        self._owner = owner
        self._project_qs = Project.objects.none()
        if owner is not None:
            self.fields["project"].queryset = Project.objects.filter(owner=owner, is_archived=False).order_by("name")
            self._project_qs = self.fields["project"].queryset
        self.fields["project_choice"].choices = [("", "Nessuno"), ("__new__", "+Nuovo")] + [
            (str(project.id), project.name) for project in self._project_qs
        ]
        if self.instance and self.instance.pk and self.instance.project_id:
            self.fields["project_choice"].initial = str(self.instance.project_id)
        elif not (self.instance and self.instance.pk):
            initial_project = self.initial.get("project")
            if initial_project:
                self.fields["project_choice"].initial = str(getattr(initial_project, "id", initial_project))
        if activity_only:
            self.fields["item_type"].choices = [(AgendaItem.ItemType.ACTIVITY, "Attivita")]
            self.fields["item_type"].initial = AgendaItem.ItemType.ACTIVITY

    def clean(self):
        cleaned = super().clean()
        project_choice = (cleaned.get("project_choice") or "").strip()
        project_name = (cleaned.get("project_name") or "").strip()
        if project_choice == "__new__" and not project_name:
            self.add_error("project_name", "Inserisci il nome del nuovo progetto.")
        elif project_choice and project_choice != "__new__":
            if not project_choice.isdigit():
                self.add_error("project_choice", "Progetto non valido.")
            elif self._owner is not None and not self._project_qs.filter(id=project_choice).exists():
                self.add_error("project_choice", "Progetto non trovato.")
        return cleaned

    def _resolve_project(self):
        project_choice = (self.cleaned_data.get("project_choice") or "").strip()
        project_name = (self.cleaned_data.get("project_name") or "").strip()
        if not project_choice or self._owner is None:
            return None
        if project_choice == "__new__":
            return create_quick_project(self._owner, project_name)
        return self._project_qs.filter(id=project_choice).first()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.project = self._resolve_project()
        if commit:
            instance.save()
        return instance


class WorkLogForm(forms.ModelForm):
    lunch_break_minutes = forms.IntegerField(required=False, min_value=0, max_value=480, initial=0)

    class Meta:
        model = WorkLog
        fields = ("work_date", "time_start", "time_end", "lunch_break_minutes", "note")
        widgets = {
            "work_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "time_start": forms.TimeInput(attrs={"type": "time", "step": "300"}),
            "time_end": forms.TimeInput(attrs={"type": "time", "step": "300"}),
            "lunch_break_minutes": forms.NumberInput(attrs={"min": "0", "max": "480", "step": "5"}),
        }
        labels = {
            "lunch_break_minutes": "Pausa pranzo (minuti)",
        }

    def clean(self):
        cleaned_data = super().clean()
        time_start = cleaned_data.get("time_start")
        time_end = cleaned_data.get("time_end")
        lunch_break_minutes = cleaned_data.get("lunch_break_minutes") or 0
        cleaned_data["lunch_break_minutes"] = int(lunch_break_minutes)

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
        if lunch_break_minutes < 0:
            self.add_error("lunch_break_minutes", "La pausa non puo essere negativa.")
            return cleaned_data
        if lunch_break_minutes > 480:
            self.add_error("lunch_break_minutes", "La pausa non puo superare 480 minuti.")
            return cleaned_data
        if lunch_break_minutes >= total_minutes:
            self.add_error("lunch_break_minutes", "La pausa deve essere inferiore all'intervallo lavorato.")
            return cleaned_data

        worked_minutes = total_minutes - int(lunch_break_minutes)
        hours = (Decimal(worked_minutes) / Decimal("60")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if hours <= Decimal("0"):
            self.add_error("time_end", "Inserisci un intervallo orario valido.")
            return cleaned_data
        if hours > Decimal("24"):
            self.add_error("time_end", "Non puoi registrare piu di 24 ore in un giorno.")
            return cleaned_data

        cleaned_data["hours"] = hours
        return cleaned_data
