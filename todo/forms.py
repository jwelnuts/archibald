from django import forms

from .models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("title", "due_date", "status", "priority", "note")
        widgets = {
            "due_date": forms.DateInput(attrs={"class": "date-field", "placeholder": "Seleziona data"}),
        }
