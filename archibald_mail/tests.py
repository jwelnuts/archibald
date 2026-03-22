from unittest.mock import patch
from types import SimpleNamespace
from datetime import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from zoneinfo import ZoneInfo

from agenda.models import WorkLog
from memory_stock.models import MemoryStockItem
from routines.models import Routine, RoutineItem
from .actions import EmailActionOutcome, detect_action_from_subject, execute_action_from_email, execute_action_manually
from .forms import ArchibaldEmailFlagRuleForm, ArchibaldMailboxConfigForm
from .models import ArchibaldEmailFlagRule, ArchibaldEmailMessage, ArchibaldInboundCategory, ArchibaldMailboxConfig
from .services import (
    ParsedInboundEmail,
    _openai_email_reply,
    _sender_allowed,
    parse_inbound_email,
    process_inbox_for_config,
    send_due_worklog_prompts_for_config,
    send_notification_for_config,
)


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
        self.assertNotIn("auto_reply_enabled", initial_form.fields)

        form = ArchibaldMailboxConfigForm(
            data={
                "inbox_address": config.inbox_address,
                "timezone_name": config.timezone_name,
                "is_enabled": "on",
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
                "notification_include_reminders": "on",
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

    def test_flag_rule_form_normalizes_token(self):
        form = ArchibaldEmailFlagRuleForm(
            data={
                "label": "Ricordi",
                "flag_token": "[ memory ]",
                "action_key": "memory_stock.save",
                "is_active": "on",
                "notes": "",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["flag_token"], "MEMORY")


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

    @patch("archibald_mail.services.imaplib.IMAP4_SSL")
    def test_process_inbox_uses_custom_search_criteria(self, mock_imap_cls):
        class FakeMailbox:
            def __init__(self):
                self.searched_criteria = None

            def login(self, *_args, **_kwargs):
                return "OK", [b""]

            def select(self, *_args, **_kwargs):
                return "OK", [b"0"]

            def search(self, _charset, *criteria):
                self.searched_criteria = criteria
                return "OK", [b""]

            def close(self):
                return "OK", [b""]

            def logout(self):
                return "BYE", [b""]

        fake_mailbox = FakeMailbox()
        mock_imap_cls.return_value = fake_mailbox
        self.config.is_enabled = True
        self.config.save(update_fields=["is_enabled", "updated_at"])

        result = process_inbox_for_config(
            self.config,
            force=False,
            search_criteria=("UNSEEN", "SUBJECT", "ARCHI"),
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["fetched"], 0)
        self.assertEqual(fake_mailbox.searched_criteria, ("UNSEEN", "SUBJECT", "ARCHI"))

    @patch.dict(
        "os.environ",
        {"ARCHIBALD_MAIL_ALLOWED_SENDERS": "allowed@example.com, second@example.com"},
        clear=False,
    )
    def test_sender_allowed_uses_env_whitelist_when_configured(self):
        self.config.allowed_sender_regex = r".*@example\.com$"
        self.assertTrue(_sender_allowed(self.config, "allowed@example.com"))
        self.assertFalse(_sender_allowed(self.config, "blocked@example.com"))

    @patch.dict(
        "os.environ",
        {"ARCHIBALD_MAIL_ALLOWED_SENDERS": "allowed@example.com"},
        clear=False,
    )
    @patch("archibald_mail.services.send_email_via_smtp")
    @patch("archibald_mail.services.execute_action_from_email")
    @patch("archibald_mail.services.parse_inbound_email")
    @patch("archibald_mail.services.imaplib.IMAP4_SSL")
    def test_process_inbox_skips_sender_not_in_env_whitelist(
        self,
        mock_imap_cls,
        mock_parse,
        mock_execute_action,
        mock_smtp,
    ):
        class FakeMailbox:
            def login(self, *_args, **_kwargs):
                return "OK", [b""]

            def select(self, *_args, **_kwargs):
                return "OK", [b"1"]

            def search(self, *_args, **_kwargs):
                return "OK", [b"1"]

            def fetch(self, *_args, **_kwargs):
                return "OK", [(b"1", b"raw")]

            def store(self, *_args, **_kwargs):
                return "OK", [b""]

            def close(self):
                return "OK", [b""]

            def logout(self):
                return "BYE", [b""]

        mock_imap_cls.return_value = FakeMailbox()
        mock_parse.return_value = ParsedInboundEmail(
            message_id="<msg-whitelist-1@example.com>",
            in_reply_to="",
            sender="blocked@example.com",
            recipient="archibald@miorganizzo.ovh",
            subject="[ARCHI] Test",
            body_text="Ciao",
            raw_headers="",
        )
        mock_execute_action.return_value = EmailActionOutcome(
            handled=False,
            action_key="archi.reply",
            force_ai_reply=True,
        )

        self.config.is_enabled = True
        self.config.save(update_fields=["is_enabled", "updated_at"])

        result = process_inbox_for_config(self.config)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["replied"], 0)
        self.assertFalse(mock_execute_action.called)
        self.assertFalse(mock_smtp.called)

        inbound = ArchibaldEmailMessage.objects.filter(
            owner=self.user,
            direction=ArchibaldEmailMessage.Direction.INBOUND,
        ).first()
        self.assertIsNotNone(inbound)
        self.assertEqual(inbound.status, ArchibaldEmailMessage.Status.SKIPPED)
        self.assertIn("Mittente non autorizzato", inbound.error_text)

    @patch("archibald_mail.services.send_email_via_smtp")
    @patch("archibald_mail.services._openai_email_reply", return_value="Risposta AI forzata.")
    @patch("archibald_mail.services.execute_action_from_email")
    @patch("archibald_mail.services.parse_inbound_email")
    @patch("archibald_mail.services.imaplib.IMAP4_SSL")
    def test_process_inbox_forced_ai_reply_works_even_when_auto_reply_disabled(
        self,
        mock_imap_cls,
        mock_parse,
        mock_execute_action,
        _mock_openai,
        mock_smtp,
    ):
        class FakeMailbox:
            def login(self, *_args, **_kwargs):
                return "OK", [b""]

            def select(self, *_args, **_kwargs):
                return "OK", [b"1"]

            def search(self, *_args, **_kwargs):
                return "OK", [b"1"]

            def fetch(self, *_args, **_kwargs):
                return "OK", [(b"1", b"raw")]

            def store(self, *_args, **_kwargs):
                return "OK", [b""]

            def close(self):
                return "OK", [b""]

            def logout(self):
                return "BYE", [b""]

        mock_imap_cls.return_value = FakeMailbox()
        mock_parse.return_value = ParsedInboundEmail(
            message_id="<msg-archi-1@example.com>",
            in_reply_to="",
            sender="sender@example.com",
            recipient="archibald@miorganizzo.ovh",
            subject="[ARCHI] Mi aiuti?",
            body_text="Vorrei un consiglio rapido.",
            raw_headers="",
        )
        mock_execute_action.return_value = EmailActionOutcome(
            handled=False,
            action_key="archi.reply",
            force_ai_reply=True,
        )

        self.config.is_enabled = True
        self.config.auto_reply_enabled = False
        self.config.save(update_fields=["is_enabled", "auto_reply_enabled", "updated_at"])

        result = process_inbox_for_config(self.config)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["replied"], 1)
        self.assertTrue(mock_smtp.called)

        inbound = ArchibaldEmailMessage.objects.filter(
            owner=self.user,
            direction=ArchibaldEmailMessage.Direction.INBOUND,
        ).first()
        self.assertIsNotNone(inbound)
        self.assertEqual(inbound.status, ArchibaldEmailMessage.Status.REPLIED)
        self.assertEqual(inbound.selected_action_key, "archi.reply")
        self.assertEqual(inbound.review_status, ArchibaldEmailMessage.ReviewStatus.APPLIED)

    @patch("archibald_mail.services.send_email_via_smtp")
    @patch("archibald_mail.services._openai_email_reply")
    @patch("archibald_mail.services.execute_action_from_email")
    @patch("archibald_mail.services.parse_inbound_email")
    @patch("archibald_mail.services.imaplib.IMAP4_SSL")
    def test_process_inbox_without_flag_never_auto_replies(
        self,
        mock_imap_cls,
        mock_parse,
        mock_execute_action,
        mock_openai_reply,
        mock_smtp,
    ):
        class FakeMailbox:
            def login(self, *_args, **_kwargs):
                return "OK", [b""]

            def select(self, *_args, **_kwargs):
                return "OK", [b"1"]

            def search(self, *_args, **_kwargs):
                return "OK", [b"1"]

            def fetch(self, *_args, **_kwargs):
                return "OK", [(b"1", b"raw")]

            def store(self, *_args, **_kwargs):
                return "OK", [b""]

            def close(self):
                return "OK", [b""]

            def logout(self):
                return "BYE", [b""]

        mock_imap_cls.return_value = FakeMailbox()
        mock_parse.return_value = ParsedInboundEmail(
            message_id="<msg-no-flag-1@example.com>",
            in_reply_to="",
            sender="sender@example.com",
            recipient="archibald@miorganizzo.ovh",
            subject="Conferma ordine 123",
            body_text="Pagamento confermato dal portale.",
            raw_headers="",
        )
        mock_execute_action.return_value = EmailActionOutcome(
            handled=False,
            action_key="",
            force_ai_reply=False,
        )

        self.config.is_enabled = True
        self.config.auto_reply_enabled = True
        self.config.save(update_fields=["is_enabled", "auto_reply_enabled", "updated_at"])

        result = process_inbox_for_config(self.config)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["replied"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertFalse(mock_openai_reply.called)
        self.assertFalse(mock_smtp.called)

        inbound = ArchibaldEmailMessage.objects.filter(
            owner=self.user,
            direction=ArchibaldEmailMessage.Direction.INBOUND,
        ).first()
        self.assertIsNotNone(inbound)
        self.assertEqual(inbound.status, ArchibaldEmailMessage.Status.SKIPPED)
        self.assertIn("Nessun flag azione riconosciuto", inbound.error_text)

    @patch("archibald_mail.services.send_email_via_smtp")
    @patch("archibald_mail.services.execute_action_from_email")
    @patch("archibald_mail.services.parse_inbound_email")
    @patch("archibald_mail.services.imaplib.IMAP4_SSL")
    def test_process_inbox_executes_actions_even_with_auto_reply_disabled(
        self,
        mock_imap_cls,
        mock_parse,
        mock_execute_action,
        mock_smtp,
    ):
        class FakeMailbox:
            def login(self, *_args, **_kwargs):
                return "OK", [b""]

            def select(self, *_args, **_kwargs):
                return "OK", [b"1"]

            def search(self, *_args, **_kwargs):
                return "OK", [b"1"]

            def fetch(self, *_args, **_kwargs):
                return "OK", [(b"1", b"raw")]

            def store(self, *_args, **_kwargs):
                return "OK", [b""]

            def close(self):
                return "OK", [b""]

            def logout(self):
                return "BYE", [b""]

        mock_imap_cls.return_value = FakeMailbox()
        mock_parse.return_value = ParsedInboundEmail(
            message_id="<msg-1@example.com>",
            in_reply_to="",
            sender="sender@example.com",
            recipient="archibald@miorganizzo.ovh",
            subject="[MEMORY] Link utile",
            body_text="https://example.com/post",
            raw_headers="",
        )
        mock_execute_action.return_value = EmailActionOutcome(
            handled=True,
            action_key="memory_stock.save",
            reply_text="Memoria salvata.",
        )

        self.config.is_enabled = True
        self.config.auto_reply_enabled = False
        self.config.save(update_fields=["is_enabled", "auto_reply_enabled", "updated_at"])

        result = process_inbox_for_config(self.config)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["fetched"], 1)
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["replied"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertTrue(mock_execute_action.called)
        self.assertTrue(mock_smtp.called)

        inbound = ArchibaldEmailMessage.objects.filter(
            owner=self.user,
            direction=ArchibaldEmailMessage.Direction.INBOUND,
        ).first()
        self.assertIsNotNone(inbound)
        self.assertEqual(inbound.status, ArchibaldEmailMessage.Status.REPLIED)

    @patch("archibald_mail.services.send_email_via_smtp")
    @patch("archibald_mail.services._openai_notification_body", return_value="Reminder body")
    def test_send_notification_force_creates_log(self, _mock_ai, mock_smtp):
        self.config.notification_recipient = "digest@example.com"
        self.config.save(update_fields=["notification_recipient", "updated_at"])
        result = send_notification_for_config(self.config, force=True, only_due=False)
        self.assertTrue(result["sent"])
        self.assertEqual(result["status"], "sent")
        self.assertTrue(mock_smtp.called)
        self.assertEqual(mock_smtp.call_args.kwargs["recipient"], "digest@example.com")

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

    @patch("archibald_mail.services.send_email_via_smtp")
    def test_send_due_worklog_prompts_sends_once_per_phase(self, mock_smtp):
        self.config.is_enabled = True
        self.config.notification_recipient = "worklog@example.com"
        self.config.timezone_name = "Europe/Rome"
        self.config.save(update_fields=["is_enabled", "notification_recipient", "timezone_name", "updated_at"])

        morning_now = datetime(2026, 3, 16, 12, 40, tzinfo=ZoneInfo("Europe/Rome"))
        first = send_due_worklog_prompts_for_config(self.config, now=morning_now)
        self.assertTrue(first["sent"])
        self.assertEqual(first["sent_count"], 1)
        self.assertEqual(first["phases"], ["am"])

        duplicate = send_due_worklog_prompts_for_config(self.config, now=morning_now)
        self.assertFalse(duplicate["sent"])
        self.assertEqual(duplicate["sent_count"], 0)

        evening_now = datetime(2026, 3, 16, 18, 40, tzinfo=ZoneInfo("Europe/Rome"))
        second = send_due_worklog_prompts_for_config(self.config, now=evening_now)
        self.assertTrue(second["sent"])
        self.assertEqual(second["sent_count"], 1)
        self.assertEqual(second["phases"], ["pm"])

        self.assertEqual(mock_smtp.call_count, 2)
        subjects = [
            row.subject
            for row in ArchibaldEmailMessage.objects.filter(
                owner=self.user,
                direction=ArchibaldEmailMessage.Direction.NOTIFICATION,
            ).order_by("created_at")
        ]
        self.assertIn("[WORKLOG_AM]", subjects[0])
        self.assertIn("[WORKLOG_PM]", subjects[1])

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


class ArchibaldMailActionsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="mail_action_user",
            password="pwd12345",
            email="action-owner@example.com",
        )

    def test_detect_action_from_subject(self):
        self.assertEqual(detect_action_from_subject("[MEMORY] Articolo"), "memory_stock.save")
        self.assertEqual(detect_action_from_subject("[TODO] Task rapido"), "todo.capture")
        self.assertEqual(detect_action_from_subject("#TRANSACTION Spesa"), "transaction.capture")
        self.assertEqual(detect_action_from_subject("[REMINDER] Evento"), "reminder.capture")
        self.assertEqual(detect_action_from_subject("[ARCHI] Rispondi al volo"), "archi.reply")
        self.assertEqual(detect_action_from_subject("[WORKLOG_AM] 2026-03-16"), "worklog.capture_am")
        self.assertEqual(detect_action_from_subject("[WORKLOG_PM] 2026-03-16"), "worklog.capture_pm")
        self.assertEqual(detect_action_from_subject("ACTION:memory_stock.save nota"), "memory_stock.save")
        self.assertEqual(detect_action_from_subject("ACTION:TODO nota"), "todo.capture")
        self.assertEqual(detect_action_from_subject("ACTION:TRANSACTION nota"), "transaction.capture")
        self.assertEqual(detect_action_from_subject("ACTION:REMINDER nota"), "reminder.capture")
        self.assertEqual(detect_action_from_subject("ACTION:ARCHI nota"), "archi.reply")
        self.assertEqual(detect_action_from_subject("ACTION:planner.pin prova"), "planner.pin")
        self.assertEqual(detect_action_from_subject("Nessuna azione"), "")

    def test_detect_action_from_subject_uses_custom_rule_for_owner(self):
        ArchibaldEmailFlagRule.objects.create(
            owner=self.user,
            label="Interesting Link",
            flag_token="IDEA",
            action_key=ArchibaldEmailFlagRule.ActionKey.MEMORY_STOCK_SAVE,
            is_active=True,
        )
        self.assertEqual(detect_action_from_subject("[IDEA] Link", owner=self.user), "memory_stock.save")

    def test_execute_action_saves_memory_stock_item(self):
        incoming = SimpleNamespace(
            sender="mario@example.com",
            subject="[MEMORY] Articolo interessante",
            body_text="Salva questo link https://example.com/post/1",
            message_id="<msg-memory-1@example.com>",
        )

        outcome = execute_action_from_email(owner=self.user, incoming=incoming, inbound_message=None)
        self.assertTrue(outcome.handled)
        self.assertEqual(outcome.action_key, "memory_stock.save")

        row = MemoryStockItem.objects.get(owner=self.user, source_message_id="<msg-memory-1@example.com>")
        self.assertEqual(row.title, "Articolo interessante")
        self.assertEqual(row.source_url, "https://example.com/post/1")
        self.assertEqual(row.source_sender, "mario@example.com")

    def test_execute_todo_action_uses_memory_stock_fallback(self):
        incoming = SimpleNamespace(
            sender="mario@example.com",
            subject="[TODO] Chiamare fornitore",
            body_text="Dettaglio task https://example.com/todo/fornitore",
            message_id="<msg-todo-1@example.com>",
        )

        outcome = execute_action_from_email(owner=self.user, incoming=incoming, inbound_message=None)
        self.assertTrue(outcome.handled)
        self.assertEqual(outcome.action_key, "todo.capture")

        row = MemoryStockItem.objects.get(owner=self.user, source_message_id="<msg-todo-1@example.com>")
        self.assertEqual(row.title, "Chiamare fornitore")
        self.assertEqual(row.source_action, "todo.capture")

    def test_execute_archi_action_forces_ai_reply(self):
        incoming = SimpleNamespace(
            sender="mario@example.com",
            subject="[ARCHI] Mi rispondi?",
            body_text="Mi serve un recap breve",
            message_id="<msg-archi-action-1@example.com>",
        )

        outcome = execute_action_from_email(owner=self.user, incoming=incoming, inbound_message=None)
        self.assertFalse(outcome.handled)
        self.assertEqual(outcome.action_key, "archi.reply")
        self.assertTrue(outcome.force_ai_reply)

    def test_execute_worklog_am_action_creates_worklog(self):
        incoming = SimpleNamespace(
            sender="mario@example.com",
            subject="[WORKLOG_AM] 2026-03-16",
            body_text="09:00-12:30",
            message_id="<msg-worklog-am-1@example.com>",
        )

        outcome = execute_action_from_email(owner=self.user, incoming=incoming, inbound_message=None)
        self.assertTrue(outcome.handled)
        self.assertEqual(outcome.action_key, "worklog.capture_am")

        row = WorkLog.objects.get(owner=self.user, work_date="2026-03-16")
        self.assertEqual(row.time_start.strftime("%H:%M"), "09:00")
        self.assertEqual(row.time_end.strftime("%H:%M"), "12:30")
        self.assertEqual(row.hours, Decimal("3.50"))
        self.assertEqual(row.lunch_break_minutes, 0)

    def test_execute_worklog_pm_action_calculates_lunch_break(self):
        WorkLog.objects.create(
            owner=self.user,
            work_date="2026-03-16",
            time_start="09:00",
            time_end="12:30",
            lunch_break_minutes=0,
            hours=Decimal("3.50"),
        )
        incoming = SimpleNamespace(
            sender="mario@example.com",
            subject="[WORKLOG_PM] 2026-03-16",
            body_text="14:00-18:30",
            message_id="<msg-worklog-pm-1@example.com>",
        )

        outcome = execute_action_from_email(owner=self.user, incoming=incoming, inbound_message=None)
        self.assertTrue(outcome.handled)
        self.assertEqual(outcome.action_key, "worklog.capture_pm")

        row = WorkLog.objects.get(owner=self.user, work_date="2026-03-16")
        self.assertEqual(row.time_start.strftime("%H:%M"), "09:00")
        self.assertEqual(row.time_end.strftime("%H:%M"), "18:30")
        self.assertEqual(row.hours, Decimal("8.00"))
        self.assertEqual(row.lunch_break_minutes, 90)

    def test_execute_worklog_pm_with_hours_uses_reply_time_for_break(self):
        WorkLog.objects.create(
            owner=self.user,
            work_date="2026-03-16",
            time_start="09:00",
            time_end="12:30",
            lunch_break_minutes=0,
            hours=Decimal("3.50"),
        )
        incoming = SimpleNamespace(
            sender="mario@example.com",
            subject="[WORKLOG_PM] 2026-03-16",
            body_text="4 ore",
            message_id="<msg-worklog-pm-2@example.com>",
        )
        inbound = SimpleNamespace(config=SimpleNamespace(timezone_name="UTC"), config_id=1)

        with patch("archibald_mail.actions.timezone.now", return_value=datetime(2026, 3, 16, 18, 30, tzinfo=ZoneInfo("UTC"))):
            outcome = execute_action_from_email(owner=self.user, incoming=incoming, inbound_message=inbound)
        self.assertTrue(outcome.handled)

        row = WorkLog.objects.get(owner=self.user, work_date="2026-03-16")
        self.assertEqual(row.time_end.strftime("%H:%M"), "18:30")
        self.assertEqual(row.hours, Decimal("7.50"))
        self.assertEqual(row.lunch_break_minutes, 120)

    def test_execute_action_manually_works_for_reminder(self):
        inbound = ArchibaldEmailMessage.objects.create(
            owner=self.user,
            config=ArchibaldMailboxConfig.objects.create(owner=self.user),
            direction=ArchibaldEmailMessage.Direction.INBOUND,
            status=ArchibaldEmailMessage.Status.RECEIVED,
            sender="shop@example.com",
            recipient="archibald@miorganizzo.ovh",
            subject="Promemoria bolletta",
            body_text="Scadenza 2026-03-30 https://example.com/bill/123",
            message_id="<msg-reminder-1@example.com>",
        )
        outcome = execute_action_manually(owner=self.user, message=inbound, action_key="reminder.capture")
        self.assertTrue(outcome.handled)
        row = MemoryStockItem.objects.get(owner=self.user, source_message_id="<msg-reminder-1@example.com>")
        self.assertEqual(row.source_action, "reminder.capture")


class ArchibaldMailPromptingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="mail_prompt_user",
            password="pwd12345",
            email="prompt-owner@example.com",
        )

    @patch("archibald_mail.services.request_openai_response", return_value="Risposta pronta.")
    @patch("archibald_mail.services.build_archibald_system_for_user", return_value="SYSTEM BASE")
    def test_openai_email_reply_includes_real_operational_context_and_guardrails(self, _mock_system, mock_openai):
        routine = Routine.objects.create(owner=self.user, name="Morning", is_active=True)
        RoutineItem.objects.create(
            owner=self.user,
            routine=routine,
            title="Stretching",
            weekday=0,
            is_active=True,
        )

        incoming = ParsedInboundEmail(
            message_id="<msg-ctx-1@example.com>",
            in_reply_to="",
            sender="user@example.com",
            recipient="archibald@miorganizzo.ovh",
            subject="[ARCHI] Aggiornamento routines",
            body_text="mi fai un aggiornamento sulle routines?",
            raw_headers="",
        )
        _openai_email_reply(self.user, incoming)

        self.assertTrue(mock_openai.called)
        messages = mock_openai.call_args.args[0]
        instructions = mock_openai.call_args.args[1]
        prompt = messages[0]["content"]

        self.assertIn("Contesto operativo reale (snapshot DB)", prompt)
        self.assertIn("Task aperti:", prompt)
        self.assertIn("Routine oggi:", prompt)
        self.assertIn("Regole operative vincolanti:", instructions)
        self.assertIn("NON promettere azioni future", instructions)


class ArchibaldMailFlagCrudViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="mail_flag_user",
            password="pwd12345",
            email="flags@example.com",
        )
        self.client.login(username="mail_flag_user", password="pwd12345")

    def test_flag_rules_page_renders(self):
        response = self.client.get("/archibald-mail/flags/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CRUD Flag Inbound")

    def test_create_update_delete_flag_rule(self):
        create_resp = self.client.post(
            "/archibald-mail/flags/add",
            data={
                "label": "Ticket",
                "flag_token": "SUPPORT",
                "action_key": "todo.capture",
                "is_active": "on",
                "notes": "Da telefono",
            },
        )
        self.assertEqual(create_resp.status_code, 302)

        row = ArchibaldEmailFlagRule.objects.get(owner=self.user, flag_token="SUPPORT")
        self.assertEqual(row.action_key, "todo.capture")

        edit_resp = self.client.post(
            f"/archibald-mail/flags/{row.id}/edit",
            data={
                "label": "Ticket aggiornato",
                "flag_token": "SUPPORT",
                "action_key": "transaction.capture",
                "notes": "modifica",
            },
        )
        self.assertEqual(edit_resp.status_code, 302)
        row.refresh_from_db()
        self.assertEqual(row.label, "Ticket aggiornato")
        self.assertEqual(row.action_key, "transaction.capture")
        self.assertFalse(row.is_active)

        delete_resp = self.client.post(f"/archibald-mail/flags/{row.id}/remove", data={})
        self.assertEqual(delete_resp.status_code, 302)
        self.assertFalse(ArchibaldEmailFlagRule.objects.filter(id=row.id).exists())


class ArchibaldMailInboundQueueViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="mail_inbox_user",
            password="pwd12345",
            email="inbox@example.com",
        )
        self.config = ArchibaldMailboxConfig.objects.create(owner=self.user)
        self.client.login(username="mail_inbox_user", password="pwd12345")
        self.inbound = ArchibaldEmailMessage.objects.create(
            owner=self.user,
            config=self.config,
            direction=ArchibaldEmailMessage.Direction.INBOUND,
            status=ArchibaldEmailMessage.Status.RECEIVED,
            sender="portal@example.com",
            recipient="archibald@miorganizzo.ovh",
            subject="Conferma pagamento",
            body_text="Pagamento online effettuato https://example.com/payments/1",
            message_id="<msg-inbox-1@example.com>",
        )

    def test_inbound_queue_page_renders(self):
        response = self.client.get("/archibald-mail/inbox/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inbox Da Gestire")
        self.assertContains(response, "Conferma pagamento")

    def test_apply_inbound_message_sets_review_status(self):
        existing_category = ArchibaldInboundCategory.objects.create(owner=self.user, label="Pagamento")
        response = self.client.post(
            f"/archibald-mail/inbox/{self.inbound.id}/apply",
            data={
                "classification_category_id": str(existing_category.id),
                "action_key": "transaction.capture",
                "review_notes": "Confermato da portale esterno",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.inbound.refresh_from_db()
        self.assertEqual(self.inbound.review_status, ArchibaldEmailMessage.ReviewStatus.APPLIED)
        self.assertEqual(self.inbound.selected_action_key, "transaction.capture")
        self.assertEqual(self.inbound.classification_label, "Pagamento")
        self.assertEqual(self.inbound.classification_category_id, existing_category.id)

    def test_apply_inbound_message_creates_new_category_when_requested(self):
        response = self.client.post(
            f"/archibald-mail/inbox/{self.inbound.id}/apply",
            data={
                "classification_category_id": "__new__",
                "new_category_label": "Rimborso",
                "action_key": "",
                "review_notes": "In attesa verifica",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.inbound.refresh_from_db()
        created_category = ArchibaldInboundCategory.objects.get(owner=self.user, label="Rimborso")
        self.assertEqual(self.inbound.classification_category_id, created_category.id)
        self.assertEqual(self.inbound.classification_label, "Rimborso")
        self.assertEqual(self.inbound.review_status, ArchibaldEmailMessage.ReviewStatus.PENDING)

    def test_ignore_and_reopen_inbound_message(self):
        ignore_resp = self.client.post(f"/archibald-mail/inbox/{self.inbound.id}/ignore", data={})
        self.assertEqual(ignore_resp.status_code, 302)
        self.inbound.refresh_from_db()
        self.assertEqual(self.inbound.review_status, ArchibaldEmailMessage.ReviewStatus.IGNORED)

        reopen_resp = self.client.post(f"/archibald-mail/inbox/{self.inbound.id}/reopen", data={})
        self.assertEqual(reopen_resp.status_code, 302)
        self.inbound.refresh_from_db()
        self.assertEqual(self.inbound.review_status, ArchibaldEmailMessage.ReviewStatus.PENDING)


class ArchibaldMailPermissionsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="mail_limited_user",
            password="pwd12345",
            email="limited@example.com",
        )
        self.config = ArchibaldMailboxConfig.objects.create(owner=self.user)
        self.message = ArchibaldEmailMessage.objects.create(
            owner=self.user,
            config=self.config,
            direction=ArchibaldEmailMessage.Direction.INBOUND,
            status=ArchibaldEmailMessage.Status.RECEIVED,
            sender="portal@example.com",
            recipient="archibald@miorganizzo.ovh",
            subject="Test",
            body_text="Body",
            message_id="<msg-perm-1@example.com>",
        )
        self.client.login(username="mail_limited_user", password="pwd12345")

    def test_non_superuser_cannot_access_archibald_mail_views(self):
        protected_paths = [
            "/archibald-mail/",
            "/archibald-mail/flags/",
            "/archibald-mail/flags/add",
            "/archibald-mail/flags/999/edit",
            "/archibald-mail/flags/999/remove",
            "/archibald-mail/inbox/",
        ]
        for path in protected_paths:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 403, path)

        post_targets = [
            f"/archibald-mail/inbox/{self.message.id}/apply",
            f"/archibald-mail/inbox/{self.message.id}/ignore",
            f"/archibald-mail/inbox/{self.message.id}/reopen",
        ]
        for path in post_targets:
            response = self.client.post(path, data={})
            self.assertEqual(response.status_code, 403, path)


class ArchibaldMailDigestTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="mail_digest_user",
            password="pwd12345",
            email="digest-owner@example.com",
        )
        self.config = ArchibaldMailboxConfig.objects.create(
            owner=self.user,
            notification_include_tasks=False,
            notification_include_planner=False,
            notification_include_subscriptions=False,
            notification_include_routines=False,
            notification_include_reminders=True,
        )

    def test_digest_includes_pending_reminder_inbound(self):
        ArchibaldEmailMessage.objects.create(
            owner=self.user,
            config=self.config,
            direction=ArchibaldEmailMessage.Direction.INBOUND,
            status=ArchibaldEmailMessage.Status.RECEIVED,
            sender="portal@example.com",
            recipient="archibald@miorganizzo.ovh",
            subject="Scadenza bolletta acqua",
            body_text="Promemoria",
            classification_label="Scadenza",
            review_status=ArchibaldEmailMessage.ReviewStatus.PENDING,
        )
        from .services import build_notification_digest

        digest, has_items = build_notification_digest(self.config)
        self.assertTrue(has_items)
        self.assertIn("Reminder da gestire", digest)
        self.assertIn("Scadenza bolletta acqua", digest)
