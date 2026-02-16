from django import forms

from .models import PlannerItem


class PlannerItemForm(forms.ModelForm):
    class Meta:
        model = PlannerItem
        fields = ("title", "due_date", "amount", "category", "project", "status", "note")
        widgets = {
            "due_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        if owner is not None:
            self.fields["category"].queryset = self.fields["category"].queryset.filter(owner=owner).order_by("name")
            self.fields["project"].queryset = self.fields["project"].queryset.filter(owner=owner).order_by("name")
