from django import forms

from .models import LabEntry


class LabEntryForm(forms.ModelForm):
    class Meta:
        model = LabEntry
        fields = (
            "title",
            "area",
            "status",
            "prompt",
            "result",
            "notes",
            "next_step",
            "resource_url",
        )
