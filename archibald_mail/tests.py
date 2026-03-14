from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from .forms import ArchibaldMailboxConfigForm
from .models import ArchibaldEmailMessage, ArchibaldMailboxConfig
from .services import parse_inbound_email, process_inbox_for_config, send_notification_for_config


class ArchibaldMailFormTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="mail_user",
            password="pwd12345",
            email="owner@example.com",
        )

    def test_form_excludes_server_login_fields_and_saves_user_controls(self):
        config = ArchibaldMailboxConfig.objects.create(
            owner=self.user,
            inbox_address="archibald@miorganizzo.ovh",
            timezone_name="Europe/Rome",
            auto_reply_subject_prefix="Re:",
            imap_host="imap.example.com",
            imap_port=993,
            imap_username="archibald@miorganizzo.ovh",
            imap_password="imap-secret",
            imap_mailbox="INBOX",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="archibald@miorganizzo.ovh",
            smtp_password="smtp-secret",
            smtp_from_email="archibald@miorganizzo.ovh",
            notification_hour=8,
            notification_minute=30,
            notification_days_ahead=2,
            max_inbox_emails_per_run=10,
        )

        initial_form = ArchibaldMailboxConfigForm(instance=config)
        self.assertNotIn("imap_host", initial_form.fields)
        self.assertNotIn("imap_username", initial_form.fields)
        self.assertNotIn("imap_password", initial_form.fields)
        self.assertNotIn("smtp_host", initial_form.fields)
        self.assertNotIn("smtp_username", initial_form.fields)
        self.assertNotIn("smtp_password", initial_form.fields)

        form = ArchibaldMailboxConfigForm(
            data={
                "inbox_address": config.inbox_address,
                "timezone_name": config.timezone_name,
                "is_enabled": "on",
                "auto_reply_enabled": "on",
                "auto_reply_subject_prefix": "Re:",
                "auto_reply_signature": "",
                "allowed_sender_regex": "",
                "max_inbox_emails_per_run": "12",
                "notifications_enabled": "on",
                "notification_recipient": "",
                "notification_hour": "9",
                "notification_minute": "15",
                "notification_days_ahead": "3",
                "notification_include_tasks": "on",
                "notification_include_planner": "on",
                "notification_include_subscriptions": "on",
                "notification_include_routines": "on",
            },
            instance=config,
        )
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()

        self.assertEqual(saved.max_inbox_emails_per_run, 12)
        self.assertEqual(saved.notification_hour, 9)
        self.assertEqual(saved.notification_minute, 15)
        self.assertEqual(saved.notification_days_ahead, 3)
        self.assertEqual(saved.imap_host, "imap.example.com")
        self.assertEqual(saved.imap_username, "archibald@miorganizzo.ovh")
        self.assertEqual(saved.imap_password, "imap-secret")
        self.assertEqual(saved.smtp_host, "smtp.example.com")
        self.assertEqual(saved.smtp_username, "archibald@miorganizzo.ovh")
        self.assertEqual(saved.smtp_password, "smtp-secret")


class ArchibaldMailServicesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="service_user",
            password="pwd12345",
            email="owner@example.com",
        )
        self.config = ArchibaldMailboxConfig.objects.create(
            owner=self.user,
            inbox_address="archibald@miorganizzo.ovh",
            timezone_name="Europe/Rome",
            is_enabled=False,
            auto_reply_enabled=True,
            imap_host="imap.example.com",
            imap_port=993,
            imap_username="archibald@miorganizzo.ovh",
            imap_password="imap-secret",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="archibald@miorganizzo.ovh",
            smtp_password="smtp-secret",
            smtp_from_email="archibald@miorganizzo.ovh",
            notifications_enabled=True,
            notification_hour=8,
            notification_minute=30,
            notification_days_ahead=2,
            max_inbox_emails_per_run=10,
        )

    def test_process_inbox_returns_disabled_if_not_enabled(self):
        result = process_inbox_for_config(self.config)
        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["fetched"], 0)

    @patch("archibald_mail.services.send_email_via_smtp")
    @patch("archibald_mail.services._openai_notification_body", return_value="Reminder body")
    def test_send_notification_force_creates_log(self, _mock_ai, mock_smtp):
        result = send_notification_for_config(self.config, force=True, only_due=False)
        self.assertTrue(result["sent"])
        self.assertEqual(result["status"], "sent")
        self.assertTrue(mock_smtp.called)

        log = ArchibaldEmailMessage.objects.filter(
            owner=self.user,
            direction=ArchibaldEmailMessage.Direction.NOTIFICATION,
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, ArchibaldEmailMessage.Status.SENT)

    def test_send_notification_skips_when_empty_and_not_force(self):
        result = send_notification_for_config(self.config, force=False, only_due=False)
        self.assertFalse(result["sent"])
        self.assertEqual(result["status"], "nothing_to_send")

    def test_parse_inbound_email(self):
        raw = (
            "From: Mario Rossi <mario@example.com>\r\n"
            "To: archibald@miorganizzo.ovh\r\n"
            "Subject: Test rapido\r\n"
            "Message-ID: <abc123@example.com>\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "\r\n"
            "Ciao Archibald"
        ).encode("utf-8")

        parsed = parse_inbound_email(raw)
        self.assertEqual(parsed.sender, "mario@example.com")
        self.assertEqual(parsed.recipient, "archibald@miorganizzo.ovh")
        self.assertEqual(parsed.subject, "Test rapido")
        self.assertIn("Ciao Archibald", parsed.body_text)

    @patch.dict(
        "os.environ",
        {
            "ARCHIBALD_MAIL_IMAP_HOST": "",
            "ARCHIBALD_MAIL_IMAP_USERNAME": "",
            "ARCHIBALD_MAIL_IMAP_PASSWORD": "",
            "IMAP_HOST": "imap.env.test",
            "IMAP_USERNAME": "env-user@example.com",
            "IMAP_PASSWORD": "env-pass",
        },
        clear=False,
    )
    def test_imap_fallback_reads_generic_env_variables(self):
        self.config.imap_host = ""
        self.config.imap_username = ""
        self.config.imap_password = ""
        self.config.save(update_fields=["imap_host", "imap_username", "imap_password", "updated_at"])

        self.assertEqual(self.config.resolved_imap_host(), "imap.env.test")
        self.assertEqual(self.config.resolved_imap_username(), "env-user@example.com")
        self.assertEqual(self.config.resolved_imap_password(), "env-pass")
        self.assertTrue(self.config.is_imap_configured())

    @patch.dict(
        "os.environ",
        {
            "ARCHIBALD_MAIL_SMTP_HOST": "",
            "ARCHIBALD_MAIL_SMTP_USERNAME": "",
            "ARCHIBALD_MAIL_SMTP_PASSWORD": "",
            "ARCHIBALD_MAIL_SMTP_FROM": "",
            "SMTP_HOST": "smtp.env.test",
            "SMTP_USERNAME": "smtp-user@example.com",
            "SMTP_PASSWORD": "smtp-pass",
            "SMTP_FROM": "archibald-env@example.com",
        },
        clear=False,
    )
    def test_smtp_fallback_reads_generic_env_variables(self):
        self.config.smtp_host = ""
        self.config.smtp_username = ""
        self.config.smtp_password = ""
        self.config.smtp_from_email = ""
        self.config.save(update_fields=["smtp_host", "smtp_username", "smtp_password", "smtp_from_email", "updated_at"])

        self.assertEqual(self.config.resolved_smtp_host(), "smtp.env.test")
        self.assertEqual(self.config.resolved_smtp_username(), "smtp-user@example.com")
        self.assertEqual(self.config.resolved_smtp_password(), "smtp-pass")
        self.assertEqual(self.config.smtp_sender(), "archibald-env@example.com")
        self.assertTrue(self.config.is_smtp_configured())
