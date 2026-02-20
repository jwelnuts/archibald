from django import forms

from contacts.models import Contact
from contacts.services import ensure_legacy_records_for_contact, sync_contacts_from_legacy, upsert_contact

from .models import Category, Customer, Project


class ProjectForm(forms.ModelForm):
    customer_choice = forms.ChoiceField(label="Cliente", required=False)
    customer_name = forms.CharField(label="Cliente", max_length=160, required=False)
    category_choice = forms.ChoiceField(label="Categoria", required=False)
    category_name = forms.CharField(label="Categoria", max_length=80, required=False)

    class Meta:
        model = Project
        fields = ("name", "description", "is_archived")

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        self._owner = owner
        self._contact_qs = Contact.objects.none()
        self._customer_qs = Customer.objects.none()
        self._category_qs = Category.objects.none()
        if owner is not None:
            sync_contacts_from_legacy(owner)
            categories = Category.objects.filter(owner=owner).order_by("name")
            self._category_qs = categories
            contacts = Contact.objects.filter(owner=owner, is_active=True).order_by("display_name")
            self._contact_qs = contacts
            self._customer_qs = Customer.objects.filter(owner=owner).order_by("name")
            self.fields["customer_choice"].choices = [("", "Seleziona...")] + [
                (str(c.id), c.display_name) for c in contacts
            ] + [("__new__", "+ Nuovo Contatto")]
            self.fields["category_choice"].choices = [("", "Seleziona...")] + [
                (str(c.id), c.name) for c in categories
            ] + [("__new__", "+ Nuova Categoria")]
        if self.instance and self.instance.pk and self.instance.customer:
            contact = None
            if owner is not None:
                contact = self._contact_qs.filter(display_name=self.instance.customer.name).first()
                if not contact:
                    contact = upsert_contact(
                        owner,
                        self.instance.customer.name,
                        entity_type=Contact.EntityType.HYBRID,
                        email=self.instance.customer.email,
                        phone=self.instance.customer.phone,
                        notes=self.instance.customer.notes,
                        roles={"role_customer"},
                    )
                    if contact:
                        ensure_legacy_records_for_contact(contact)
            if contact:
                self.fields["customer_choice"].initial = str(contact.id)
                self.fields["customer_name"].initial = contact.display_name
            else:
                self.fields["customer_name"].initial = self.instance.customer.name
        if self.instance and self.instance.pk and self.instance.category:
            self.fields["category_choice"].initial = str(self.instance.category.id)
            self.fields["category_name"].initial = self.instance.category.name

    def save(self, commit=True):
        instance = super().save(commit=False)
        customer_choice = (self.cleaned_data.get("customer_choice") or "").strip()
        customer_name = (self.cleaned_data.get("customer_name") or "").strip()
        if customer_choice and customer_choice not in {"__new__"}:
            try:
                contact = self._contact_qs.get(id=customer_choice)
                if not contact.role_customer:
                    contact.role_customer = True
                    contact.save(update_fields=["role_customer", "updated_at"])
                ensure_legacy_records_for_contact(contact)
                instance.customer = self._customer_qs.get(name=contact.display_name)
            except Exception:
                instance.customer = None
        elif customer_choice == "__new__" and customer_name and self._owner is not None:
            contact = upsert_contact(
                self._owner,
                customer_name,
                entity_type=Contact.EntityType.HYBRID,
                roles={"role_customer"},
            )
            if contact:
                ensure_legacy_records_for_contact(contact)
                try:
                    instance.customer = self._customer_qs.get(name=contact.display_name)
                except Exception:
                    instance.customer = None
            else:
                instance.customer = None
        else:
            instance.customer = None
        category_choice = (self.cleaned_data.get("category_choice") or "").strip()
        category_name = (self.cleaned_data.get("category_name") or "").strip()
        if category_choice and category_choice not in {"__new__"}:
            try:
                instance.category = self._category_qs.get(id=category_choice)
            except Exception:
                instance.category = None
        elif category_choice == "__new__" and category_name and self._owner is not None:
            category, _ = Category.objects.get_or_create(owner=self._owner, name=category_name)
            instance.category = category
        else:
            instance.category = None
        if commit:
            instance.save()
        return instance
