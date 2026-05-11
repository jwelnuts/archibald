from datetime import date

from django import forms

from projects.models import Project
from projects.quick_create import create_quick_project

from .models import TodoList, TodoCategory, TodoItem

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
        return TodoCategory.objects.none()
    return TodoCategory.objects.filter(owner=owner, is_active=True).order_by("name")


def _resolve_category(*, owner, category_qs, category_choice, category_name):
    choice = (category_choice or "").strip()
    name = (category_name or "").strip()

    if choice == "__new__":
        if owner is None or not name:
            return None
        category, _ = TodoCategory.objects.get_or_create(
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


class TodoListForm(forms.ModelForm):
    class Meta:
        model = TodoList
        fields = ("name", "description", "is_active")

    def __init__(self, *args, **kwargs):
        kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        _apply_uikit_compact(self.fields)


class QuickTodoListForm(forms.Form):
    name = forms.CharField(label="Nome lista", max_length=160)
    description = forms.CharField(
        label="Descrizione",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, **kwargs):
        kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        _apply_uikit_compact(self.fields)


class QuickTodoItemForm(forms.Form):
    todo_list_choice = forms.ChoiceField(label="Lista", required=False)
    title = forms.CharField(label="Attivita", max_length=200)
    category_choice = forms.ChoiceField(label="Categoria", required=False)
    category_name = forms.CharField(label="Nuova categoria", max_length=120, required=False)
    weekday = forms.ChoiceField(
        label="Giorno",
        choices=[(str(value), label) for value, label in TodoItem.Weekday.choices],
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
    is_standalone = forms.BooleanField(label="Attivita singola (senza lista)", required=False)

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        selected_category = kwargs.pop("category", None)
        super().__init__(*args, **kwargs)
        _apply_uikit_compact(self.fields)
        self._owner = owner
        self._todo_list_qs = TodoList.objects.none()
        self._category_qs = _active_categories_for(owner)

        if owner is not None:
            self._todo_list_qs = TodoList.objects.filter(owner=owner, is_active=True).order_by("name")
            self.fields["todo_list_choice"].choices = [("", "Seleziona...")] + [
                (str(lst.id), lst.name) for lst in self._todo_list_qs
            ]
        else:
            self.fields["todo_list_choice"].choices = [("", "Seleziona...")]

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
        allowed = {choice[0] for choice in TodoItem.Weekday.choices}
        if value not in allowed:
            raise forms.ValidationError("Giorno non valido.")
        return value

    def clean(self):
        cleaned = super().clean()
        is_standalone = cleaned.get("is_standalone")
        todo_list_choice = (cleaned.get("todo_list_choice") or "").strip()
        category_choice = (cleaned.get("category_choice") or "").strip()
        category_name = (cleaned.get("category_name") or "").strip()

        if not is_standalone:
            if not todo_list_choice:
                self.add_error("todo_list_choice", "Seleziona una lista.")
            elif not todo_list_choice.isdigit():
                self.add_error("todo_list_choice", "Lista non valida.")
            elif self._owner is not None and not self._todo_list_qs.filter(id=todo_list_choice).exists():
                self.add_error("todo_list_choice", "Lista non trovata.")

        if category_choice == "__new__":
            if not category_name:
                self.add_error("category_name", "Inserisci il nome della categoria.")
        elif category_choice:
            if not category_choice.isdigit():
                self.add_error("category_choice", "Categoria non valida.")
            elif self._owner is not None and not self._category_qs.filter(id=category_choice).exists():
                self.add_error("category_choice", "Categoria non trovata.")

        return cleaned

    def resolve_todo_list(self):
        if self.cleaned_data.get("is_standalone"):
            return None
        todo_list_choice = (self.cleaned_data.get("todo_list_choice") or "").strip()
        if todo_list_choice and self._owner is not None:
            return self._todo_list_qs.filter(id=todo_list_choice).first()
        return None

    def resolve_category(self):
        return _resolve_category(
            owner=self._owner,
            category_qs=self._category_qs,
            category_choice=self.cleaned_data.get("category_choice"),
            category_name=self.cleaned_data.get("category_name"),
        )

    def save(self, *, owner):
        is_standalone = self.cleaned_data.get("is_standalone")
        todo_list = self.resolve_todo_list()
        if not is_standalone and todo_list is None:
            raise ValueError("Lista non valida.")
        return TodoItem.objects.create(
            owner=owner,
            todo_list=todo_list,
            category=self.resolve_category(),
            title=(self.cleaned_data.get("title") or "").strip(),
            weekday=self.cleaned_data["weekday"],
            time_start=self.cleaned_data.get("time_start"),
            note=(self.cleaned_data.get("note") or "").strip(),
            is_active=True,
            is_standalone=is_standalone,
        )


class TodoItemForm(forms.ModelForm):
    weekday = forms.ChoiceField(label="Giorno della settimana")
    todo_list_choice = forms.ChoiceField(label="Lista", required=False)
    category_choice = forms.ChoiceField(label="Categoria", required=False)
    category_name = forms.CharField(label="Nuova categoria", max_length=120, required=False)
    project_choice = forms.ChoiceField(label="Progetto", required=False)
    project_name = forms.CharField(label="Nuovo progetto", max_length=120, required=False)
    is_standalone = forms.BooleanField(label="Attivita singola (senza lista)", required=False)

    class Meta:
        model = TodoItem
        fields = (
            "project",
            "title",
            "weekday",
            "time_start",
            "time_end",
            "note",
            "schema",
            "is_active",
            "item_type",
            "due_date",
            "due_time",
            "priority",
            "status",
        )
        widgets = {
            "time_start": forms.TimeInput(attrs={"type": "time"}),
            "time_end": forms.TimeInput(attrs={"type": "time"}),
            "due_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "due_time": forms.TimeInput(attrs={"type": "time", "step": "900"}),
            "schema": forms.Textarea(
                attrs={"rows": 6, "placeholder": '{"fields": []}'}
            ),
        }
        help_texts = {
            "schema": "Definisci i campi dinamici per la scheda.",
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        _apply_uikit_compact(self.fields)
        self._owner = owner
        self._weekday_all = False
        self._todo_list_qs = TodoList.objects.none()
        self._project_qs = Project.objects.none()
        self._category_qs = _active_categories_for(owner)

        base_choices = [(str(value), label) for value, label in TodoItem.Weekday.choices]
        if self.instance and self.instance.pk:
            self.fields["weekday"].choices = base_choices
        else:
            self.fields["weekday"].choices = [(WEEKDAY_ALL, "Tutti i giorni")] + base_choices

        if owner is not None:
            todo_lists = TodoList.objects.filter(owner=owner).order_by("name")
            self._todo_list_qs = todo_lists
            self.fields["todo_list_choice"].choices = [("", "Seleziona...")] + [
                (str(lst.id), lst.name) for lst in todo_lists
            ]
            self.fields["project"].queryset = self.fields["project"].queryset.filter(owner=owner).order_by("name")
            self._project_qs = self.fields["project"].queryset
        else:
            self.fields["todo_list_choice"].choices = [("", "Seleziona...")]

        self.fields["category_choice"].choices = [("", "Senza categoria")] + [
            (str(category.id), category.name) for category in self._category_qs
        ] + [("__new__", "+ Nuova categoria")]
        self.fields["project_choice"].choices = [("", "Nessuno"), ("__new__", "+Nuovo")] + [
            (str(project.id), project.name) for project in self._project_qs
        ]

        if self.instance and self.instance.pk and self.instance.todo_list_id:
            self.fields["todo_list_choice"].initial = str(self.instance.todo_list_id)
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
            return TodoItem.Weekday.MONDAY
        self._weekday_all = False
        try:
            return int(value)
        except (TypeError, ValueError):
            raise forms.ValidationError("Giorno non valido.")

    def clean(self):
        cleaned = super().clean()
        is_standalone = cleaned.get("is_standalone")
        todo_list_choice = (cleaned.get("todo_list_choice") or "").strip()
        category_choice = (cleaned.get("category_choice") or "").strip()
        category_name = (cleaned.get("category_name") or "").strip()
        project_choice = (cleaned.get("project_choice") or "").strip()
        project_name = (cleaned.get("project_name") or "").strip()

        if not is_standalone:
            if not todo_list_choice:
                self.add_error("todo_list_choice", "Seleziona una lista.")
            elif not todo_list_choice.isdigit():
                self.add_error("todo_list_choice", "Lista non valida.")
            elif self._owner is not None and not self._todo_list_qs.filter(id=todo_list_choice).exists():
                self.add_error("todo_list_choice", "Lista non trovata.")

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

    def resolve_todo_list(self):
        todo_list_choice = (self.cleaned_data.get("todo_list_choice") or "").strip()
        if todo_list_choice and self._owner is not None:
            return self._todo_list_qs.filter(id=todo_list_choice).first()
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
        instance.todo_list = self.resolve_todo_list()
        instance.category = self.resolve_category()
        instance.project = self.resolve_project()
        instance.is_standalone = bool(self.cleaned_data.get("is_standalone"))
        if commit:
            instance.save()
        return instance
