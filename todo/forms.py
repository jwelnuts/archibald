from django import forms

from projects.models import Category
from projects.models import Project
from projects.quick_create import create_quick_category, create_quick_project

from .models import Task


class TaskForm(forms.ModelForm):
    project_choice = forms.ChoiceField(label="Progetto", required=False)
    project_name = forms.CharField(label="Nuovo progetto", max_length=120, required=False)
    category_choice = forms.ChoiceField(label="Categoria", required=False)
    category_name = forms.CharField(label="Nuova categoria", max_length=80, required=False)

    class Meta:
        model = Task
        fields = ("title", "item_type", "due_date", "due_time", "status", "priority", "note")
        widgets = {
            "due_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "due_time": forms.TimeInput(attrs={"type": "time", "step": "900"}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        self._owner = owner
        self._project_qs = Project.objects.none()
        self._category_qs = Category.objects.none()
        if owner is not None:
            self._project_qs = Project.objects.filter(owner=owner, is_archived=False).order_by("name")
            self._category_qs = Category.objects.filter(owner=owner).order_by("name")
            self.fields["project_choice"].choices = [("", "Seleziona...")] + [
                (str(p.id), p.name) for p in self._project_qs
            ] + [("__new__", "+ Nuovo Progetto")]
            self.fields["category_choice"].choices = [("", "Seleziona...")] + [
                (str(c.id), c.name) for c in self._category_qs
            ] + [("__new__", "+ Nuova Categoria")]
        else:
            self.fields["project_choice"].choices = [("", "Seleziona..."), ("__new__", "+ Nuovo Progetto")]
            self.fields["category_choice"].choices = [("", "Seleziona..."), ("__new__", "+ Nuova Categoria")]

        if self.instance and self.instance.pk and self.instance.project:
            self.fields["project_choice"].initial = str(self.instance.project.id)
            self.fields["project_name"].initial = self.instance.project.name
        if self.instance and self.instance.pk and self.instance.category:
            self.fields["category_choice"].initial = str(self.instance.category.id)
            self.fields["category_name"].initial = self.instance.category.name

        for name, field in self.fields.items():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            classes = []
            if isinstance(widget, forms.Select):
                classes = ["uk-select", "uk-form-small"]
            elif isinstance(widget, forms.Textarea):
                classes = ["uk-textarea", "uk-form-small"]
            else:
                classes = ["uk-input", "uk-form-small"]
            widget.attrs["class"] = " ".join(part for part in [existing, *classes] if part).strip()

            if name == "title":
                widget.attrs.setdefault("placeholder", "Titolo attivita")
            if name == "project_name":
                widget.attrs.setdefault("placeholder", "Nome nuovo progetto")
            if name == "category_name":
                widget.attrs.setdefault("placeholder", "Nome nuova categoria")

    def save(self, commit=True):
        instance = super().save(commit=False)
        project_choice = (self.cleaned_data.get("project_choice") or "").strip()
        project_name = (self.cleaned_data.get("project_name") or "").strip()
        category_choice = (self.cleaned_data.get("category_choice") or "").strip()
        category_name = (self.cleaned_data.get("category_name") or "").strip()

        if project_choice and project_choice != "__new__":
            try:
                instance.project = self._project_qs.get(id=project_choice)
            except Exception:
                instance.project = None
        elif project_choice == "__new__" and project_name and self._owner is not None:
            instance.project = create_quick_project(self._owner, project_name)
        else:
            instance.project = None

        if category_choice and category_choice != "__new__":
            try:
                instance.category = self._category_qs.get(id=category_choice)
            except Exception:
                instance.category = None
        elif category_choice == "__new__" and category_name and self._owner is not None:
            instance.category = create_quick_category(self._owner, category_name)
        else:
            instance.category = None

        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned = super().clean()
        project_choice = (cleaned.get("project_choice") or "").strip()
        project_name = (cleaned.get("project_name") or "").strip()
        category_choice = (cleaned.get("category_choice") or "").strip()
        category_name = (cleaned.get("category_name") or "").strip()
        if project_choice == "__new__" and not project_name:
            self.add_error("project_name", "Inserisci il nome del nuovo progetto.")
        if category_choice == "__new__" and not category_name:
            self.add_error("category_name", "Inserisci il nome della nuova categoria.")
        if cleaned.get("due_time") and not cleaned.get("due_date"):
            self.add_error("due_date", "Imposta una data se specifichi anche l'orario.")
        return cleaned
