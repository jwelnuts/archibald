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
    IMAP_FIELDS = (
        "imap_host",
        "imap_port",
        "imap_use_ssl",
        "imap_username",
        "imap_password",
        "imap_mailbox",
    )
    SMTP_FIELDS = (
        "smtp_host",
        "smtp_port",
        "smtp_use_tls",
        "smtp_use_ssl",
        "smtp_username",
        "smtp_password",
        "smtp_from_email",
        "smtp_reply_to",
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
            "imap_host",
            "imap_port",
            "imap_use_ssl",
            "imap_username",
            "imap_password",
            "imap_mailbox",
            "smtp_host",
            "smtp_port",
            "smtp_use_tls",
            "smtp_use_ssl",
            "smtp_username",
            "smtp_password",
            "smtp_from_email",
            "smtp_reply_to",
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
            "imap_password": forms.PasswordInput(render_value=False),
            "smtp_password": forms.PasswordInput(render_value=False),
        }
        help_texts = {
            "auto_reply_signature": "Firma opzionale aggiunta in fondo alla risposta.",
            "allowed_sender_regex": "Opzionale: rispondi solo ai mittenti che matchano questa regex.",
            "max_inbox_emails_per_run": "Limite email processate per singolo run.",
            "imap_password": "Lascia vuoto per mantenere la password già salvata.",
            "smtp_password": "Lascia vuoto per mantenere la password già salvata.",
            "notification_recipient": "Se vuoto usa email utente, altrimenti inbox address.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_imap_password = (self.instance.imap_password or "") if self.instance.pk else ""
        self._original_smtp_password = (self.instance.smtp_password or "") if self.instance.pk else ""

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("smtp_use_ssl") and cleaned.get("smtp_use_tls"):
            self.add_error("smtp_use_tls", "Con SMTP SSL attivo, disattiva STARTTLS.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)

        if not (self.cleaned_data.get("imap_password") or "").strip():
            instance.imap_password = self._original_imap_password
        if not (self.cleaned_data.get("smtp_password") or "").strip():
            instance.smtp_password = self._original_smtp_password

        if commit:
            instance.save()
        return instance


class SendTestEmailForm(forms.Form):
    recipient = forms.EmailField(required=False, label="Destinatario test")
    subject = forms.CharField(max_length=180, label="Oggetto")
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), label="Messaggio")
