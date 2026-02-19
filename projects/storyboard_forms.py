from django import forms

from planner.models import PlannerItem
from todo.models import Task


class StoryboardTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("title", "due_date", "status", "priority", "note")
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date", "placeholder": "YYYY-MM-DD"}),
            "note": forms.Textarea(attrs={"rows": 3, "placeholder": "Dettagli task..."}),
        }


class StoryboardPlannerForm(forms.ModelForm):
    class Meta:
        model = PlannerItem
        fields = ("title", "due_date", "status", "note")
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date", "placeholder": "YYYY-MM-DD"}),
            "note": forms.Textarea(attrs={"rows": 3, "placeholder": "Note planner..."}),
        }
