from django import forms


class ArchibaldPromptForm(forms.Form):
    prompt = forms.CharField(
        label="Richiesta",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Chiedi ad Archibald..."}),
    )
