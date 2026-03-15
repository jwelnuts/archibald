from __future__ import annotations

import imaplib
import re
import smtplib
from dataclasses import dataclass
from datetime import timedelta
from email import policy
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parseaddr
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from archibald.openai_client import request_openai_response
from archibald.prompting import build_archibald_system_for_user
from memory_stock.models import MemoryStockItem
from planner.models import PlannerItem
from routines.models import RoutineCheck, RoutineItem
from subscriptions.models import SubscriptionOccurrence
from todo.models import Task

from .actions import execute_action_from_email
from .models import ArchibaldEmailMessage, ArchibaldMailboxConfig


class ArchibaldMailError(RuntimeError):
    pass


@dataclass
class ParsedInboundEmail:
    message_id: str
    in_reply_to: str
    sender: str
    recipient: str
    subject: str
    body_text: str
    raw_headers: str


def _safe_header(value: str) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _extract_body(message) -> str:
    if message.is_multipart():
        plain_chunks = []
        html_chunks = []
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_filename():
                continue

            content_type = (part.get_content_type() or "").lower()
            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except LookupError:
                text = payload.decode("utf-8", errors="replace")

            if content_type == "text/plain":
                plain_chunks.append(text)
            elif content_type == "text/html":
                html_chunks.append(text)

        if plain_chunks:
            return "\n".join(chunk.strip() for chunk in plain_chunks if chunk.strip()).strip()
        if html_chunks:
            html = "\n".join(html_chunks)
            cleaned = re.sub(r"<[^>]+>", " ", html)
            cleaned = re.sub(r"\s+", " ", cleaned)
            return cleaned.strip()
        return ""

    payload = message.get_payload(decode=True) or b""
    charset = message.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace").strip()
    except LookupError:
        return payload.decode("utf-8", errors="replace").strip()


def parse_inbound_email(raw_bytes: bytes) -> ParsedInboundEmail:
    parsed = BytesParser(policy=policy.default).parsebytes(raw_bytes)
    sender = (parseaddr(parsed.get("From", ""))[1] or "").strip().lower()
    recipient = (parseaddr(parsed.get("To", ""))[1] or "").strip().lower()
    subject = _safe_header(parsed.get("Subject", "")).strip()
    message_id = (parsed.get("Message-ID") or "").strip()
    in_reply_to = (parsed.get("In-Reply-To") or "").strip()
    body = _extract_body(parsed)

    header_lines = []
    for key in ("Date", "From", "To", "Cc", "Subject", "Message-ID", "In-Reply-To"):
        value = parsed.get(key)
        if value:
            header_lines.append(f"{key}: {_safe_header(value)}")

    return ParsedInboundEmail(
        message_id=message_id,
        in_reply_to=in_reply_to,
        sender=sender,
        recipient=recipient,
        subject=subject,
        body_text=body,
        raw_headers="\n".join(header_lines),
    )


def _reply_subject(config: ArchibaldMailboxConfig, subject: str) -> str:
    prefix = (config.auto_reply_subject_prefix or "Re:").strip() or "Re:"
    subject = (subject or "Messaggio").strip()
    if subject.lower().startswith(prefix.lower()):
        return subject
    return f"{prefix} {subject}".strip()


def _append_signature(text: str, signature: str) -> str:
    if not signature.strip():
        return text
    return f"{text.rstrip()}\n\n{signature.strip()}"


def _sender_allowed(config: ArchibaldMailboxConfig, sender: str) -> bool:
    sender = (sender or "").strip().lower()
    if not sender:
        return False
    if sender == (config.inbox_address or "").strip().lower():
        return False
    pattern = (config.allowed_sender_regex or "").strip()
    if not pattern:
        return True
    try:
        return bool(re.search(pattern, sender))
    except re.error:
        return True


def _build_email_operational_context(owner) -> str:
    if owner is None:
        return "Contesto utente non disponibile."

    today = timezone.localdate()
    horizon = today + timedelta(days=7)
    week_start = today - timedelta(days=today.weekday())

    open_tasks = Task.objects.filter(owner=owner).exclude(status=Task.Status.DONE)
    open_tasks_count = open_tasks.count()
    tasks_due_today = open_tasks.filter(due_date=today).count()
    tasks_due_week = open_tasks.filter(due_date__gte=today, due_date__lte=horizon).count()

    planner_due_week = PlannerItem.objects.filter(
        owner=owner,
        status=PlannerItem.Status.PLANNED,
        due_date__gte=today,
        due_date__lte=horizon,
    ).count()

    subscriptions_due_week = SubscriptionOccurrence.objects.filter(
        owner=owner,
        state=SubscriptionOccurrence.State.PLANNED,
        due_date__gte=today,
        due_date__lte=horizon,
    ).count()

    routine_rows = list(
        RoutineItem.objects.filter(
            owner=owner,
            is_active=True,
            routine__is_active=True,
            weekday=today.weekday(),
        )
        .select_related("routine")
        .order_by("time_start", "routine__name", "title")[:12]
    )
    routine_done = 0
    routine_skipped = 0
    routine_planned = 0
    routine_lines = []
    if routine_rows:
        checks = RoutineCheck.objects.filter(
            owner=owner,
            item_id__in=[row.id for row in routine_rows],
            week_start=week_start,
        )
        status_map = {row.item_id: row.status for row in checks}
        for row in routine_rows:
            status = status_map.get(row.id, RoutineCheck.Status.PLANNED)
            if status == RoutineCheck.Status.DONE:
                routine_done += 1
            elif status == RoutineCheck.Status.SKIPPED:
                routine_skipped += 1
            else:
                routine_planned += 1
            slot = row.time_start.strftime("%H:%M") if row.time_start else "--:--"
            routine_lines.append(f"- {slot} | {row.title} ({row.routine.name}) -> {status}")

    lines = [
        "Contesto operativo reale (snapshot DB):",
        f"- Data locale: {today.isoformat()}",
        f"- Task aperti: {open_tasks_count} (oggi: {tasks_due_today}, prossimi 7 giorni: {tasks_due_week})",
        f"- Planner pianificato prossimi 7 giorni: {planner_due_week}",
        f"- Subscription in scadenza prossimi 7 giorni: {subscriptions_due_week}",
        (
            "- Routine oggi: "
            f"{len(routine_rows)} (DONE: {routine_done}, SKIPPED: {routine_skipped}, PLANNED: {routine_planned})"
        ),
    ]
    if routine_lines:
        lines.append("- Prime routine di oggi:")
        lines.extend(routine_lines[:8])
    return "\n".join(lines)


def _openai_email_reply(owner, incoming: ParsedInboundEmail) -> str:
    operational_context = _build_email_operational_context(owner)
    instructions = (
        build_archibald_system_for_user(owner)
        + "\n"
        + "Modalita email: rispondi in italiano, tono elegante ma concreto, max 220 parole, "
        "senza markdown complesso, chiudi con una micro-azione consigliata.\n"
        "Regole operative vincolanti:\n"
        "- Usa solo i dati realmente presenti nel contesto operativo e nel testo email.\n"
        "- Non inventare stati o automazioni che non esistono nel sistema.\n"
        "- NON promettere azioni future con orari specifici (es. 'ti inviero tra 2 ore') "
        "se non sono gia pianificate nel sistema.\n"
        "- Se un dato non e disponibile, dichiaralo chiaramente e proponi un passo pratico immediato."
    )
    prompt = (
        "Hai ricevuto una email e devi rispondere.\n"
        f"Mittente: {incoming.sender or '-'}\n"
        f"Oggetto: {incoming.subject or '-'}\n"
        "Contesto operativo utente:\n"
        f"{operational_context}\n\n"
        "Testo email:\n"
        f"{incoming.body_text or '(vuoto)'}\n\n"
        "Genera il corpo della risposta email con riferimento esplicito ai dati disponibili sopra."
    )
    return (request_openai_response([{"role": "user", "content": prompt}], instructions) or "").strip()


def send_email_via_smtp(
    config: ArchibaldMailboxConfig,
    *,
    recipient: str,
    subject: str,
    body: str,
    in_reply_to: str = "",
    references: str = "",
) -> None:
    recipient = (recipient or "").strip()
    if not recipient:
        raise ArchibaldMailError("Destinatario email mancante.")
    if not config.is_smtp_configured():
        raise ArchibaldMailError("SMTP non configurato: host/utente/password o mittente mancanti.")

    message = EmailMessage()
    message["From"] = config.smtp_sender()
    message["To"] = recipient
    message["Subject"] = (subject or "Messaggio Archibald").strip()
    if config.smtp_reply_to:
        message["Reply-To"] = config.smtp_reply_to
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
    if references:
        message["References"] = references
    message.set_content((body or "").strip() or "Messaggio vuoto.")

    password = config.resolved_smtp_password()
    smtp_host = config.resolved_smtp_host()
    smtp_port = config.resolved_smtp_port()
    smtp_username = config.resolved_smtp_username()
    if config.smtp_use_ssl:
        client = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20)
    else:
        client = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
    try:
        client.ehlo()
        if not config.smtp_use_ssl and config.smtp_use_tls:
            client.starttls()
            client.ehlo()
        client.login(smtp_username, password)
        client.send_message(message)
    except Exception as exc:  # pragma: no cover - depends on SMTP network
        raise ArchibaldMailError(f"Invio SMTP fallito: {exc}") from exc
    finally:
        try:
            client.quit()
        except Exception:
            pass


def _mark_seen(mailbox, uid: bytes) -> None:
    try:
        mailbox.store(uid, "+FLAGS", "\\Seen")
    except Exception:
        pass


def process_inbox_for_config(
    config: ArchibaldMailboxConfig,
    *,
    limit: int | None = None,
    force: bool = False,
) -> dict:
    if not config.is_enabled and not force:
        return {"status": "disabled", "fetched": 0, "processed": 0, "replied": 0, "skipped": 0, "failed": 0}
    if not config.is_imap_configured():
        raise ArchibaldMailError("IMAP non configurato: host/utente/password mancanti.")
    if not config.is_smtp_configured():
        raise ArchibaldMailError("SMTP non configurato: host/utente/password o mittente mancanti.")

    max_items = limit or config.max_inbox_emails_per_run
    result = {
        "status": "ok",
        "fetched": 0,
        "processed": 0,
        "replied": 0,
        "skipped": 0,
        "failed": 0,
        "errors": [],
    }

    imap_host = config.resolved_imap_host()
    imap_port = config.resolved_imap_port()
    imap_username = config.resolved_imap_username()
    password = config.resolved_imap_password()
    mailbox = None
    try:
        if config.imap_use_ssl:
            mailbox = imaplib.IMAP4_SSL(imap_host, imap_port)
        else:
            mailbox = imaplib.IMAP4(imap_host, imap_port)

        mailbox.login(imap_username, password)
        select_status, _ = mailbox.select(config.imap_mailbox or "INBOX")
        if select_status != "OK":
            raise ArchibaldMailError("Selezione mailbox IMAP fallita.")

        search_status, data = mailbox.search(None, "UNSEEN")
        if search_status != "OK":
            raise ArchibaldMailError("Ricerca messaggi UNSEEN fallita.")

        all_ids = data[0].split() if data and data[0] else []
        selected_ids = all_ids[-max_items:]

        result["fetched"] = len(selected_ids)

        for uid in selected_ids:
            fetch_status, payload = mailbox.fetch(uid, "(RFC822)")
            if fetch_status != "OK" or not payload:
                result["failed"] += 1
                result["errors"].append("Fetch IMAP fallita per un messaggio.")
                _mark_seen(mailbox, uid)
                continue

            raw_bytes = b""
            for row in payload:
                if isinstance(row, tuple) and len(row) >= 2:
                    raw_bytes = row[1] or b""
                    break

            if not raw_bytes:
                result["failed"] += 1
                result["errors"].append("Messaggio IMAP privo di body raw.")
                _mark_seen(mailbox, uid)
                continue

            incoming = parse_inbound_email(raw_bytes)

            already_exists = False
            if incoming.message_id:
                already_exists = ArchibaldEmailMessage.objects.filter(
                    owner=config.owner,
                    direction=ArchibaldEmailMessage.Direction.INBOUND,
                    message_id=incoming.message_id,
                ).exists()
            if already_exists:
                result["skipped"] += 1
                _mark_seen(mailbox, uid)
                continue

            with transaction.atomic():
                inbound = ArchibaldEmailMessage.objects.create(
                    owner=config.owner,
                    config=config,
                    direction=ArchibaldEmailMessage.Direction.INBOUND,
                    status=ArchibaldEmailMessage.Status.RECEIVED,
                    message_id=incoming.message_id,
                    in_reply_to=incoming.in_reply_to,
                    external_ref=uid.decode(errors="ignore"),
                    sender=incoming.sender,
                    recipient=incoming.recipient,
                    subject=incoming.subject,
                    body_text=incoming.body_text,
                    raw_headers=incoming.raw_headers,
                )

                if not _sender_allowed(config, incoming.sender):
                    inbound.status = ArchibaldEmailMessage.Status.SKIPPED
                    inbound.processed_at = timezone.now()
                    inbound.error_text = "Mittente non autorizzato o non valido."
                    inbound.save(update_fields=["status", "processed_at", "error_text", "updated_at"])
                    result["processed"] += 1
                    result["skipped"] += 1
                    _mark_seen(mailbox, uid)
                    continue

                try:
                    action_outcome = execute_action_from_email(
                        owner=config.owner,
                        incoming=incoming,
                        inbound_message=inbound,
                    )

                    if action_outcome.handled:
                        reply_body = action_outcome.reply_text.strip() or "Azione completata."
                    elif action_outcome.force_ai_reply:
                        reply_body = _openai_email_reply(config.owner, incoming)
                    else:
                        inbound.status = ArchibaldEmailMessage.Status.SKIPPED
                        inbound.processed_at = timezone.now()
                        inbound.error_text = "Nessun flag azione riconosciuto: email lasciata da gestire manualmente."
                        inbound.save(update_fields=["status", "processed_at", "error_text", "updated_at"])
                        result["processed"] += 1
                        result["skipped"] += 1
                        _mark_seen(mailbox, uid)
                        continue

                    reply_body = _append_signature(reply_body, config.auto_reply_signature)
                    reply_subject = _reply_subject(config, incoming.subject)

                    send_email_via_smtp(
                        config,
                        recipient=incoming.sender,
                        subject=reply_subject,
                        body=reply_body,
                        in_reply_to=incoming.message_id,
                        references=incoming.message_id,
                    )

                    ArchibaldEmailMessage.objects.create(
                        owner=config.owner,
                        config=config,
                        related_message=inbound,
                        direction=ArchibaldEmailMessage.Direction.OUTBOUND,
                        status=ArchibaldEmailMessage.Status.SENT,
                        in_reply_to=incoming.message_id,
                        sender=config.smtp_sender(),
                        recipient=incoming.sender,
                        subject=reply_subject,
                        body_text=reply_body,
                        sent_at=timezone.now(),
                        processed_at=timezone.now(),
                    )

                    inbound.status = ArchibaldEmailMessage.Status.REPLIED
                    inbound.processed_at = timezone.now()
                    inbound.ai_response_text = reply_body
                    if action_outcome.handled or action_outcome.force_ai_reply:
                        inbound.selected_action_key = action_outcome.action_key
                        inbound.classification_label = action_outcome.action_key
                        inbound.review_status = ArchibaldEmailMessage.ReviewStatus.APPLIED
                        inbound.reviewed_at = timezone.now()
                    inbound.save(
                        update_fields=[
                            "status",
                            "processed_at",
                            "ai_response_text",
                            "selected_action_key",
                            "classification_label",
                            "review_status",
                            "reviewed_at",
                            "updated_at",
                        ]
                    )
                    result["processed"] += 1
                    result["replied"] += 1
                except Exception as exc:
                    error_message = str(exc)
                    inbound.status = ArchibaldEmailMessage.Status.FAILED
                    inbound.processed_at = timezone.now()
                    inbound.error_text = error_message[:3000]
                    inbound.save(update_fields=["status", "processed_at", "error_text", "updated_at"])

                    ArchibaldEmailMessage.objects.create(
                        owner=config.owner,
                        config=config,
                        related_message=inbound,
                        direction=ArchibaldEmailMessage.Direction.OUTBOUND,
                        status=ArchibaldEmailMessage.Status.FAILED,
                        in_reply_to=incoming.message_id,
                        sender=config.smtp_sender(),
                        recipient=incoming.sender,
                        subject=_reply_subject(config, incoming.subject),
                        error_text=error_message[:3000],
                        processed_at=timezone.now(),
                    )
                    result["processed"] += 1
                    result["failed"] += 1
                    result["errors"].append(error_message[:240])

            _mark_seen(mailbox, uid)

    finally:
        if mailbox is not None:
            try:
                mailbox.close()
            except Exception:
                pass
            try:
                mailbox.logout()
            except Exception:
                pass

    config.latest_poll_at = timezone.now()
    if result["failed"] and result["replied"] == 0 and result["processed"] > 0:
        config.latest_poll_status = "error"
    elif result["failed"]:
        config.latest_poll_status = "partial"
    elif result["fetched"] == 0:
        config.latest_poll_status = "no_messages"
    else:
        config.latest_poll_status = "ok"
    config.latest_poll_error = "\n".join(result["errors"][:5])
    config.save(update_fields=["latest_poll_at", "latest_poll_status", "latest_poll_error", "updated_at"])

    return result


def _week_start(day):
    return day - timedelta(days=day.weekday())


def build_notification_digest(config: ArchibaldMailboxConfig) -> tuple[str, bool]:
    today = timezone.localdate()
    horizon = today + timedelta(days=config.notification_days_ahead)

    lines = [
        f"Promemoria Archibald per {today.isoformat()}.",
        f"Finestra scadenze: {today.isoformat()} -> {horizon.isoformat()}.",
        "",
    ]
    has_items = False

    if config.notification_include_tasks:
        tasks = list(
            Task.objects.filter(owner=config.owner, due_date__range=(today, horizon))
            .exclude(status=Task.Status.DONE)
            .order_by("due_date", "priority", "title")[:8]
        )
        if tasks:
            has_items = True
            lines.append("Task aperti in scadenza:")
            for task in tasks:
                lines.append(f"- {task.title} ({task.due_date}, {task.get_priority_display()})")
            lines.append("")

    if config.notification_include_reminders:
        reminder_rows = list(
            ArchibaldEmailMessage.objects.filter(
                owner=config.owner,
                direction=ArchibaldEmailMessage.Direction.INBOUND,
                review_status=ArchibaldEmailMessage.ReviewStatus.PENDING,
            )
            .filter(
                Q(selected_action_key="reminder.capture")
                | Q(classification_label__icontains="reminder")
                | Q(classification_label__icontains="scadenza")
                | Q(classification_label__icontains="evento")
                | Q(classification_category__label__icontains="reminder")
                | Q(classification_category__label__icontains="scadenza")
                | Q(classification_category__label__icontains="evento")
            )
            .order_by("-created_at")[:8]
        )
        if not reminder_rows:
            reminder_rows = list(
                MemoryStockItem.objects.filter(
                    owner=config.owner,
                    is_archived=False,
                    source_action="reminder.capture",
                ).order_by("-created_at")[:8]
            )
        if reminder_rows:
            has_items = True
            lines.append("Reminder da gestire:")
            for row in reminder_rows:
                title = getattr(row, "subject", "") or getattr(row, "title", "") or "Reminder"
                created_at = getattr(row, "created_at", None)
                when = f" ({created_at.date()})" if created_at else ""
                lines.append(f"- {title[:90]}{when}")
            lines.append("")

    if config.notification_include_planner:
        planner_rows = list(
            PlannerItem.objects.filter(
                owner=config.owner,
                status=PlannerItem.Status.PLANNED,
                due_date__range=(today, horizon),
            )
            .order_by("due_date", "title")[:8]
        )
        if planner_rows:
            has_items = True
            lines.append("Planner in scadenza:")
            for row in planner_rows:
                lines.append(f"- {row.title} ({row.due_date})")
            lines.append("")

    if config.notification_include_subscriptions:
        occurrences = list(
            SubscriptionOccurrence.objects.filter(
                owner=config.owner,
                state=SubscriptionOccurrence.State.PLANNED,
                due_date__range=(today, horizon),
            )
            .select_related("subscription", "currency")
            .order_by("due_date")[:8]
        )
        if occurrences:
            has_items = True
            lines.append("Abbonamenti prossimi:")
            for occ in occurrences:
                lines.append(f"- {occ.subscription.name}: {occ.amount} {occ.currency.code} ({occ.due_date})")
            lines.append("")

    if config.notification_include_routines:
        weekday = today.weekday()
        items = list(
            RoutineItem.objects.filter(
                owner=config.owner,
                is_active=True,
                weekday=weekday,
            )
            .select_related("routine")
            .order_by("routine__name", "time_start", "title")[:20]
        )
        if items:
            has_items = True
            checks = RoutineCheck.objects.filter(
                owner=config.owner,
                item__in=items,
                week_start=_week_start(today),
            )
            status_map = {check.item_id: check.status for check in checks}
            lines.append("Routine di oggi:")
            for item in items:
                status = status_map.get(item.id, RoutineCheck.Status.PLANNED)
                lines.append(f"- {item.title} [{status}]")
            lines.append("")

    if not has_items:
        lines.append("Nessuna scadenza critica rilevata nella finestra configurata.")

    digest = "\n".join(lines).strip()
    return digest, has_items


def _notification_due_now(config: ArchibaldMailboxConfig, now=None) -> bool:
    if now is None:
        now = timezone.now()

    try:
        tz = ZoneInfo((config.timezone_name or "UTC").strip() or "UTC")
    except Exception:
        tz = timezone.get_current_timezone()

    local_now = now.astimezone(tz)
    due_time = local_now.replace(
        hour=config.notification_hour,
        minute=config.notification_minute,
        second=0,
        microsecond=0,
    )
    if local_now < due_time:
        return False

    if config.last_notification_sent_at is None:
        return True

    elapsed = now - config.last_notification_sent_at
    return elapsed >= timedelta(hours=24)


def _openai_notification_body(config: ArchibaldMailboxConfig, digest: str) -> str:
    instructions = (
        build_archibald_system_for_user(config.owner)
        + "\nModalita promemoria email: massimo 260 parole, tono gentile ma assertivo, "
        "lista operativa finale con max 3 azioni concrete per oggi."
    )
    prompt = (
        "Trasforma questo digest in una email di promemoria firmata Archibald.\n"
        "Inizia con un breve contesto e poi vai al punto.\n\n"
        f"Digest:\n{digest}"
    )
    return (request_openai_response([{"role": "user", "content": prompt}], instructions) or "").strip()


def send_notification_for_config(
    config: ArchibaldMailboxConfig,
    *,
    force: bool = False,
    only_due: bool = True,
) -> dict:
    if not config.notifications_enabled and not force:
        return {"status": "disabled", "sent": False, "reason": "notifications_disabled"}
    if not config.is_smtp_configured():
        raise ArchibaldMailError("SMTP non configurato per notifiche.")

    target = config.notification_target()
    if not target:
        raise ArchibaldMailError("Nessun destinatario valido per notifiche.")

    if only_due and not force and not _notification_due_now(config):
        return {"status": "not_due", "sent": False, "reason": "time_window"}

    digest, has_items = build_notification_digest(config)
    if not has_items and not force:
        return {"status": "nothing_to_send", "sent": False, "reason": "empty_digest"}

    subject = f"Archibald | Promemoria {timezone.localdate().isoformat()}"
    body = digest
    try:
        ai_body = _openai_notification_body(config, digest)
        if ai_body:
            body = ai_body + "\n\n---\n" + digest
    except Exception:
        pass

    try:
        send_email_via_smtp(config, recipient=target, subject=subject, body=body)
        ArchibaldEmailMessage.objects.create(
            owner=config.owner,
            config=config,
            direction=ArchibaldEmailMessage.Direction.NOTIFICATION,
            status=ArchibaldEmailMessage.Status.SENT,
            sender=config.smtp_sender(),
            recipient=target,
            subject=subject,
            body_text=body,
            sent_at=timezone.now(),
            processed_at=timezone.now(),
        )
        config.last_notification_sent_at = timezone.now()
        config.save(update_fields=["last_notification_sent_at", "updated_at"])
        return {"status": "sent", "sent": True, "reason": "ok"}
    except Exception as exc:
        ArchibaldEmailMessage.objects.create(
            owner=config.owner,
            config=config,
            direction=ArchibaldEmailMessage.Direction.NOTIFICATION,
            status=ArchibaldEmailMessage.Status.FAILED,
            sender=config.smtp_sender(),
            recipient=target,
            subject=subject,
            body_text=body,
            error_text=str(exc)[:3000],
            processed_at=timezone.now(),
        )
        raise


def send_test_email(config: ArchibaldMailboxConfig, *, recipient: str, subject: str, body: str) -> None:
    target = (recipient or "").strip() or config.notification_target()
    if not target:
        raise ArchibaldMailError("Destinatario test mancante.")

    send_email_via_smtp(config, recipient=target, subject=subject, body=body)
    ArchibaldEmailMessage.objects.create(
        owner=config.owner,
        config=config,
        direction=ArchibaldEmailMessage.Direction.TEST,
        status=ArchibaldEmailMessage.Status.SENT,
        sender=config.smtp_sender(),
        recipient=target,
        subject=subject,
        body_text=body,
        sent_at=timezone.now(),
        processed_at=timezone.now(),
    )


def process_inbox_for_all(*, limit: int | None = None) -> list[tuple[ArchibaldMailboxConfig, dict]]:
    rows = []
    configs = ArchibaldMailboxConfig.objects.filter(is_enabled=True).select_related("owner")
    for config in configs:
        try:
            result = process_inbox_for_config(config, limit=limit, force=False)
        except Exception as exc:
            result = {
                "status": "error",
                "fetched": 0,
                "processed": 0,
                "replied": 0,
                "skipped": 0,
                "failed": 1,
                "errors": [str(exc)],
            }
        rows.append((config, result))
    return rows


def send_due_notifications_for_all(*, force: bool = False, only_due: bool = True):
    rows = []
    configs = ArchibaldMailboxConfig.objects.filter(notifications_enabled=True).select_related("owner")
    for config in configs:
        try:
            result = send_notification_for_config(config, force=force, only_due=only_due)
        except Exception as exc:
            result = {"status": "error", "sent": False, "reason": str(exc)}
        rows.append((config, result))
    return rows
