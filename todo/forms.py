from django import forms

from projects.models import Project

from .models import Task


class TaskForm(forms.ModelForm):
    project_choice = forms.ChoiceField(label="Progetto", required=False)
    project_name = forms.CharField(label="Nuovo progetto", max_length=120, required=False)

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
        if owner is not None:
            self._project_qs = Project.objects.filter(owner=owner, is_archived=False).order_by("name")
            self.fields["project_choice"].choices = [("", "Seleziona...")] + [
                (str(p.id), p.name) for p in self._project_qs
            ] + [("__new__", "+ Nuovo Progetto")]
        else:
            self.fields["project_choice"].choices = [("", "Seleziona..."), ("__new__", "+ Nuovo Progetto")]

        if self.instance and self.instance.pk and self.instance.project:
            self.fields["project_choice"].initial = str(self.instance.project.id)
            self.fields["project_name"].initial = self.instance.project.name

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

    def save(self, commit=True):
        instance = super().save(commit=False)
        project_choice = (self.cleaned_data.get("project_choice") or "").strip()
        project_name = (self.cleaned_data.get("project_name") or "").strip()

        if project_choice and project_choice != "__new__":
            try:
                instance.project = self._project_qs.get(id=project_choice)
            except Exception:
                instance.project = None
        elif project_name and self._owner is not None:
            project, _ = Project.objects.get_or_create(owner=self._owner, name=project_name)
            instance.project = project
        else:
            instance.project = None

        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned = super().clean()
        project_choice = (cleaned.get("project_choice") or "").strip()
        project_name = (cleaned.get("project_name") or "").strip()
        if project_choice == "__new__" and not project_name:
            self.add_error("project_name", "Inserisci il nome del nuovo progetto.")
        if cleaned.get("due_time") and not cleaned.get("due_date"):
            self.add_error("due_date", "Imposta una data se specifichi anche l'orario.")
        return cleaned
