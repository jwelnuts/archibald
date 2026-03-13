import binascii
import base64
import os

import pyotp


def issuer_name() -> str:
    return (os.getenv("VAULT_TOTP_ISSUER") or "MIO Vault").strip()


def generate_secret() -> str:
    return pyotp.random_base32()


def _normalize_secret(secret: str) -> str:
    return (secret or "").strip().replace(" ", "")


def _is_base32_secret(secret: str) -> bool:
    normalized = _normalize_secret(secret).upper()
    if not normalized:
        return False
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    try:
        base64.b32decode(f"{normalized}{padding}", casefold=True)
        return True
    except (binascii.Error, ValueError, TypeError):
        return False


def _build_totp(secret: str):
    normalized = _normalize_secret(secret)
    if not _is_base32_secret(normalized):
        return None
    try:
        return pyotp.TOTP(normalized)
    except (TypeError, ValueError, binascii.Error):
        return None


def is_valid_secret(secret: str) -> bool:
    return _build_totp(secret) is not None


def provisioning_uri(username: str, secret: str) -> str:
    totp = _build_totp(secret)
    if totp is None:
        raise ValueError("Secret TOTP non valido.")
    account_name = (username or "user").strip()
    return totp.provisioning_uri(name=account_name, issuer_name=issuer_name())


def verify_code(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    totp = _build_totp(secret)
    if totp is None:
        return False
    try:
        return bool(totp.verify(str(code).strip(), valid_window=1))
    except (TypeError, ValueError, binascii.Error):
        return False
