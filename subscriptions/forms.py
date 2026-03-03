from django import forms

from core.models import Payee
from projects.models import Category, Project
from projects.quick_create import create_quick_category, create_quick_project
from .models import Currency, Subscription


class SubscriptionForm(forms.ModelForm):
    payee_choice = forms.ChoiceField(label="Beneficiario", required=False)
    payee_name = forms.CharField(label="Beneficiario", max_length=160, required=False)
    category_choice = forms.ChoiceField(label="Categoria", required=False)
    category_name = forms.CharField(label="Categoria", max_length=80, required=False)
    project_choice = forms.ChoiceField(label="Progetto", required=False)
    project_name = forms.CharField(label="Nuovo progetto", max_length=120, required=False)

    class Meta:
        model = Subscription
        fields = (
            "name",
            "project",
            "account",
            "currency",
            "amount",
            "start_date",
            "next_due_date",
            "end_date",
            "interval",
            "interval_unit",
            "status",
            "autopay",
            "note",
            "tags",
        )
        widgets = {
            "start_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "next_due_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "end_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        self._owner = owner
        self._category_qs = Category.objects.none()
        self._project_qs = Project.objects.none()
        if owner is not None:
            payees = Payee.objects.filter(owner=owner).order_by("name")
            self.fields["payee_choice"].choices = [("", "Seleziona...")] + [
                (str(p.id), p.name) for p in payees
            ] + [("__new__", "+ Nuovo Beneficiario")]
            categories = Category.objects.filter(owner=owner).order_by("name")
            self._category_qs = categories
            self.fields["category_choice"].choices = [("", "Seleziona...")] + [
                (str(c.id), c.name) for c in categories
            ] + [("__new__", "+ Nuova Categoria")]
            self.fields["project"].queryset = self.fields["project"].queryset.filter(owner=owner).order_by("name")
            self._project_qs = self.fields["project"].queryset
            self.fields["project_choice"].choices = [("", "Nessuno")] + [
                (str(p.id), p.name) for p in self._project_qs
            ] + [("__new__", "+Nuovo")]
            self.fields["account"].queryset = self.fields["account"].queryset.filter(owner=owner)
            self.fields["tags"].queryset = self.fields["tags"].queryset.filter(owner=owner)
        else:
            self.fields["payee_choice"].choices = [("", "Seleziona..."), ("__new__", "+ Nuovo Beneficiario")]
            self.fields["category_choice"].choices = [("", "Seleziona..."), ("__new__", "+ Nuova Categoria")]
            self.fields["project_choice"].choices = [("", "Nessuno"), ("__new__", "+Nuovo")]
        currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
        self._default_currency = currency
        self.fields["currency"].queryset = Currency.objects.filter(code="EUR")
        self.fields["currency"].initial = currency
        self.fields["currency"].required = False
        if self.instance and self.instance.pk and self.instance.payee:
            self.fields["payee_name"].initial = self.instance.payee.name
            self.fields["payee_choice"].initial = str(self.instance.payee.id)
        if self.instance and self.instance.pk and self.instance.category:
            self.fields["category_name"].initial = self.instance.category.name
            self.fields["category_choice"].initial = str(self.instance.category.id)
        if self.instance and self.instance.pk and self.instance.project:
            self.fields["project_name"].initial = self.instance.project.name
            self.fields["project_choice"].initial = str(self.instance.project.id)
        elif not (self.instance and self.instance.pk):
            initial_project = self.initial.get("project")
            if initial_project:
                self.fields["project_choice"].initial = str(getattr(initial_project, "id", initial_project))

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            return name
        if self._owner is not None:
            qs = Subscription.objects.filter(owner=self._owner, name=name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Esiste gia un abbonamento con questo nome.")
        return name

    def clean(self):
        cleaned = super().clean()
        category_choice = (cleaned.get("category_choice") or "").strip()
        category_name = (cleaned.get("category_name") or "").strip()
        project_choice = (cleaned.get("project_choice") or "").strip()
        project_name = (cleaned.get("project_name") or "").strip()

        if category_choice == "__new__" and not category_name:
            self.add_error("category_name", "Inserisci il nome della nuova categoria.")
        elif category_choice and category_choice != "__new__":
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
        if not instance.currency_id:
            instance.currency = getattr(self, "_default_currency", None)
        payee_choice = (self.cleaned_data.get("payee_choice") or "").strip()
        payee_name = (self.cleaned_data.get("payee_name") or "").strip()
        if payee_choice and payee_choice not in {"__new__"}:
            try:
                instance.payee = Payee.objects.get(id=payee_choice, owner=self._owner)
            except Payee.DoesNotExist:
                instance.payee = None
        elif payee_choice == "__new__" and payee_name and self._owner is not None:
            payee_obj, _ = Payee.objects.get_or_create(owner=self._owner, name=payee_name)
            instance.payee = payee_obj
        else:
            instance.payee = None
        instance.project = self._resolve_project()
        category_choice = (self.cleaned_data.get("category_choice") or "").strip()
        category_name = (self.cleaned_data.get("category_name") or "").strip()
        if category_choice and category_choice not in {"__new__"}:
            try:
                instance.category = self._category_qs.get(id=category_choice)
            except Exception:
                instance.category = None
        elif category_choice == "__new__" and category_name and self._owner is not None:
            category_obj = create_quick_category(self._owner, category_name)
            instance.category = category_obj
        else:
            instance.category = None
        if commit:
            instance.save()
            self.save_m2m()
        return instance
