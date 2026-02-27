import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _derive_fernet_key(seed: bytes) -> bytes:
    digest = hashlib.sha256(seed).digest()
    return base64.urlsafe_b64encode(digest)


def _normalize_key(raw_key: str) -> bytes:
    value = (raw_key or "").strip()
    if not value:
        # Fallback deterministico per sviluppo locale.
        return _derive_fernet_key(settings.SECRET_KEY.encode("utf-8"))

    candidate = value.encode("utf-8")
    try:
        Fernet(candidate)
        return candidate
    except ValueError:
        # Supporta passphrase arbitrarie in env (es. "mio-vault-key") rendendole Fernet-safe.
        return _derive_fernet_key(candidate)


def _fernet() -> Fernet:
    raw_key = os.getenv("VAULT_ENCRYPTION_KEY") or ""
    return Fernet(_normalize_key(raw_key))


def encrypt_text(value: str) -> str:
    if not value:
        return ""
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Impossibile decifrare il contenuto del vault.") from exc
