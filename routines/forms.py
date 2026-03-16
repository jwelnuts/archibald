from datetime import date

from django import forms

from projects.models import Project
from projects.quick_create import create_quick_project

from .models import Routine, RoutineCategory, RoutineItem

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


def _active_categories_for(owner):
    if owner is None:
        return RoutineCategory.objects.none()
    return RoutineCategory.objects.filter(owner=owner, is_active=True).order_by("name")


def _resolve_category(*, owner, category_qs, category_choice, category_name):
    choice = (category_choice or "").strip()
    name = (category_name or "").strip()

    if choice == "__new__":
        if owner is None or not name:
            return None
        category, _ = RoutineCategory.objects.get_or_create(
            owner=owner,
            name=name,
            defaults={"is_active": True},
        )
        if not category.is_active:
            category.is_active = True
            category.save(update_fields=["is_active"])
        return category

    if choice and owner is not None:
        return category_qs.filter(id=choice).first()

    return None


class RoutineForm(forms.ModelForm):
    class Meta:
        model = Routine
        fields = ("name", "description", "is_active")

    def __init__(self, *args, **kwargs):
        kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        _apply_uikit_compact(self.fields)


class QuickRoutineForm(forms.Form):
    name = forms.CharField(label="Nome contenitore", max_length=160)
    description = forms.CharField(
        label="Descrizione",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, **kwargs):
        kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        _apply_uikit_compact(self.fields)


class QuickRoutineItemForm(forms.Form):
    routine_choice = forms.ChoiceField(label="Contenitore")
    title = forms.CharField(label="Attivita", max_length=200)
    category_choice = forms.ChoiceField(label="Categoria", required=False)
    category_name = forms.CharField(label="Nuova categoria", max_length=120, required=False)
    weekday = forms.ChoiceField(
        label="Giorno",
        choices=[(str(value), label) for value, label in RoutineItem.Weekday.choices],
    )
    time_start = forms.TimeField(
        label="Orario",
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
    )
    note = forms.CharField(
        label="Nota",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        selected_category = kwargs.pop("category", None)
        super().__init__(*args, **kwargs)
        _apply_uikit_compact(self.fields)
        self._owner = owner
        self._routine_qs = Routine.objects.none()
        self._category_qs = _active_categories_for(owner)

        if owner is not None:
            self._routine_qs = Routine.objects.filter(owner=owner, is_active=True).order_by("name")
            self.fields["routine_choice"].choices = [("", "Seleziona...")] + [
                (str(routine.id), routine.name) for routine in self._routine_qs
            ]
        else:
            self.fields["routine_choice"].choices = [("", "Seleziona...")]

        self.fields["category_choice"].choices = [("", "Senza categoria")] + [
            (str(category.id), category.name) for category in self._category_qs
        ] + [("__new__", "+ Nuova categoria")]

        if selected_category is not None:
            self.fields["category_choice"].initial = str(selected_category.id)

        if not self.is_bound and not self.initial.get("weekday"):
            self.initial["weekday"] = str(date.today().weekday())

    def clean_weekday(self):
        raw = self.cleaned_data.get("weekday")
        try:
            value = int(raw)
        except (TypeError, ValueError):
            raise forms.ValidationError("Giorno non valido.")
        allowed = {choice[0] for choice in RoutineItem.Weekday.choices}
        if value not in allowed:
            raise forms.ValidationError("Giorno non valido.")
        return value

    def clean(self):
        cleaned = super().clean()
        routine_choice = (cleaned.get("routine_choice") or "").strip()
        category_choice = (cleaned.get("category_choice") or "").strip()
        category_name = (cleaned.get("category_name") or "").strip()

        if not routine_choice:
            self.add_error("routine_choice", "Seleziona un contenitore.")
        elif not routine_choice.isdigit():
            self.add_error("routine_choice", "Contenitore non valido.")
        elif self._owner is not None and not self._routine_qs.filter(id=routine_choice).exists():
            self.add_error("routine_choice", "Contenitore non trovato.")

        if category_choice == "__new__":
            if not category_name:
                self.add_error("category_name", "Inserisci il nome della categoria.")
        elif category_choice:
            if not category_choice.isdigit():
                self.add_error("category_choice", "Categoria non valida.")
            elif self._owner is not None and not self._category_qs.filter(id=category_choice).exists():
                self.add_error("category_choice", "Categoria non trovata.")

        return cleaned

    def resolve_routine(self):
        routine_choice = (self.cleaned_data.get("routine_choice") or "").strip()
        if routine_choice and self._owner is not None:
            return self._routine_qs.filter(id=routine_choice).first()
        return None

    def resolve_category(self):
        return _resolve_category(
            owner=self._owner,
            category_qs=self._category_qs,
            category_choice=self.cleaned_data.get("category_choice"),
            category_name=self.cleaned_data.get("category_name"),
        )

    def save(self, *, owner):
        routine = self.resolve_routine()
        if routine is None:
            raise ValueError("Contenitore non valido.")
        return RoutineItem.objects.create(
            owner=owner,
            routine=routine,
            category=self.resolve_category(),
            title=(self.cleaned_data.get("title") or "").strip(),
            weekday=self.cleaned_data["weekday"],
            time_start=self.cleaned_data.get("time_start"),
            note=(self.cleaned_data.get("note") or "").strip(),
            is_active=True,
        )


class RoutineItemForm(forms.ModelForm):
    weekday = forms.ChoiceField(label="Giorno della settimana")
    routine_choice = forms.ChoiceField(label="Contenitore")
    category_choice = forms.ChoiceField(label="Categoria", required=False)
    category_name = forms.CharField(label="Nuova categoria", max_length=120, required=False)
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
        self._category_qs = _active_categories_for(owner)

        base_choices = [(str(value), label) for value, label in RoutineItem.Weekday.choices]
        if self.instance and self.instance.pk:
            self.fields["weekday"].choices = base_choices
        else:
            self.fields["weekday"].choices = [(WEEKDAY_ALL, "Tutti i giorni")] + base_choices

        if owner is not None:
            routines = Routine.objects.filter(owner=owner).order_by("name")
            self._routine_qs = routines
            self.fields["routine_choice"].choices = [("", "Seleziona...")] + [
                (str(routine.id), routine.name) for routine in routines
            ]
            self.fields["project"].queryset = self.fields["project"].queryset.filter(owner=owner).order_by("name")
            self._project_qs = self.fields["project"].queryset
        else:
            self.fields["routine_choice"].choices = [("", "Seleziona...")]

        self.fields["category_choice"].choices = [("", "Senza categoria")] + [
            (str(category.id), category.name) for category in self._category_qs
        ] + [("__new__", "+ Nuova categoria")]
        self.fields["project_choice"].choices = [("", "Nessuno"), ("__new__", "+Nuovo")] + [
            (str(project.id), project.name) for project in self._project_qs
        ]

        if self.instance and self.instance.pk and self.instance.routine_id:
            self.fields["routine_choice"].initial = str(self.instance.routine_id)
        if self.instance and self.instance.pk and self.instance.category_id:
            self.fields["category_choice"].initial = str(self.instance.category_id)
            self.fields["category_name"].initial = self.instance.category.name
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
        category_choice = (cleaned.get("category_choice") or "").strip()
        category_name = (cleaned.get("category_name") or "").strip()
        project_choice = (cleaned.get("project_choice") or "").strip()
        project_name = (cleaned.get("project_name") or "").strip()

        if not routine_choice:
            self.add_error("routine_choice", "Seleziona un contenitore.")
        elif not routine_choice.isdigit():
            self.add_error("routine_choice", "Contenitore non valido.")
        elif self._owner is not None and not self._routine_qs.filter(id=routine_choice).exists():
            self.add_error("routine_choice", "Contenitore non trovato.")

        if category_choice == "__new__":
            if not category_name:
                self.add_error("category_name", "Inserisci il nome della categoria.")
        elif category_choice:
            if not category_choice.isdigit():
                self.add_error("category_choice", "Categoria non valida.")
            elif self._owner is not None and not self._category_qs.filter(id=category_choice).exists():
                self.add_error("category_choice", "Categoria non trovata.")

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
        if routine_choice and self._owner is not None:
            return self._routine_qs.filter(id=routine_choice).first()
        return None

    def resolve_category(self):
        return _resolve_category(
            owner=self._owner,
            category_qs=self._category_qs,
            category_choice=self.cleaned_data.get("category_choice"),
            category_name=self.cleaned_data.get("category_name"),
        )

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
        instance.category = self.resolve_category()
        instance.project = self.resolve_project()
        if commit:
            instance.save()
        return instance
