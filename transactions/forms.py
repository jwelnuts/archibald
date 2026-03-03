from django import forms
from django.core.exceptions import ValidationError

from contacts.models import Contact
from contacts.services import ensure_legacy_records_for_contact, upsert_contact
from core.models import Payee
from income.models import IncomeSource
from projects.models import Category, Project
from subscriptions.models import Currency

from .models import Transaction


class TransactionFilterForm(forms.Form):
    tx_type = forms.ChoiceField(label="Tipo", required=False)
    date_from = forms.DateField(
        label="Dal",
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"class": "date-field", "placeholder": "YYYY-MM-DD"}),
    )
    date_to = forms.DateField(
        label="Al",
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"class": "date-field", "placeholder": "YYYY-MM-DD"}),
    )
    query = forms.CharField(label="Cerca", required=False, max_length=120)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tx_type"].choices = [
            ("", "Tutti i tipi"),
            *Transaction.Type.choices,
        ]
        self.fields["tx_type"].widget.attrs.update({"id": "id_filter_tx_type"})
        self.fields["date_from"].widget.attrs.update({"id": "id_filter_date_from"})
        self.fields["date_to"].widget.attrs.update({"id": "id_filter_date_to"})
        self.fields["query"].widget.attrs.update({"id": "id_filter_query", "placeholder": "Cerca per nota, conto, progetto..."})

    def clean(self):
        cleaned = super().clean()
        date_from = cleaned.get("date_from")
        date_to = cleaned.get("date_to")
        if date_from and date_to and date_from > date_to:
            self.add_error("date_to", "La data finale deve essere successiva alla data iniziale.")
        return cleaned


class TransactionEntryForm(forms.ModelForm):
    tx_type = forms.ChoiceField(label="Tipo", choices=Transaction.Type.choices)
    payee_name = forms.CharField(label="Beneficiario", max_length=160, required=False)
    source_choice = forms.ChoiceField(label="Fonte del denaro", required=False)
    source_name = forms.CharField(label="Nuova fonte", max_length=160, required=False)
    project_choice = forms.ChoiceField(label="Progetto", required=False)
    project_name = forms.CharField(label="Nuovo progetto", max_length=120, required=False)
    category_choice = forms.ChoiceField(label="Categoria", required=False)
    category_name = forms.CharField(label="Nuova categoria", max_length=80, required=False)

    _ALLOWED_ATTACHMENT_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".bmp",
        ".tif",
        ".tiff",
        ".pdf",
    }
    _MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024

    class Meta:
        model = Transaction
        fields = (
            "tx_type",
            "date",
            "amount",
            "currency",
            "account",
            "project",
            "category",
            "note",
            "attachment",
            "tags",
        )
        widgets = {
            "date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "note": forms.Textarea(attrs={"rows": 3}),
            "attachment": forms.ClearableFileInput(attrs={"accept": "image/*,.pdf"}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        requested_type = (kwargs.pop("tx_type", "") or "").strip()
        super().__init__(*args, **kwargs)
        self._owner = owner

        if owner is not None:
            self.fields["account"].queryset = self.fields["account"].queryset.filter(owner=owner)
            self.fields["project"].queryset = self.fields["project"].queryset.filter(owner=owner)
            self.fields["category"].queryset = self.fields["category"].queryset.filter(owner=owner)
            self.fields["tags"].queryset = self.fields["tags"].queryset.filter(owner=owner)

        currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
        self.fields["currency"].queryset = Currency.objects.filter(code="EUR")
        self.fields["currency"].initial = currency

        source_choices = [("", "Seleziona..."), ("__new__", "Nuova fonte...")]
        if owner is not None:
            sources = IncomeSource.objects.filter(owner=owner).order_by("name")
            source_choices += [(str(source.id), source.name) for source in sources]
        self.fields["source_choice"].choices = source_choices

        project_choices = [("", "Nessuno"), ("__new__", "+Nuovo")]
        category_choices = [("", "Nessuna"), ("__new__", "+Nuovo")]

        if owner is not None:
            projects = self.fields["project"].queryset.order_by("name")
            categories = self.fields["category"].queryset.order_by("name")
            project_choices += [(str(project.id), project.name) for project in projects]
            category_choices += [(str(category.id), category.name) for category in categories]

        self.fields["project_choice"].choices = project_choices
        self.fields["category_choice"].choices = category_choices

        inferred_type = requested_type
        if not inferred_type and self.instance and self.instance.pk:
            inferred_type = self.instance.tx_type
        if inferred_type in {choice[0] for choice in Transaction.Type.choices}:
            self.fields["tx_type"].initial = inferred_type

        if self.instance and self.instance.pk and self.instance.income_source:
            self.fields["source_choice"].initial = str(self.instance.income_source.id)
        if self.instance and self.instance.pk and self.instance.payee:
            self.fields["payee_name"].initial = self.instance.payee.name

        if self.instance and self.instance.pk:
            if self.instance.project:
                self.fields["project_choice"].initial = str(self.instance.project.id)
            if self.instance.category:
                self.fields["category_choice"].initial = str(self.instance.category.id)
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

        tx_type = cleaned.get("tx_type")
        source_choice = (cleaned.get("source_choice") or "").strip()
        source_name = (cleaned.get("source_name") or "").strip()
        project_choice = (cleaned.get("project_choice") or "").strip()
        project_name = (cleaned.get("project_name") or "").strip()
        category_choice = (cleaned.get("category_choice") or "").strip()
        category_name = (cleaned.get("category_name") or "").strip()

        if tx_type == Transaction.Type.INCOME and source_choice == "__new__" and not source_name:
            self.add_error("source_name", "Inserisci il nome della nuova fonte.")

        if project_choice == "__new__" and not project_name:
            self.add_error("project_name", "Inserisci il nome del nuovo progetto.")
        elif project_choice and project_choice != "__new__":
            if not self._is_valid_selection_id(project_choice):
                self.add_error("project_choice", "Progetto non valido.")
            elif self._owner is not None and not Project.objects.filter(owner=self._owner, id=project_choice).exists():
                self.add_error("project_choice", "Progetto non trovato.")

        if category_choice == "__new__" and not category_name:
            self.add_error("category_name", "Inserisci il nome della nuova categoria.")
        elif category_choice and category_choice != "__new__":
            if not self._is_valid_selection_id(category_choice):
                self.add_error("category_choice", "Categoria non valida.")
            elif self._owner is not None and not Category.objects.filter(owner=self._owner, id=category_choice).exists():
                self.add_error("category_choice", "Categoria non trovata.")

        return cleaned

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")
        if not attachment:
            return attachment

        ext = f".{attachment.name.rsplit('.', 1)[-1].lower()}" if "." in attachment.name else ""
        if ext not in self._ALLOWED_ATTACHMENT_EXTENSIONS:
            raise ValidationError("Formato file non supportato. Carica un'immagine o un PDF.")

        content_type = (getattr(attachment, "content_type", "") or "").lower()
        if content_type and not (content_type.startswith("image/") or content_type == "application/pdf"):
            raise ValidationError("Tipo di file non valido. Sono ammessi solo immagini o PDF.")

        if attachment.size > self._MAX_ATTACHMENT_SIZE_BYTES:
            raise ValidationError("File troppo grande. Dimensione massima: 10 MB.")

        return attachment

    def _build_placeholder_name(self, model_cls, raw_value, max_length):
        base_raw = (raw_value or "").strip()
        base_name = "Nuovo"
        if base_raw:
            base_name = f"Nuovo - {base_raw}"

        base_name = base_name[:max_length]
        candidate = base_name
        index = 2

        while model_cls.objects.filter(owner=self._owner, name=candidate).exists():
            suffix = f" ({index})"
            truncated_base = base_name[: max(1, max_length - len(suffix))]
            candidate = f"{truncated_base}{suffix}"
            index += 1

        return candidate

    def _resolve_project(self):
        choice = (self.cleaned_data.get("project_choice") or "").strip()
        new_name = (self.cleaned_data.get("project_name") or "").strip()

        if not choice:
            return None
        if self._owner is None:
            return None

        if choice == "__new__":
            placeholder_name = self._build_placeholder_name(Project, new_name, 120)
            return Project.objects.create(
                owner=self._owner,
                name=placeholder_name,
                description="Creato da inserimento rapido transazione. Da completare nel modulo Projects.",
                is_archived=False,
            )

        return Project.objects.filter(owner=self._owner, id=choice).first()

    def _resolve_category(self):
        choice = (self.cleaned_data.get("category_choice") or "").strip()
        new_name = (self.cleaned_data.get("category_name") or "").strip()

        if not choice:
            return None
        if self._owner is None:
            return None

        if choice == "__new__":
            placeholder_name = self._build_placeholder_name(Category, new_name, 80)
            return Category.objects.create(
                owner=self._owner,
                name=placeholder_name,
            )

        return Category.objects.filter(owner=self._owner, id=choice).first()

    def _set_income_source(self, instance):
        source_choice = (self.cleaned_data.get("source_choice") or "").strip()
        source_name = (self.cleaned_data.get("source_name") or "").strip()
        instance.income_source = None

        if source_choice and source_choice != "__new__" and self._owner is not None:
            try:
                source_obj = IncomeSource.objects.get(id=source_choice, owner=self._owner)
            except IncomeSource.DoesNotExist:
                return
            instance.income_source = source_obj
            contact = upsert_contact(
                self._owner,
                source_obj.name,
                entity_type=Contact.EntityType.HYBRID,
                website=source_obj.website,
                roles={"role_income_source", "role_customer"},
            )
            ensure_legacy_records_for_contact(contact)
            return

        if source_name and self._owner is not None:
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

    def _set_payee(self, instance):
        payee_name = (self.cleaned_data.get("payee_name") or "").strip()
        instance.payee = None

        if not payee_name or self._owner is None:
            return

        payee, _ = Payee.objects.get_or_create(owner=self._owner, name=payee_name)
        instance.payee = payee
        contact = upsert_contact(
            self._owner,
            payee_name,
            entity_type=Contact.EntityType.HYBRID,
            roles={"role_payee", "role_supplier"},
        )
        ensure_legacy_records_for_contact(contact)

    def save(self, commit=True):
        instance = super().save(commit=False)
        tx_type = self.cleaned_data.get("tx_type")
        instance.tx_type = tx_type
        if self._owner is not None and not instance.owner_id:
            instance.owner = self._owner

        instance.project = self._resolve_project()
        instance.category = self._resolve_category()

        if tx_type == Transaction.Type.INCOME:
            instance.payee = None
            self._set_income_source(instance)
        elif tx_type == Transaction.Type.EXPENSE:
            instance.income_source = None
            self._set_payee(instance)
        else:
            instance.payee = None
            instance.income_source = None

        if commit:
            instance.save()
            self.save_m2m()

        return instance
