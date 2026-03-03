from django import forms

from projects.models import Category, Project
from projects.quick_create import create_quick_category, create_quick_project

from .models import PlannerItem


class PlannerItemForm(forms.ModelForm):
    category_choice = forms.ChoiceField(label="Categoria", required=False)
    category_name = forms.CharField(label="Nuova categoria", max_length=80, required=False)
    project_choice = forms.ChoiceField(label="Progetto", required=False)
    project_name = forms.CharField(label="Nuovo progetto", max_length=120, required=False)

    class Meta:
        model = PlannerItem
        fields = ("title", "due_date", "amount", "category", "project", "status", "note")
        widgets = {
            "due_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        self._owner = owner
        self._category_qs = Category.objects.none()
        self._project_qs = Project.objects.none()
        if owner is not None:
            self.fields["category"].queryset = self.fields["category"].queryset.filter(owner=owner).order_by("name")
            self.fields["project"].queryset = self.fields["project"].queryset.filter(owner=owner).order_by("name")
            self._category_qs = self.fields["category"].queryset
            self._project_qs = self.fields["project"].queryset

        self.fields["category_choice"].choices = [("", "Nessuna"), ("__new__", "+Nuovo")] + [
            (str(category.id), category.name) for category in self._category_qs
        ]
        self.fields["project_choice"].choices = [("", "Nessuno"), ("__new__", "+Nuovo")] + [
            (str(project.id), project.name) for project in self._project_qs
        ]

        if self.instance and self.instance.pk:
            if self.instance.category_id:
                self.fields["category_choice"].initial = str(self.instance.category_id)
            if self.instance.project_id:
                self.fields["project_choice"].initial = str(self.instance.project_id)
        else:
            initial_category = self.initial.get("category")
            initial_project = self.initial.get("project")
            if initial_category:
                self.fields["category_choice"].initial = str(getattr(initial_category, "id", initial_category))
            if initial_project:
                self.fields["project_choice"].initial = str(getattr(initial_project, "id", initial_project))

    def _is_valid_selection_id(self, value):
        try:
            int(value)
            return True
        except (TypeError, ValueError):
            return False

    def clean(self):
        cleaned = super().clean()
        category_choice = (cleaned.get("category_choice") or "").strip()
        category_name = (cleaned.get("category_name") or "").strip()
        project_choice = (cleaned.get("project_choice") or "").strip()
        project_name = (cleaned.get("project_name") or "").strip()

        if category_choice == "__new__" and not category_name:
            self.add_error("category_name", "Inserisci il nome della nuova categoria.")
        elif category_choice and category_choice != "__new__":
            if not self._is_valid_selection_id(category_choice):
                self.add_error("category_choice", "Categoria non valida.")
            elif self._owner is not None and not self._category_qs.filter(id=category_choice).exists():
                self.add_error("category_choice", "Categoria non trovata.")

        if project_choice == "__new__" and not project_name:
            self.add_error("project_name", "Inserisci il nome del nuovo progetto.")
        elif project_choice and project_choice != "__new__":
            if not self._is_valid_selection_id(project_choice):
                self.add_error("project_choice", "Progetto non valido.")
            elif self._owner is not None and not self._project_qs.filter(id=project_choice).exists():
                self.add_error("project_choice", "Progetto non trovato.")

        return cleaned

    def _resolve_category(self):
        choice = (self.cleaned_data.get("category_choice") or "").strip()
        category_name = (self.cleaned_data.get("category_name") or "").strip()
        if not choice or self._owner is None:
            return None
        if choice == "__new__":
            return create_quick_category(self._owner, category_name)
        return self._category_qs.filter(id=choice).first()

    def _resolve_project(self):
        choice = (self.cleaned_data.get("project_choice") or "").strip()
        project_name = (self.cleaned_data.get("project_name") or "").strip()
        if not choice or self._owner is None:
            return None
        if choice == "__new__":
            return create_quick_project(self._owner, project_name)
        return self._project_qs.filter(id=choice).first()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.category = self._resolve_category()
        instance.project = self._resolve_project()
        if commit:
            instance.save()
        return instance
