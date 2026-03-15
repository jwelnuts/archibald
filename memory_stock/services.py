from __future__ import annotations

import re
from dataclasses import dataclass

from .models import MemoryStockItem


URL_PATTERN = re.compile(r"https?://[^\s<>()\[\]{}\"']+", re.IGNORECASE)
ACTION_TOKEN_PATTERN = re.compile(
    r"\[\s*(memory|todo|transaction|reminder)\s*\]|#(memory|todo|transaction|reminder|tx)\b|action\s*:\s*[a-z0-9_.-]+",
    re.IGNORECASE,
)


@dataclass
class MemorySaveResult:
    item: MemoryStockItem
    created: bool


def extract_first_url(text: str) -> str:
    content = (text or "").strip()
    if not content:
        return ""
    match = URL_PATTERN.search(content)
    if not match:
        return ""
    return match.group(0).strip().rstrip(").,;")


def clean_subject_for_title(subject: str) -> str:
    cleaned = ACTION_TOKEN_PATTERN.sub(" ", subject or "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -_:\t")


def save_memory_from_inbound_email(
    *,
    owner,
    sender: str,
    subject: str,
    body_text: str,
    message_id: str,
    action_key: str,
) -> MemorySaveResult:
    normalized_msg_id = (message_id or "").strip()
    if normalized_msg_id:
        existing = MemoryStockItem.objects.filter(owner=owner, source_message_id=normalized_msg_id).first()
        if existing:
            return MemorySaveResult(item=existing, created=False)

    title = clean_subject_for_title(subject) or "Memory capture"
    source_url = extract_first_url(body_text)
    note = (body_text or "").strip()

    item = MemoryStockItem.objects.create(
        owner=owner,
        title=title[:220],
        source_url=source_url,
        note=note,
        source_sender=(sender or "").strip().lower(),
        source_subject=(subject or "").strip()[:255],
        source_message_id=normalized_msg_id[:255],
        source_action=(action_key or "")[:64],
        metadata={
            "captured_via": "archibald_mail",
            "url_detected": bool(source_url),
            "note_chars": len(note),
        },
    )
    return MemorySaveResult(item=item, created=True)
