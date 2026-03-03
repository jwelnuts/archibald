from django import forms

from contacts.models import Contact
from contacts.services import ensure_legacy_records_for_contact, upsert_contact
from projects.models import Category, Project
from projects.quick_create import create_quick_category, create_quick_project
from subscriptions.models import Currency
from transactions.models import Transaction
from .models import IncomeSource


class IncomeForm(forms.ModelForm):
    source_choice = forms.ChoiceField(label="Fonte del denaro", required=False)
    source_name = forms.CharField(label="Fonte del denaro", max_length=160, required=False)
    project_choice = forms.ChoiceField(label="Progetto", required=False)
    project_name = forms.CharField(label="Nuovo progetto", max_length=120, required=False)
    category_choice = forms.ChoiceField(label="Categoria", required=False)
    category_name = forms.CharField(label="Nuova categoria", max_length=80, required=False)

    class Meta:
        model = Transaction
        fields = ("date", "amount", "currency", "account", "project", "category", "note", "tags")
        widgets = {
            "date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        self._owner = owner
        self._project_qs = Project.objects.none()
        self._category_qs = Category.objects.none()
        if owner is not None:
            self.fields["account"].queryset = self.fields["account"].queryset.filter(owner=owner)
            self.fields["project"].queryset = self.fields["project"].queryset.filter(owner=owner)
            self.fields["category"].queryset = self.fields["category"].queryset.filter(owner=owner)
            self.fields["tags"].queryset = self.fields["tags"].queryset.filter(owner=owner)
            self._project_qs = self.fields["project"].queryset.order_by("name")
            self._category_qs = self.fields["category"].queryset.order_by("name")
        currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
        self.fields["currency"].queryset = Currency.objects.filter(code="EUR")
        self.fields["currency"].initial = currency
        choices = [("", "Seleziona..."), ("__new__", "Nuova fonte...")]
        if owner is not None:
            sources = IncomeSource.objects.filter(owner=owner).order_by("name")
            choices += [(str(source.id), source.name) for source in sources]
        self.fields["source_choice"].choices = choices

        project_choices = [("", "Nessuno"), ("__new__", "+Nuovo")]
        category_choices = [("", "Nessuna"), ("__new__", "+Nuovo")]
        project_choices += [(str(project.id), project.name) for project in self._project_qs]
        category_choices += [(str(category.id), category.name) for category in self._category_qs]
        self.fields["project_choice"].choices = project_choices
        self.fields["category_choice"].choices = category_choices

        if self.instance and self.instance.pk and self.instance.income_source:
            self.fields["source_choice"].initial = str(self.instance.income_source.id)
        if self.instance and self.instance.pk:
            if self.instance.project_id:
                self.fields["project_choice"].initial = str(self.instance.project_id)
            if self.instance.category_id:
                self.fields["category_choice"].initial = str(self.instance.category_id)
        else:
            initial_project = self.initial.get("project")
            initial_category = self.initial.get("category")
            if initial_project:
                self.fields["project_choice"].initial = str(getattr(initial_project, "id", initial_project))
            if initial_category:
                self.fields["category_choice"].initial = str(getattr(initial_category, "id", initial_category))

    def _is_valid_selection_id(self, value):
        try:
            int(value)
            return True
        except (TypeError, ValueError):
            return False

    def clean(self):
        cleaned = super().clean()
        source_choice = (cleaned.get("source_choice") or "").strip()
        source_name = (cleaned.get("source_name") or "").strip()
        project_choice = (cleaned.get("project_choice") or "").strip()
        project_name = (cleaned.get("project_name") or "").strip()
        category_choice = (cleaned.get("category_choice") or "").strip()
        category_name = (cleaned.get("category_name") or "").strip()

        if source_choice == "__new__" and not source_name:
            self.add_error("source_name", "Inserisci il nome della nuova fonte.")

        if project_choice == "__new__" and not project_name:
            self.add_error("project_name", "Inserisci il nome del nuovo progetto.")
        elif project_choice and project_choice != "__new__":
            if not self._is_valid_selection_id(project_choice):
                self.add_error("project_choice", "Progetto non valido.")
            elif self._owner is not None and not self._project_qs.filter(id=project_choice).exists():
                self.add_error("project_choice", "Progetto non trovato.")

        if category_choice == "__new__" and not category_name:
            self.add_error("category_name", "Inserisci il nome della nuova categoria.")
        elif category_choice and category_choice != "__new__":
            if not self._is_valid_selection_id(category_choice):
                self.add_error("category_choice", "Categoria non valida.")
            elif self._owner is not None and not self._category_qs.filter(id=category_choice).exists():
                self.add_error("category_choice", "Categoria non trovata.")

        return cleaned

    def _resolve_project(self):
        choice = (self.cleaned_data.get("project_choice") or "").strip()
        project_name = (self.cleaned_data.get("project_name") or "").strip()

        if not choice or self._owner is None:
            return None
        if choice == "__new__":
            return create_quick_project(self._owner, project_name)
        return self._project_qs.filter(id=choice).first()

    def _resolve_category(self):
        choice = (self.cleaned_data.get("category_choice") or "").strip()
        category_name = (self.cleaned_data.get("category_name") or "").strip()

        if not choice or self._owner is None:
            return None
        if choice == "__new__":
            return create_quick_category(self._owner, category_name)
        return self._category_qs.filter(id=choice).first()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.project = self._resolve_project()
        instance.category = self._resolve_category()
        source_choice = (self.cleaned_data.get("source_choice") or "").strip()
        source_name = (self.cleaned_data.get("source_name") or "").strip()
        if source_choice and source_choice not in {"__new__"}:
            try:
                source_obj = IncomeSource.objects.get(id=source_choice, owner=self._owner)
                instance.income_source = source_obj
                contact = upsert_contact(
                    self._owner,
                    source_obj.name,
                    entity_type=Contact.EntityType.HYBRID,
                    website=source_obj.website,
                    roles={"role_income_source", "role_customer"},
                )
                ensure_legacy_records_for_contact(contact)
            except IncomeSource.DoesNotExist:
                instance.income_source = None
        elif source_name and self._owner is not None:
            source_obj, _ = IncomeSource.objects.get_or_create(owner=self._owner, name=source_name)
            instance.income_source = source_obj
            contact = upsert_contact(
                self._owner,
                source_name,
                entity_type=Contact.EntityType.HYBRID,
                website=source_obj.website,
                roles={"role_income_source", "role_customer"},
            )
            ensure_legacy_records_for_contact(contact)
        elif not source_choice:
            instance.income_source = None
        if commit:
            instance.save()
            self.save_m2m()
        return instance
