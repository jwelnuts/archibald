from django import forms

from projects.models import Project

from .models import Task


class TaskForm(forms.ModelForm):
    project_choice = forms.ChoiceField(label="Progetto", required=False)
    project_name = forms.CharField(label="Nuovo progetto", max_length=120, required=False)

    class Meta:
        model = Task
        fields = ("title", "due_date", "status", "priority", "note")
        widgets = {
            "due_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
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
        return cleaned
