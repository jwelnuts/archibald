from django import forms

from .models import ProjectNote


class ProjectNoteForm(forms.ModelForm):
    class Meta:
        model = ProjectNote
        fields = ("content", "attachment")
        widgets = {
            "content": forms.Textarea(attrs={"rows": 3, "placeholder": "Scrivi un appunto..."}),
        }
