from django import forms

from .models import SocialChannel, SocialPost


class SocialChannelForm(forms.ModelForm):
    class Meta:
        model = SocialChannel
        fields = ["platform", "name", "handle", "url", "is_active", "notes"]
        widgets = {
            "platform": forms.Select(attrs={"class": "uk-select"}),
            "name": forms.TextInput(attrs={"class": "uk-input", "placeholder": "Nome canale"}),
            "handle": forms.TextInput(attrs={"class": "uk-input", "placeholder": "@username"}),
            "url": forms.URLInput(attrs={"class": "uk-input", "placeholder": "https://..."}),
            "notes": forms.Textarea(attrs={"class": "uk-textarea", "rows": 3}),
        }

    def __init__(self, *args, owner=None, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner = owner
        self._project = project

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self._owner:
            instance.owner = self._owner
        if self._project:
            instance.project = self._project
        if commit:
            instance.save()
        return instance


class SocialPostForm(forms.ModelForm):
    class Meta:
        model = SocialPost
        fields = ["channel", "status", "content", "scheduled_at", "media_file", "notes"]
        widgets = {
            "channel": forms.Select(attrs={"class": "uk-select"}),
            "status": forms.Select(attrs={"class": "uk-select"}),
            "content": forms.Textarea(attrs={"class": "uk-textarea", "rows": 5, "placeholder": "Contenuto del post..."}),
            "scheduled_at": forms.DateTimeInput(
                attrs={"class": "uk-input", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "media_file": forms.ClearableFileInput(attrs={"class": "uk-input"}),
            "notes": forms.Textarea(attrs={"class": "uk-textarea", "rows": 2}),
        }

    def __init__(self, *args, owner=None, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner = owner
        self._project = project
        if project and owner:
            self.fields["channel"].queryset = (
                SocialChannel.objects.filter(owner=owner, project=project, is_active=True)
                .order_by("platform", "name")
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self._owner:
            instance.owner = self._owner
        if self._project:
            instance.project = self._project
        if commit:
            instance.save()
        return instance
