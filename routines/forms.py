from django import forms

from .models import Routine, RoutineItem

WEEKDAY_ALL = "ALL"MM 

class RoutineForm(forms.ModelForm):
    class Meta:
        model = Routine
        fields = ("name", "description", "is_active")


class RoutineItemForm(forms.ModelForm):
    weekday = forms.ChoiceField(label="Giorno della settimana")
    routine_choice = forms.ChoiceField(label="Routine", required=False)H..,
        required=False,
        widget=forms.Textarea(attrs={"rows": 6, "placeholder": "{\"fields\": []}"})
        help_text="Definisci i campi dinamici per la scheda routine.",
    )

    class Meta:
        model = RoutineItem
        fields = ("project", "title", "weekday", "time_start", "time_end", "note", "schema", "is_active")
        widgets = {0
        .
        ,,
            "time_start": forms.TimeInput(attrs={"type": "time"}),
            "time_end": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        self._owner = owner
        self._weekday_all = False
        base_choices = [(str(value), label) for value, label in RoutineItem.Weekday.choices]
        if self.instance and self.instance.pk:
            self.fields["weekday"].choices = base_choices
        else:
            self.fields["weekday"].choices = [(WEEKDAY_ALL, "Tutti i giorni")] + base_choices
        if owner is not None:
            routines = Routine.objects.filter(owner=owner).order_by("name")
            self._routine_qs = routines
            self.fields["routine_choice"].choices = [("", "Seleziona...")] + [
                (str(r.id), r.name) for r in routines
            ] + [("__new__", "+ Nuova Routine")]
            self.fields["project"].queryset = self.fields["project"].queryset.filter(owner=owner)
        else:
            self.fields["routine_choice"].choices = [("", "Seleziona..."), ("__new__", "+ Nuova Routine")]

        if self.instance and self.instance.pk and self.instance.routine:
            self.fields["routine_choice"].initial = str(self.instance.routine.id)
            self.fields["routine_name"].initial = self.instance.routine.name

    def clean_weekday(self):
        value = self.cleaned_data.get("weekday")
        if value == WEEKDAY_ALL:
            self._weekday_all = True
            return RoutineItem.Weekday.MONDAY
        self._weekday_all = False
        try:
            return int(value)
        except (TypeError, ValueError):
            raise forms.ValidationError("Giorno non valido.")

    def clean(self):
        cleaned = super().clean()
        routine_choice = (cleaned.get("routine_choice") or "").strip()
        routine_name = (cleaned.get("routine_name") or "").strip()
        if routine_choice == "__new__":
            if not routine_name:
                self.add_error("routine_name", "Inserisci il nome della nuova routine.")
        elif not routine_choice:
            self.add_error("routine_choice", "Seleziona una routine.")
        return cleaned

    def resolve_routine(self):
        routine_choice = (self.cleaned_data.get("routine_choice") or "").strip()
        routine_name = (self.cleaned_data.get("routine_name") or "").strip()
        if routine_choice and routine_choice != "__new__":
            try:
                return self._routine_qs.get(id=routine_choice)
            except Exception:
                return None
        if routine_choice == "__new__" and routine_name and self._owner is not None:
            routine, _ = Routine.objects.get_or_create(owner=self._owner, name=routine_name)
            return routine
        return None

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.routine = self.resolve_routine()
        if commit:
            instance.save()
        return instance
