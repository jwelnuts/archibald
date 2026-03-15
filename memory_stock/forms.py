from django import forms

from .models import MemoryStockItem


class MemoryStockItemForm(forms.ModelForm):
    class Meta:
        model = MemoryStockItem
        fields = ("title", "source_url", "note", "is_archived")
        widgets = {
            "note": forms.Textarea(attrs={"rows": 5}),
        }
