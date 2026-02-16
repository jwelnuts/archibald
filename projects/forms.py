from django import forms

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
        if owner is not None:
            categories = Category.objects.filter(owner=owner).order_by("name")
            self._category_qs = categories
            customers = Customer.objects.filter(owner=owner).order_by("name")
            self._customer_qs = customers
            self.fields["customer_choice"].choices = [("", "Seleziona...")] + [
                (str(c.id), c.name) for c in customers
            ] + [("__new__", "+ Nuovo Cliente")]
            self.fields["category_choice"].choices = [("", "Seleziona...")] + [
                (str(c.id), c.name) for c in categories
            ] + [("__new__", "+ Nuova Categoria")]
        if self.instance and self.instance.pk and self.instance.customer:
            self.fields["customer_choice"].initial = str(self.instance.customer.id)
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
                instance.customer = self._customer_qs.get(id=customer_choice)
            except Exception:
                instance.customer = None
        elif customer_choice == "__new__" and customer_name and self._owner is not None:
            customer, _ = Customer.objects.get_or_create(owner=self._owner, name=customer_name)
            instance.customer = customer
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
