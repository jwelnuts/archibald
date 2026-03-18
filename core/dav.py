from __future__ import annotations

import fcntl
import logging
import os
import re
import secrets
import stat
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from passlib.context import CryptContext

from .models import DavAccount

_DAV_USERNAME_SANITIZER = re.compile(r"[^a-z0-9._@+-]+")
_HASH_CONTEXT = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
_LEGACY_HASH_PREFIXES = ("{SSHA}", "{SHA}")
_UNSUPPORTED_HASH_PREFIXES = ("$2a$", "$2b$", "$2y$", "$6$", "$1$", "$apr1$")
logger = logging.getLogger(__name__)


class DavProvisioningError(RuntimeError):
    pass


def caldav_base_url() -> str:
    raw = (settings.CALDAV_BASE_URL or "").strip()
    if not raw:
        return ""
    return raw if raw.endswith("/") else f"{raw}/"


def _service_account_username() -> str:
    return (settings.CALDAV_SERVICE_USERNAME or "").strip().lower()


def _service_account_password() -> str:
    return (settings.CALDAV_SERVICE_PASSWORD or "").strip()


def _normalize_user_part(value: str, fallback: str) -> str:
    normalized = _DAV_USERNAME_SANITIZER.sub("-", value.lower()).strip("-")
    return normalized or fallback


def _build_base_username(user) -> str:
    raw_user = _normalize_user_part(str(getattr(user, "username", "")), f"user-{user.id}")
    domain = (getattr(settings, "CALDAV_LOGIN_DOMAIN", "") or "").strip().lower()
    if domain and "@" not in raw_user:
        return f"{raw_user}@{domain}"
    return raw_user


def _next_available_username(base_username: str, exclude_user_id: int | None = None) -> str:
    candidate = base_username
    sequence = 2
    while True:
        qs = DavAccount.objects.filter(dav_username=candidate)
        if exclude_user_id is not None:
            qs = qs.exclude(user_id=exclude_user_id)
        if not qs.exists():
            return candidate
        candidate = f"{base_username}-{sequence}"
        sequence += 1


def _generate_app_password() -> str:
    return secrets.token_urlsafe(24)


def _is_supported_hash(value: str) -> bool:
    return bool(_HASH_CONTEXT.identify(value))


def _hash_password(raw_password: str) -> str:
    return _HASH_CONTEXT.hash(raw_password)


def _hash_or_keep(raw_value: str) -> str:
    if _is_supported_hash(raw_value):
        return raw_value
    if raw_value.startswith(_LEGACY_HASH_PREFIXES) or raw_value.startswith(_UNSUPPORTED_HASH_PREFIXES):
        raise DavProvisioningError(
            "Hash DAV legacy non supportato rilevato: usa password in chiaro oppure hash sha256_crypt."
        )
    return _hash_password(raw_value)


def _users_file_path() -> Path:
    configured = (getattr(settings, "RADICALE_USERS_FILE", "") or "").strip()
    if not configured:
        raise DavProvisioningError("RADICALE_USERS_FILE non configurato.")
    return Path(configured)


def _users_lock_path(users_path: Path) -> Path:
    configured = (getattr(settings, "RADICALE_USERS_LOCK_FILE", "") or "").strip()
    return Path(configured) if configured else Path(f"{users_path}.lock")


def _build_users_payload() -> dict[str, str]:
    entries: dict[str, str] = {}
    for username, password_hash in DavAccount.objects.filter(is_active=True).values_list("dav_username", "password_hash"):
        if username and password_hash:
            if not _is_supported_hash(password_hash):
                logger.warning(
                    "Skipping DAV user '%s' with unsupported hash; rotate password to reprovision.",
                    username,
                )
                continue
            entries[username] = password_hash

    svc_username = _service_account_username()
    svc_password = _service_account_password()
    if svc_username and svc_password:
        svc_hash = _hash_or_keep(svc_password)
        if svc_username in entries and entries[svc_username] != svc_hash:
            raise DavProvisioningError(
                f"Conflitto account DAV: username '{svc_username}' gia assegnato a un utente applicativo."
            )
        entries[svc_username] = svc_hash
    return entries


def sync_radicale_users_file() -> None:
    users_path = _users_file_path()
    lock_path = _users_lock_path(users_path)
    payload = _build_users_payload()
    existing_uid: int | None = None
    existing_gid: int | None = None
    existing_mode: int | None = None

    if users_path.exists():
        try:
            existing_stat = users_path.stat()
            existing_uid = existing_stat.st_uid
            existing_gid = existing_stat.st_gid
            existing_mode = stat.S_IMODE(existing_stat.st_mode)
        except OSError:
            existing_uid = None
            existing_gid = None
            existing_mode = None

    users_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        tmp_path = Path(f"{users_path}.tmp")
        with tmp_path.open("w", encoding="utf-8") as tmp_handle:
            for username in sorted(payload):
                tmp_handle.write(f"{username}:{payload[username]}\n")
        if existing_uid is not None and existing_gid is not None:
            try:
                os.chown(tmp_path, existing_uid, existing_gid)
            except PermissionError:
                pass
        if existing_mode is not None:
            try:
                os.chmod(tmp_path, existing_mode)
            except PermissionError:
                pass
        os.replace(tmp_path, users_path)
        if existing_mode is None:
            try:
                os.chmod(users_path, 0o600)
            except PermissionError:
                pass


def ensure_user_dav_access(
    user,
    rotate_password: bool = False,
    raw_password: str | None = None,
) -> tuple[DavAccount, str | None]:
    if not getattr(settings, "CALDAV_ENABLED", False):
        raise DavProvisioningError("Integrazione CalDAV disabilitata.")

    if not user or not getattr(user, "id", None):
        raise DavProvisioningError("Utente non valido per provisioning DAV.")

    with transaction.atomic():
        account = DavAccount.objects.select_for_update().filter(user=user).first()
        if account is None:
            base_username = _build_base_username(user)
            account = DavAccount(
                user=user,
                dav_username=_next_available_username(base_username),
                password_hash="",
                is_active=True,
            )

        issued_password = None
        if raw_password is not None:
            if not raw_password:
                raise DavProvisioningError("Password DAV vuota non consentita.")
            account.password_hash = _hash_password(raw_password)
            account.password_rotated_at = timezone.now()
        elif rotate_password or not account.password_hash or not _is_supported_hash(account.password_hash):
            issued_password = _generate_app_password()
            account.password_hash = _hash_password(issued_password)
            account.password_rotated_at = timezone.now()
        account.is_active = True
        account.save()
        sync_radicale_users_file()
    return account, issued_password
