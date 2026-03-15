from django import forms

from .models import ArchibaldEmailFlagRule, ArchibaldMailboxConfig


class ArchibaldMailboxConfigForm(forms.ModelForm):
    CORE_FIELDS = (
        "inbox_address",
        "timezone_name",
        "is_enabled",
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
        "notification_include_reminders",
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
            "notification_include_reminders",
            "notification_include_planner",
            "notification_include_subscriptions",
            "notification_include_routines",
        )
        widgets = {
            "auto_reply_signature": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "auto_reply_signature": "Firma opzionale aggiunta in fondo alla risposta.",
            "allowed_sender_regex": (
                "Opzionale: rispondi solo ai mittenti che matchano questa regex. "
                "Se ARCHIBALD_MAIL_ALLOWED_SENDERS e configurato in .env, la whitelist ha priorita."
            ),
            "max_inbox_emails_per_run": "Limite email processate per singolo run.",
            "notification_recipient": "Email destinatario riepilogo ogni 24 ore (configurabile da pannello).",
        }


class SendTestEmailForm(forms.Form):
    recipient = forms.EmailField(required=False, label="Destinatario test")
    subject = forms.CharField(max_length=180, label="Oggetto")
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), label="Messaggio")


class ArchibaldEmailFlagRuleForm(forms.ModelForm):
    class Meta:
        model = ArchibaldEmailFlagRule
        fields = ("label", "flag_token", "action_key", "is_active", "notes")
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "flag_token": "Token senza parentesi: es. MEMORY, TODO, TRANSACTION, TX, ARCHI.",
            "action_key": "Categoria/azione da applicare quando il flag e presente nell'oggetto.",
            "is_active": "Se disattivato il flag non viene considerato nel processamento inbox.",
        }

    def clean_flag_token(self):
        token = (self.cleaned_data.get("flag_token") or "").strip().upper()
        token = token.strip("[]# ")
        if token.startswith("ACTION:"):
            token = token.split(":", 1)[1].strip()
        token = token.replace(" ", "_")
        if not ArchibaldEmailFlagRule.is_valid_token(token):
            raise forms.ValidationError("Formato flag non valido. Usa lettere, numeri, underscore o trattino.")
        return token
