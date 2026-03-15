from __future__ import annotations

import re
from dataclasses import dataclass

from memory_stock.services import save_memory_from_inbound_email

from .models import ArchibaldEmailFlagRule


EXPLICIT_ACTION_PATTERN = re.compile(r"action\s*:\s*([a-z0-9_.-]+)", re.IGNORECASE)
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
}
ACTION_DESTINATIONS = {
    "memory_stock.save": "Memory Stock",
    "todo.capture": "Memory Stock (temporaneo)",
    "transaction.capture": "Memory Stock (temporaneo)",
    "reminder.capture": "Memory Stock (temporaneo)",
    "archi.reply": "Risposta email immediata con Archibald",
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
