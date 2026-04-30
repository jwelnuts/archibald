from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .models import MemoryStockItem


URL_PATTERN = re.compile(r'https?://[^\s<>()\[\]{}"\']+', re.IGNORECASE)
ACTION_TOKEN_PATTERN = re.compile(
    r"\[\s*(memory|todo|transaction|reminder)\s*\]|#(memory|todo|transaction|reminder|tx)\b|action\s*:\s*[a-z0-9_.-]+",
    re.IGNORECASE,
)


@dataclass
class MemorySaveResult:
    item: MemoryStockItem
    created: bool
    link_created: bool = False


def extract_first_url(text: str) -> str:
    content = (text or "").strip()
    if not content:
        return ""
    match = URL_PATTERN.search(content)
    if not match:
        return ""
    return match.group(0).strip().rstrip(").,;")


def extract_all_urls(text: str) -> list[str]:
    """Estrae tutti gli URL trovati nel testo."""
    content = (text or "").strip()
    if not content:
        return []
    matches = URL_PATTERN.findall(content)
    return [match.strip().rstrip(").,;") for match in matches]


def clean_subject_for_title(subject: str) -> str:
    cleaned = ACTION_TOKEN_PATTERN.sub(" ", subject or "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -_:\t")


def create_link_from_memory_item(
    memory_item: MemoryStockItem,
    category: str = "",
    importance: int = 3,
) -> Optional["Link"]:
    """
    Crea un Link (link_storage) associato a un MemoryStockItem.
    Se il memory_item ha già un Link associato, lo restituisce.
    """
    if not memory_item.source_url:
        return None
    
    # Controlla se esiste già un Link associato
    if hasattr(memory_item, 'link_specialization') and memory_item.link_specialization:
        return memory_item.link_specialization
    
    try:
        from link_storage.models import Link
        
        # Determina categoria dal contenuto se non fornita
        if not category:
            category = _guess_category_from_content(
                memory_item.title,
                memory_item.note,
                memory_item.source_url
            )
        
        link = Link.objects.create(
            owner=memory_item.owner,
            memory_item=memory_item,
            url=memory_item.source_url[:160],
            category=category,
            importance=importance,
            note=memory_item.note[:500] if memory_item.note else "",
            title_extracted=memory_item.title[:255],
        )
        
        # Aggiorna il tipo del memory_item
        memory_item.item_type = MemoryStockItem.ItemType.LINK
        memory_item.save(update_fields=['item_type'])
        
        return link
        
    except ImportError:
        # link_storage non è disponibile
        return None


def _guess_category_from_content(title: str, note: str, url: str) -> str:
    """Tenta di indovinare la categoria dal contenuto."""
    text = f"{title} {note} {url}".lower()
    
    keywords_map = {
        "TECNOLOGIA": ["tech", "code", "programming", "software", "app", "github", "stackoverflow", "developer"],
        "SALUTE": ["health", "fitness", "gym", "workout", "medical", "doctor", "salute", "benessere"],
        "SPORT": ["sport", "football", "soccer", "basket", "tennis", "running", "calcio"],
        "LAVORO": ["work", "business", "client", "project", "meeting", "job", "lavoro", "azienda"],
        "STUDIO": ["study", "learn", "course", "tutorial", "education", "university", "studio", "corso"],
    }
    
    for category, keywords in keywords_map.items():
        if any(kw in text for kw in keywords):
            return category
    
    return "ALTRI"


def save_memory_from_inbound_email(
    *,
    owner,
    sender: str,
    subject: str,
    body_text: str,
    message_id: str,
    action_key: str,
    auto_create_link: bool = True,
) -> MemorySaveResult:
    """
    Salva un'email in memory_stock.
    Se contiene URL e auto_create_link=True, crea anche un Link associato.
    """
    normalized_msg_id = (message_id or "").strip()
    if normalized_msg_id:
        existing = MemoryStockItem.objects.filter(owner=owner, source_message_id=normalized_msg_id).first()
        if existing:
            return MemorySaveResult(item=existing, created=False)

    title = clean_subject_for_title(subject) or "Memory capture"
    source_url = extract_first_url(body_text)
    urls = extract_all_urls(body_text)
    note = (body_text or "").strip()

    # Determina il tipo in base al contenuto
    item_type = MemoryStockItem.ItemType.GENERIC
    if source_url:
        item_type = MemoryStockItem.ItemType.LINK
    elif len(note) > 500:
        item_type = MemoryStockItem.ItemType.NOTE

    item = MemoryStockItem.objects.create(
        owner=owner,
        title=title[:220],
        item_type=item_type,
        source_url=source_url,
        note=note,
        source_sender=(sender or "").strip().lower(),
        source_subject=(subject or "").strip()[:255],
        source_message_id=normalized_msg_id[:255],
        source_action=(action_key or "")[:64],
        metadata={
            "captured_via": "archibald_mail",
            "url_detected": bool(source_url),
            "urls_count": len(urls),
            "note_chars": len(note),
        },
    )
    
    # Crea automaticamente il Link se c'è un URL
    link_created = False
    if auto_create_link and source_url:
        link = create_link_from_memory_item(item)
        link_created = link is not None

    return MemorySaveResult(item=item, created=True, link_created=link_created)
