from django import forms

from .models import ArchibaldMailboxConfig


class ArchibaldMailboxConfigForm(forms.ModelForm):
    CORE_FIELDS = (
        "inbox_address",
        "timezone_name",
        "is_enabled",
        "auto_reply_enabled",
        "auto_reply_subject_prefix",
        "auto_reply_signature",
        "allowed_sender_regex",
        "max_inbox_emails_per_run",
    )
    NOTIFICATION_FIELDS = (
        "notifications_enabled",
        "notification_recipient",
        "notification_hour",
        "notification_minute",
        "notification_days_ahead",
        "notification_include_tasks",
        "notification_include_planner",
        "notification_include_subscriptions",
        "notification_include_routines",
    )

    class Meta:
        model = ArchibaldMailboxConfig
        fields = (
            "inbox_address",
            "timezone_name",
            "is_enabled",
            "auto_reply_enabled",
            "auto_reply_subject_prefix",
            "auto_reply_signature",
            "allowed_sender_regex",
            "max_inbox_emails_per_run",
            "notifications_enabled",
            "notification_recipient",
            "notification_hour",
            "notification_minute",
            "notification_days_ahead",
            "notification_include_tasks",
            "notification_include_planner",
            "notification_include_subscriptions",
            "notification_include_routines",
        )
        widgets = {
            "auto_reply_signature": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "auto_reply_signature": "Firma opzionale aggiunta in fondo alla risposta.",
            "allowed_sender_regex": "Opzionale: rispondi solo ai mittenti che matchano questa regex.",
            "max_inbox_emails_per_run": "Limite email processate per singolo run.",
            "notification_recipient": "Se vuoto usa email utente, altrimenti inbox address.",
        }


class SendTestEmailForm(forms.Form):
    recipient = forms.EmailField(required=False, label="Destinatario test")
    subject = forms.CharField(max_length=180, label="Oggetto")
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), label="Messaggio")
