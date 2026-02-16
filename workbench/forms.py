from django import forms

from .models import WorkbenchItem


class WorkbenchItemForm(forms.ModelForm):
    class Meta:
        model = WorkbenchItem
        fields = ("title", "kind", "status", "note")
