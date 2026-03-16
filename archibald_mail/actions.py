from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
import re
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from django.utils import timezone

from agenda.models import WorkLog
from memory_stock.services import save_memory_from_inbound_email

from .models import ArchibaldEmailFlagRule


EXPLICIT_ACTION_PATTERN = re.compile(r"action\s*:\s*([a-z0-9_.-]+)", re.IGNORECASE)
WORKLOG_DATE_PATTERN = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
WORKLOG_TIME_RANGE_PATTERN = re.compile(
    r"\b(\d{1,2}(?:[:.]\d{2})?)\s*(?:-|–|—|a|to)\s*(\d{1,2}(?:[:.]\d{2})?)\b",
    re.IGNORECASE,
)
WORKLOG_HOURS_PATTERN = re.compile(r"\b(\d+(?:[.,]\d{1,2})?)\s*(?:h|ore|ora)\b", re.IGNORECASE)
WORKLOG_MINUTES_PATTERN = re.compile(r"\b(\d{1,3})\s*(?:min|mins|minuti|minuto)\b", re.IGNORECASE)

WORKLOG_ACTION_AM = "worklog.capture_am"
WORKLOG_ACTION_PM = "worklog.capture_pm"
WORKLOG_TOKEN_AM = "WORKLOG_AM"
WORKLOG_TOKEN_PM = "WORKLOG_PM"

ACTIONS_WITH_MEMORY_STOCK_FALLBACK = {
    "memory_stock.save",
    "todo.capture",
    "transaction.capture",
    "reminder.capture",
}
ACTION_LABELS = {
    "memory_stock.save": "Memory",
    "todo.capture": "Todo",
    "transaction.capture": "Transaction",
    "reminder.capture": "Reminder",
    "archi.reply": "Archibald Reply",
    WORKLOG_ACTION_AM: "Worklog mattina",
    WORKLOG_ACTION_PM: "Worklog pomeriggio",
}
ACTION_DESTINATIONS = {
    "memory_stock.save": "Memory Stock",
    "todo.capture": "Memory Stock (temporaneo)",
    "transaction.capture": "Memory Stock (temporaneo)",
    "reminder.capture": "Memory Stock (temporaneo)",
    "archi.reply": "Risposta email immediata con Archibald",
    WORKLOG_ACTION_AM: "Agenda WorkLog",
    WORKLOG_ACTION_PM: "Agenda WorkLog",
}
DEFAULT_FLAG_RULES = (
    {
        "label": "Memory",
        "flag_token": "MEMORY",
        "action_key": "memory_stock.save",
        "is_active": True,
    },
    {
        "label": "Todo",
        "flag_token": "TODO",
        "action_key": "todo.capture",
        "is_active": True,
    },
    {
        "label": "Transaction",
        "flag_token": "TRANSACTION",
        "action_key": "transaction.capture",
        "is_active": True,
    },
    {
        "label": "Transaction (short)",
        "flag_token": "TX",
        "action_key": "transaction.capture",
        "is_active": True,
    },
    {
        "label": "Reminder",
        "flag_token": "REMINDER",
        "action_key": "reminder.capture",
        "is_active": True,
    },
    {
        "label": "Archibald Reply",
        "flag_token": "ARCHI",
        "action_key": "archi.reply",
        "is_active": True,
    },
    {
        "label": "Worklog Mattina",
        "flag_token": WORKLOG_TOKEN_AM,
        "action_key": WORKLOG_ACTION_AM,
        "is_active": True,
    },
    {
        "label": "Worklog Pomeriggio",
        "flag_token": WORKLOG_TOKEN_PM,
        "action_key": WORKLOG_ACTION_PM,
        "is_active": True,
    },
)


@dataclass
class EmailActionOutcome:
    handled: bool
    action_key: str = ""
    reply_text: str = ""
    force_ai_reply: bool = False


def _destination_for_action(action_key: str) -> str:
    return ACTION_DESTINATIONS.get((action_key or "").strip(), "N/D")


def ensure_default_flag_rules(owner) -> None:
    if owner is None:
        return
    for row in DEFAULT_FLAG_RULES:
        ArchibaldEmailFlagRule.objects.get_or_create(
            owner=owner,
            flag_token=row["flag_token"],
            defaults={
                "label": row["label"],
                "action_key": row["action_key"],
                "is_active": row["is_active"],
            },
        )


def list_supported_email_actions(owner=None) -> tuple[dict, ...]:
    if owner is None:
        return tuple(
            {
                "id": None,
                "key": row["action_key"],
                "label": row["label"],
                "flag_token": row["flag_token"],
                "flags": (
                    f"[{row['flag_token']}]",
                    f"#{row['flag_token']}",
                    f"ACTION:{row['flag_token']}",
                ),
                "destination": _destination_for_action(row["action_key"]),
                "status": "Attiva" if row["is_active"] else "Disattiva",
                "is_active": row["is_active"],
            }
            for row in DEFAULT_FLAG_RULES
        )

    ensure_default_flag_rules(owner)
    rules = ArchibaldEmailFlagRule.objects.filter(owner=owner).order_by("-is_active", "action_key", "flag_token")
    return tuple(
        {
            "id": row.id,
            "key": row.action_key,
            "label": row.label,
            "flag_token": row.flag_token,
            "flags": (
                f"[{row.flag_token}]",
                f"#{row.flag_token}",
                f"ACTION:{row.flag_token}",
            ),
            "destination": _destination_for_action(row.action_key),
            "status": "Attiva" if row.is_active else "Disattiva",
            "is_active": row.is_active,
        }
        for row in rules
    )


def _subject_matches_token(subject: str, token: str) -> bool:
    if not subject or not token:
        return False
    pattern = re.compile(rf"\[\s*{re.escape(token)}\s*\]|#{re.escape(token)}\b", re.IGNORECASE)
    return bool(pattern.search(subject))


def list_action_choices(owner=None) -> tuple[tuple[str, str], ...]:
    rows = list_supported_email_actions(owner)
    output = []
    seen = set()
    for row in rows:
        key = row["key"]
        if key == "archi.reply":
            continue
        if key in seen:
            continue
        seen.add(key)
        output.append((key, ACTION_LABELS.get(key, key)))
    return tuple(output)


def _execute_action_to_memory_stock(*, owner, sender: str, subject: str, body_text: str, message_id: str, action_key: str):
    return save_memory_from_inbound_email(
        owner=owner,
        sender=sender,
        subject=subject,
        body_text=body_text,
        message_id=message_id,
        action_key=action_key,
    )


def _parse_date_from_subject(subject: str, fallback: date) -> date:
    match = WORKLOG_DATE_PATTERN.search(subject or "")
    if not match:
        return fallback
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return fallback


def _parse_time_token(raw: str):
    value = (raw or "").strip().replace(".", ":")
    if not value:
        return None
    if ":" in value:
        left, right = value.split(":", 1)
        if not left.isdigit() or not right.isdigit():
            return None
        hour = int(left)
        minute = int(right)
    else:
        if not value.isdigit():
            return None
        hour = int(value)
        minute = 0
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()


def _extract_time_range(text: str):
    match = WORKLOG_TIME_RANGE_PATTERN.search(text or "")
    if not match:
        return None, None
    start = _parse_time_token(match.group(1))
    end = _parse_time_token(match.group(2))
    return start, end


def _minutes_between(start_time, end_time):
    start_dt = datetime.combine(date.min, start_time)
    end_dt = datetime.combine(date.min, end_time)
    return int((end_dt - start_dt).total_seconds() // 60)


def _minutes_to_hours(minutes: int) -> Decimal:
    return (Decimal(minutes) / Decimal("60")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _extract_worked_minutes(text: str):
    text = (text or "").strip()
    if not text:
        return None
    min_match = WORKLOG_MINUTES_PATTERN.search(text)
    if min_match:
        return int(min_match.group(1))

    hour_match = WORKLOG_HOURS_PATTERN.search(text)
    if hour_match:
        value = hour_match.group(1).replace(",", ".")
        try:
            hours = Decimal(value)
        except Exception:
            return None
        if hours <= 0:
            return None
        return int((hours * Decimal("60")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    numeric_text = text.replace(",", ".").strip()
    if re.fullmatch(r"\d+(?:\.\d{1,2})?", numeric_text):
        hours = Decimal(numeric_text)
        if hours > 0:
            return int((hours * Decimal("60")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return None


def _resolve_local_now(inbound_message):
    now = timezone.now()
    tz_name = ""
    config_obj = getattr(inbound_message, "config", None) if inbound_message is not None else None
    if config_obj is not None:
        tz_name = (getattr(config_obj, "timezone_name", "") or "").strip()
    if not tz_name:
        return now
    try:
        return now.astimezone(ZoneInfo(tz_name))
    except Exception:
        return now


def _append_worklog_note(existing_note: str, line: str) -> str:
    base = (existing_note or "").strip()
    if not base:
        return line
    return f"{base}\n{line}"


def _handle_worklog_am(*, owner, incoming, inbound_message):
    local_now = _resolve_local_now(inbound_message)
    work_date = _parse_date_from_subject(incoming.subject, local_now.date())
    start, end = _extract_time_range(incoming.body_text)
    if not start or not end:
        return (
            "Formato non riconosciuto per il worklog mattina. "
            "Rispondi con una fascia oraria, esempio: 09:00-12:30."
        )
    if end <= start:
        return "Orario non valido: l'orario finale deve essere successivo a quello iniziale."

    morning_minutes = _minutes_between(start, end)
    if morning_minutes <= 0:
        return "Intervallo mattina non valido. Riprova con formato tipo 09:00-12:30."

    morning_hours = _minutes_to_hours(morning_minutes)
    row, _ = WorkLog.objects.get_or_create(
        owner=owner,
        work_date=work_date,
        defaults={
            "hours": morning_hours,
            "time_start": start,
            "time_end": end,
            "lunch_break_minutes": 0,
        },
    )
    row.time_start = start
    row.time_end = end
    row.lunch_break_minutes = 0
    row.hours = morning_hours
    row.note = _append_worklog_note(row.note, f"Archibald mattina: {start.strftime('%H:%M')}-{end.strftime('%H:%M')}")
    row.save(update_fields=["time_start", "time_end", "lunch_break_minutes", "hours", "note", "updated_at"])

    return (
        f"Worklog mattina salvato per {work_date.isoformat()}: "
        f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')} ({morning_hours}h)."
    )


def _handle_worklog_pm(*, owner, incoming, inbound_message):
    local_now = _resolve_local_now(inbound_message)
    work_date = _parse_date_from_subject(incoming.subject, local_now.date())
    row = WorkLog.objects.filter(owner=owner, work_date=work_date).first()
    if row is None or not row.time_start or not row.time_end:
        return (
            "Non ho trovato il blocco mattina per questa data. "
            "Prima rispondi al prompt delle 12:30 con una fascia oraria (es. 09:00-12:30)."
        )

    morning_start = row.time_start
    morning_end = row.time_end
    morning_minutes = _minutes_between(morning_start, morning_end)
    if morning_minutes <= 0:
        return "I dati della mattina non sono validi. Re-invia il blocco mattina."

    pm_start, pm_end = _extract_time_range(incoming.body_text)
    lunch_minutes = 0
    afternoon_minutes = 0
    final_end = None

    if pm_start and pm_end:
        if pm_end <= pm_start:
            return "Intervallo pomeriggio non valido: l'orario finale deve essere successivo a quello iniziale."
        if pm_start < morning_end:
            return "Intervallo pomeriggio non valido: inizio pomeriggio precedente alla fine mattina."
        afternoon_minutes = _minutes_between(pm_start, pm_end)
        lunch_minutes = _minutes_between(morning_end, pm_start)
        final_end = pm_end
    else:
        parsed_minutes = _extract_worked_minutes(incoming.body_text)
        if not parsed_minutes:
            return (
                "Formato pomeriggio non riconosciuto. Rispondi con ore (es. 4 ore) "
                "oppure con fascia oraria (es. 14:00-18:30)."
            )
        final_end = local_now.time().replace(second=0, microsecond=0)
        if final_end <= morning_end:
            return "Orario risposta non coerente con la mattina. Invia una fascia oraria completa per il pomeriggio."
        span_after_morning = _minutes_between(morning_end, final_end)
        lunch_minutes = span_after_morning - parsed_minutes
        if lunch_minutes < 0:
            return (
                "Le ore indicate dopo pranzo superano l'intervallo disponibile. "
                "Invia una fascia oraria completa (es. 14:00-18:30)."
            )
        afternoon_minutes = parsed_minutes

    total_minutes = morning_minutes + afternoon_minutes
    total_hours = _minutes_to_hours(total_minutes)
    row.time_start = morning_start
    row.time_end = final_end
    row.lunch_break_minutes = int(lunch_minutes)
    row.hours = total_hours
    row.note = _append_worklog_note(
        row.note,
        (
            "Archibald pomeriggio: "
            f"+{_minutes_to_hours(afternoon_minutes)}h, pausa pranzo calcolata {int(lunch_minutes)} min"
        ),
    )
    row.save(update_fields=["time_start", "time_end", "lunch_break_minutes", "hours", "note", "updated_at"])

    return (
        f"Worklog aggiornato {work_date.isoformat()}: totale {total_hours}h, "
        f"pausa pranzo calcolata {int(lunch_minutes)} minuti."
    )


def detect_action_from_subject(subject: str, owner=None) -> str:
    text = (subject or "").strip()
    if not text:
        return ""

    if owner is None:
        active_rules = [row for row in DEFAULT_FLAG_RULES if row.get("is_active")]
    else:
        ensure_default_flag_rules(owner)
        active_rules = list(
            ArchibaldEmailFlagRule.objects.filter(owner=owner, is_active=True).order_by("flag_token")
        )

    for row in active_rules:
        token = row["flag_token"] if isinstance(row, dict) else row.flag_token
        action_key = row["action_key"] if isinstance(row, dict) else row.action_key
        if _subject_matches_token(text, token):
            return action_key

    explicit_match = EXPLICIT_ACTION_PATTERN.search(text)
    if explicit_match:
        explicit_raw = (explicit_match.group(1) or "").strip().lower()
        if not explicit_raw:
            return ""

        alias_map = {}
        for row in active_rules:
            token = row["flag_token"] if isinstance(row, dict) else row.flag_token
            action_key = row["action_key"] if isinstance(row, dict) else row.action_key
            alias_map[token.lower()] = action_key
            alias_map[action_key.lower()] = action_key
        if explicit_raw in alias_map:
            return alias_map[explicit_raw]
        return explicit_raw

    return ""


def execute_action_from_email(*, owner, incoming, inbound_message) -> EmailActionOutcome:
    action_key = detect_action_from_subject(incoming.subject, owner=owner)
    if not action_key:
        return EmailActionOutcome(handled=False)

    if action_key == "archi.reply":
        return EmailActionOutcome(handled=False, action_key=action_key, force_ai_reply=True)

    if action_key == WORKLOG_ACTION_AM:
        reply_text = _handle_worklog_am(owner=owner, incoming=incoming, inbound_message=inbound_message)
        return EmailActionOutcome(handled=True, action_key=action_key, reply_text=reply_text)

    if action_key == WORKLOG_ACTION_PM:
        reply_text = _handle_worklog_pm(owner=owner, incoming=incoming, inbound_message=inbound_message)
        return EmailActionOutcome(handled=True, action_key=action_key, reply_text=reply_text)

    if action_key in ACTIONS_WITH_MEMORY_STOCK_FALLBACK:
        save_result = _execute_action_to_memory_stock(
            owner=owner,
            sender=incoming.sender,
            subject=incoming.subject,
            body_text=incoming.body_text,
            message_id=incoming.message_id,
            action_key=action_key,
        )
        item = save_result.item
        action_label = ACTION_LABELS.get(action_key, action_key)
        if action_key == "memory_stock.save":
            if save_result.created:
                base = f"Memoria salvata in Memory Stock: {item.title}."
            else:
                base = f"Memoria già presente in Memory Stock: {item.title}."
        else:
            if save_result.created:
                base = f"Azione {action_label} registrata in Memory Stock (temporaneo): {item.title}."
            else:
                base = f"Azione {action_label} già registrata in Memory Stock: {item.title}."
        if item.source_url:
            base += f" URL: {item.source_url}"
        base += " Puoi rivederla su /memory-stock/."
        return EmailActionOutcome(handled=True, action_key=action_key, reply_text=base)

    return EmailActionOutcome(handled=False)


def execute_action_manually(*, owner, message, action_key: str) -> EmailActionOutcome:
    selected = (action_key or "").strip().lower()
    if not selected:
        return EmailActionOutcome(handled=False, action_key="")

    if selected in ACTIONS_WITH_MEMORY_STOCK_FALLBACK:
        save_result = _execute_action_to_memory_stock(
            owner=owner,
            sender=message.sender,
            subject=message.subject,
            body_text=message.body_text,
            message_id=message.message_id,
            action_key=selected,
        )
        item = save_result.item
        action_label = ACTION_LABELS.get(selected, selected)
        if save_result.created:
            base = f"Email classificata come {action_label} e salvata in Memory Stock: {item.title}."
        else:
            base = f"Email classificata come {action_label}; voce già presente in Memory Stock: {item.title}."
        return EmailActionOutcome(handled=True, action_key=selected, reply_text=base)

    return EmailActionOutcome(handled=False, action_key=selected, reply_text="Azione non supportata.")
