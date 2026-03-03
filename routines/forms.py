from django import forms

from projects.models import Project
from projects.quick_create import create_quick_project

from .models import Routine, RoutineItem

WEEKDAY_ALL = "ALL"


def _append_class(widget, classes: str):
    current = (widget.attrs.get("class") or "").strip()
    widget.attrs["class"] = f"{current} {classes}".strip()


def _apply_uikit_compact(fields):
    for field in fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            _append_class(widget, "uk-checkbox")
            continue
        if isinstance(widget, forms.Select):
            _append_class(widget, "uk-select uk-form-small")
            continue
        if isinstance(widget, forms.Textarea):
            _append_class(widget, "uk-textarea uk-form-small")
            continue
        _append_class(widget, "uk-input uk-form-small")


class RoutineForm(forms.ModelForm):
    class Meta:
        model = Routine
        fields = ("name", "description", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_uikit_compact(self.fields)


class RoutineItemForm(forms.ModelForm):
    weekday = forms.ChoiceField(label="Giorno della settimana")
    routine_choice = forms.ChoiceField(label="Routine", required=False)
    routine_name = forms.CharField(
        required=False,
        label="Nome nuova routine",
        max_length=160,
    )
    project_choice = forms.ChoiceField(label="Progetto", required=False)
    project_name = forms.CharField(label="Nuovo progetto", max_length=120, required=False)

    class Meta:
        model = RoutineItem
        fields = (
            "project",
            "title",
            "weekday",
            "time_start",
            "time_end",
            "note",
            "schema",
            "is_active",
        )
        widgets = {
            "time_start": forms.TimeInput(attrs={"type": "time"}),
            "time_end": forms.TimeInput(attrs={"type": "time"}),
            "schema": forms.Textarea(
                attrs={"rows": 6, "placeholder": '{"fields": []}'}
            ),
        }
        help_texts = {
            "schema": "Definisci i campi dinamici per la scheda routine.",
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        _apply_uikit_compact(self.fields)
        self._owner = owner
        self._weekday_all = False
        self._routine_qs = Routine.objects.none()
        self._project_qs = Project.objects.none()

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
            self.fields["project"].queryset = self.fields["project"].queryset.filter(owner=owner).order_by("name")
            self._project_qs = self.fields["project"].queryset
        else:
            self.fields["routine_choice"].choices = [("", "Seleziona..."), ("__new__", "+ Nuova Routine")]
        self.fields["project_choice"].choices = [("", "Nessuno"), ("__new__", "+Nuovo")] + [
            (str(project.id), project.name) for project in self._project_qs
        ]

        if self.instance and self.instance.pk and self.instance.routine_id:
            self.fields["routine_choice"].initial = str(self.instance.routine_id)
            self.fields["routine_name"].initial = self.instance.routine.name
        if self.instance and self.instance.pk and self.instance.project_id:
            self.fields["project_choice"].initial = str(self.instance.project_id)
        elif not (self.instance and self.instance.pk):
            initial_project = self.initial.get("project")
            if initial_project:
                self.fields["project_choice"].initial = str(getattr(initial_project, "id", initial_project))

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
        project_choice = (cleaned.get("project_choice") or "").strip()
        project_name = (cleaned.get("project_name") or "").strip()
        if routine_choice == "__new__":
            if not routine_name:
                self.add_error("routine_name", "Inserisci il nome della nuova routine.")
        elif not routine_choice:
            self.add_error("routine_choice", "Seleziona una routine.")
        if project_choice == "__new__" and not project_name:
            self.add_error("project_name", "Inserisci il nome del nuovo progetto.")
        elif project_choice and project_choice != "__new__":
            if not project_choice.isdigit():
                self.add_error("project_choice", "Progetto non valido.")
            elif self._owner is not None and not self._project_qs.filter(id=project_choice).exists():
                self.add_error("project_choice", "Progetto non trovato.")
        return cleaned

    def resolve_routine(self):
        routine_choice = (self.cleaned_data.get("routine_choice") or "").strip()
        routine_name = (self.cleaned_data.get("routine_name") or "").strip()

        if routine_choice and routine_choice != "__new__":
            try:
                return self._routine_qs.get(id=routine_choice)
            except (Routine.DoesNotExist, ValueError, TypeError):
                return None

        if routine_choice == "__new__" and routine_name and self._owner is not None:
            routine, _ = Routine.objects.get_or_create(owner=self._owner, name=routine_name)
            return routine

        return None

    def resolve_project(self):
        project_choice = (self.cleaned_data.get("project_choice") or "").strip()
        project_name = (self.cleaned_data.get("project_name") or "").strip()

        if not project_choice or self._owner is None:
            return None
        if project_choice == "__new__":
            return create_quick_project(self._owner, project_name)
        return self._project_qs.filter(id=project_choice).first()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.routine = self.resolve_routine()
        instance.project = self.resolve_project()
        if commit:
            instance.save()
        return instance
