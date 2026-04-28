from django import forms
from django.forms import inlineformset_factory

from contacts.models import ContactDeliveryAddress
from core.models import Payee
from projects.models import Category, Project
from projects.quick_create import create_quick_category, create_quick_project
from finance_hub.models import Currency

from .models import Currency, Tag, Account, Subscription, SubscriptionOccurrence, Invoice, PaymentMethod, Quote, QuoteLine, ShippingMethod, VatCode, WorkOrder


def _ensure_default_quote_catalogs(owner):
    if owner is None:
        return

    payment_defaults = [
        ("Bonifico bancario", ""),
        ("Contanti", ""),
        ("Carta", ""),
        ("PayPal", ""),
    ]
    shipping_defaults = [
        ("Ritiro in sede", ""),
        ("Corriere standard", ""),
        ("Corriere espresso", ""),
        ("Consegna diretta", ""),
    ]

    for name, description in payment_defaults:
        PaymentMethod.objects.get_or_create(
            owner=owner,
            name=name,
            defaults={"description": description, "is_active": True},
        )
    for name, description in shipping_defaults:
        ShippingMethod.objects.get_or_create(
            owner=owner,
            name=name,
            defaults={"description": description, "is_active": True},
        )


class _OwnedFinanceFormMixin:
    def _init_common(self, owner):
        self._owner = owner
        self._project_qs = Project.objects.none()
        if owner is not None:
            if "payment_method" in self.fields or "shipping_method" in self.fields:
                _ensure_default_quote_catalogs(owner)
            if "customer" in self.fields:
                self.fields["customer"].queryset = self.fields["customer"].queryset.filter(owner=owner).order_by("name")
            if "project" in self.fields:
                self.fields["project"].queryset = self.fields["project"].queryset.filter(owner=owner).order_by("name")
                self._project_qs = self.fields["project"].queryset
            if "account" in self.fields:
                self.fields["account"].queryset = self.fields["account"].queryset.filter(owner=owner).order_by("name")
            if "quote" in self.fields:
                self.fields["quote"].queryset = self.fields["quote"].queryset.filter(owner=owner).order_by("-issue_date", "-id")
            if "vat_code" in self.fields:
                self.fields["vat_code"].queryset = (
                    self.fields["vat_code"].queryset.filter(owner=owner, is_active=True).order_by("rate", "code")
                )
            if "payment_method" in self.fields:
                self.fields["payment_method"].queryset = (
                    self.fields["payment_method"].queryset.filter(owner=owner, is_active=True).order_by("name", "id")
                )
            if "shipping_method" in self.fields:
                self.fields["shipping_method"].queryset = (
                    self.fields["shipping_method"].queryset.filter(owner=owner, is_active=True).order_by("name", "id")
                )
            if "delivery_address" in self.fields:
                self.fields["delivery_address"].queryset = (
                    self.fields["delivery_address"]
                    .queryset.filter(owner=owner, is_active=True)
                    .select_related("contact")
                    .order_by("contact__display_name", "label", "id")
                )

        if "currency" in self.fields:
            currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
            self.fields["currency"].queryset = Currency.objects.filter(code="EUR")
            self.fields["currency"].initial = currency

        if "project_choice" in self.fields:
            self.fields["project_choice"].choices = [("", "Nessuno"), ("__new__", "+Nuovo")] + [
                (str(project.id), project.name) for project in self._project_qs
            ]
            if self.instance and self.instance.pk and getattr(self.instance, "project_id", None):
                self.fields["project_choice"].initial = str(self.instance.project_id)
            else:
                initial_project = self.initial.get("project")
                if initial_project:
                    self.fields["project_choice"].initial = str(getattr(initial_project, "id", initial_project))

    def _validate_project_choice(self, cleaned):
        choice = (cleaned.get("project_choice") or "").strip()
        project_name = (cleaned.get("project_name") or "").strip()

        if choice == "__new__" and not project_name:
            self.add_error("project_name", "Inserisci il nome del nuovo progetto.")
        elif choice and choice != "__new__":
            if not choice.isdigit():
                self.add_error("project_choice", "Progetto non valido.")
            elif self._owner is not None and not self._project_qs.filter(id=choice).exists():
                self.add_error("project_choice", "Progetto non trovato.")

    def _customer_for_delivery(self):
        customer_field = self.fields.get("customer")
        if customer_field is None:
            return None

        selected_id = ""
        if self.is_bound:
            selected_id = (self.data.get(self.add_prefix("customer")) or "").strip()
        if not selected_id and self.initial.get("customer"):
            selected_id = str(getattr(self.initial.get("customer"), "id", self.initial.get("customer")))
        if not selected_id and self.instance and getattr(self.instance, "customer_id", None):
            selected_id = str(self.instance.customer_id)
        if not selected_id:
            return None
        if not selected_id.isdigit():
            return None
        return customer_field.queryset.filter(id=selected_id).first()

    def _filter_delivery_addresses_for_customer(self):
        if "delivery_address" not in self.fields:
            return
        owner = getattr(self, "_owner", None)
        if owner is None:
            return

        field = self.fields["delivery_address"]
        base_qs = ContactDeliveryAddress.objects.filter(owner=owner, is_active=True).select_related("contact")
        customer = self._customer_for_delivery()
        if customer and customer.name:
            customer_qs = base_qs.filter(contact__display_name__iexact=customer.name)
            if customer_qs.exists():
                base_qs = customer_qs
        if self.instance and getattr(self.instance, "delivery_address_id", None):
            base_qs = (base_qs | ContactDeliveryAddress.objects.filter(id=self.instance.delivery_address_id)).distinct()
        field.queryset = base_qs.order_by("contact__display_name", "label", "id")
        field.empty_label = "Nessuna destinazione merce"

    def _resolve_project(self):
        choice = (self.cleaned_data.get("project_choice") or "").strip()
        project_name = (self.cleaned_data.get("project_name") or "").strip()

        if not choice or self._owner is None:
            return None
        if choice == "__new__":
            return create_quick_project(self._owner, project_name)
        return self._project_qs.filter(id=choice).first()


def _append_widget_class(widget, class_name):
    current = widget.attrs.get("class", "")
    current_parts = [part for part in current.split() if part]
    if class_name not in current_parts:
        current_parts.append(class_name)
    widget.attrs["class"] = " ".join(current_parts)


def _apply_uikit_input_styles(form):
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.Textarea):
            _append_widget_class(widget, "uk-textarea")
        elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
            _append_widget_class(widget, "uk-select")
        elif isinstance(widget, forms.CheckboxInput):
            _append_widget_class(widget, "uk-checkbox")
        else:
            _append_widget_class(widget, "uk-input")


class QuoteForm(_OwnedFinanceFormMixin, forms.ModelForm):
    project_choice = forms.ChoiceField(label="Progetto", required=False)
    project_name = forms.CharField(label="Nuovo progetto", max_length=120, required=False)

    class Meta:
        model = Quote
        fields = (
            "code",
            "title",
            "customer",
            "delivery_address",
            "payment_method",
            "shipping_method",
            "project",
            "issue_date",
            "valid_until",
            "currency",
            "vat_code",
            "amount_net",
            "status",
            "note",
        )
        widgets = {
            "issue_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "valid_until": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        self._init_common(owner)
        _apply_uikit_input_styles(self)
        self.fields["vat_code"].required = False
        self.fields["vat_code"].empty_label = "Nessuna IVA / Esente (0%)"
        self.fields["payment_method"].required = False
        self.fields["payment_method"].empty_label = "Nessuna modalita di pagamento"
        self.fields["shipping_method"].required = False
        self.fields["shipping_method"].empty_label = "Nessuna modalita di spedizione"
        self.fields["delivery_address"].required = False
        self._filter_delivery_addresses_for_customer()

    def clean(self):
        cleaned = super().clean()
        self._validate_project_choice(cleaned)
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.project = self._resolve_project()
        if commit:
            instance.save()
        return instance


class InvoiceForm(_OwnedFinanceFormMixin, forms.ModelForm):
    project_choice = forms.ChoiceField(label="Progetto", required=False)
    project_name = forms.CharField(label="Nuovo progetto", max_length=120, required=False)

    class Meta:
        model = Invoice
        fields = (
            "code",
            "title",
            "quote",
            "customer",
            "project",
            "account",
            "issue_date",
            "due_date",
            "paid_date",
            "currency",
            "amount_net",
            "tax_amount",
            "status",
            "note",
        )
        widgets = {
            "issue_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "due_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "paid_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        self._init_common(owner)

    def clean(self):
        cleaned = super().clean()
        self._validate_project_choice(cleaned)
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.project = self._resolve_project()
        if commit:
            instance.save()
        return instance


class WorkOrderForm(_OwnedFinanceFormMixin, forms.ModelForm):
    project_choice = forms.ChoiceField(label="Progetto", required=False)
    project_name = forms.CharField(label="Nuovo progetto", max_length=120, required=False)

    class Meta:
        model = WorkOrder
        fields = (
            "code",
            "title",
            "customer",
            "project",
            "account",
            "start_date",
            "end_date",
            "currency",
            "estimated_amount",
            "final_amount",
            "is_billable",
            "status",
            "note",
        )
        widgets = {
            "start_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
            "end_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        self._init_common(owner)

    def clean(self):
        cleaned = super().clean()
        self._validate_project_choice(cleaned)
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.project = self._resolve_project()
        if commit:
            instance.save()
        return instance


class PublicQuoteConfirmationForm(forms.Form):
    signer_name = forms.CharField(label="Nome e cognome firmatario", max_length=180)
    customer_name = forms.CharField(label="Ragione sociale / Nominativo", max_length=160)
    customer_email = forms.EmailField(label="Email", required=False)
    customer_phone = forms.CharField(label="Telefono", max_length=40, required=False)
    customer_notes = forms.CharField(
        label="Note anagrafiche",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    delivery_label = forms.CharField(label="Etichetta indirizzo", max_length=120, required=False)
    delivery_recipient_name = forms.CharField(label="Destinatario", max_length=160, required=False)
    delivery_line1 = forms.CharField(label="Indirizzo", max_length=180, required=False)
    delivery_line2 = forms.CharField(label="Indirizzo (linea 2)", max_length=180, required=False)
    delivery_postal_code = forms.CharField(label="CAP", max_length=20, required=False)
    delivery_city = forms.CharField(label="Citta", max_length=120, required=False)
    delivery_province = forms.CharField(label="Provincia", max_length=120, required=False)
    delivery_country = forms.CharField(label="Nazione", max_length=120, required=False, initial="Italia")
    reject_reason = forms.CharField(
        label="Motivazione rifiuto",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, decision="", **kwargs):
        self.current_decision = (decision or "").strip().lower()
        super().__init__(*args, **kwargs)
        _apply_uikit_input_styles(self)

    def clean(self):
        cleaned = super().clean()
        decision = self.current_decision
        if not decision and (self.data.get("accept_quote") == "on"):
            decision = "approve"
        self.current_decision = decision

        if decision not in {"approve", "reject"}:
            raise forms.ValidationError("Seleziona se confermare o rifiutare il preventivo.")
        if decision == "reject" and not (cleaned.get("reject_reason") or "").strip():
            self.add_error("reject_reason", "Inserisci la motivazione del rifiuto.")

        address_fields = (
            "delivery_label",
            "delivery_recipient_name",
            "delivery_line1",
            "delivery_line2",
            "delivery_postal_code",
            "delivery_city",
            "delivery_province",
            "delivery_country",
        )
        has_delivery_address = any((cleaned.get(field) or "").strip() for field in address_fields)
        cleaned["has_delivery_address"] = has_delivery_address

        if has_delivery_address:
            if not (cleaned.get("delivery_line1") or "").strip():
                self.add_error("delivery_line1", "Inserisci l'indirizzo di consegna.")
            if not (cleaned.get("delivery_city") or "").strip():
                self.add_error("delivery_city", "Inserisci la citta di consegna.")
            if not (cleaned.get("delivery_label") or "").strip():
                cleaned["delivery_label"] = "Destinazione principale"
            if not (cleaned.get("delivery_country") or "").strip():
                cleaned["delivery_country"] = "Italia"

        return cleaned


class QuoteLineForm(forms.ModelForm):
    class Meta:
        model = QuoteLine
        fields = (
            "row_order",
            "code",
            "description",
            "net_amount",
            "quantity",
            "discount",
        )
        widgets = {
            "row_order": forms.HiddenInput(),
            "description": forms.TextInput(attrs={"placeholder": "Descrizione articolo"}),
            "discount": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}),
            "quantity": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "net_amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["row_order"].required = False
        _apply_uikit_input_styles(self)


class VatCodeForm(forms.ModelForm):
    class Meta:
        model = VatCode
        fields = ("code", "description", "rate", "is_active")
        widgets = {
            "rate": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_uikit_input_styles(self)


QuoteLineFormSet = inlineformset_factory(
    Quote,
    QuoteLine,
    form=QuoteLineForm,
    extra=1,
    can_delete=True,
)


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
