from __future__ import annotations

import fcntl
import json
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

from .models import DavAccount, DavCalendarGrant, DavExternalAccount, DavManagedCalendar

_DAV_USERNAME_SANITIZER = re.compile(r"[^a-z0-9._@+-]+")
_DAV_PRINCIPAL_SANITIZER = re.compile(r"[^a-z0-9._@+-]+")
_DAV_COLLECTION_SANITIZER = re.compile(r"[^a-z0-9._-]+")
_HASH_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
_LEGACY_HASH_PREFIXES = ("{SSHA}", "{SHA}")
_UNSUPPORTED_HASH_PREFIXES = ("$5$", "$6$", "$1$", "$apr1$")
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


def _append_login_domain(username: str) -> str:
    domain = (getattr(settings, "CALDAV_LOGIN_DOMAIN", "") or "").strip().lower()
    if domain and "@" not in username:
        return f"{username}@{domain}"
    return username


def _normalize_user_part(value: str, fallback: str) -> str:
    normalized = _DAV_USERNAME_SANITIZER.sub("-", value.lower()).strip("-")
    return normalized or fallback


def _normalize_dav_principal(value: str) -> str:
    principal = _DAV_PRINCIPAL_SANITIZER.sub("-", (value or "").strip().lower()).strip("-")
    if not principal:
        raise DavProvisioningError("Principal DAV non valido.")
    return principal


def _normalize_dav_collection_slug(value: str) -> str:
    slug = _DAV_COLLECTION_SANITIZER.sub("-", (value or "").strip().lower()).strip("-.")
    if not slug:
        raise DavProvisioningError("Nome calendario DAV non valido.")
    return slug


def default_user_collection_slug() -> str:
    raw = (
        getattr(settings, "CALDAV_DEFAULT_USER_COLLECTION", "")
        or getattr(settings, "CALDAV_TODO_COLLECTION", "")
        or "personal_dav"
    )
    return _normalize_dav_collection_slug(raw)


def _build_base_username(user) -> str:
    raw_user = _normalize_user_part(str(getattr(user, "username", "")), f"user-{user.id}")
    return _append_login_domain(raw_user)


def _build_external_base_username(owner, raw_hint: str) -> str:
    hint = _normalize_user_part(raw_hint, f"guest-{owner.id}")
    owner_part = _normalize_user_part(str(getattr(owner, "username", "")), f"owner-{owner.id}")
    return _append_login_domain(f"{owner_part}-{hint}")


def _username_exists(candidate: str, *, exclude_user_id: int | None = None, exclude_external_id: int | None = None) -> bool:
    internal_qs = DavAccount.objects.filter(dav_username=candidate)
    if exclude_user_id is not None:
        internal_qs = internal_qs.exclude(user_id=exclude_user_id)
    if internal_qs.exists():
        return True

    external_qs = DavExternalAccount.objects.filter(dav_username=candidate)
    if exclude_external_id is not None:
        external_qs = external_qs.exclude(id=exclude_external_id)
    return external_qs.exists()


def _next_available_username(
    base_username: str,
    *,
    exclude_user_id: int | None = None,
    exclude_external_id: int | None = None,
) -> str:
    candidate = base_username
    sequence = 2
    while True:
        if not _username_exists(
            candidate,
            exclude_user_id=exclude_user_id,
            exclude_external_id=exclude_external_id,
        ):
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
            "Hash DAV legacy non supportato rilevato: usa password in chiaro oppure hash bcrypt."
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


def _rights_file_path(users_path: Path) -> Path:
    configured = (getattr(settings, "RADICALE_RIGHTS_FILE", "") or "").strip()
    return Path(configured) if configured else users_path.parent / "rights"


def _sync_owner_from_reference(path: Path, reference: Path | None) -> None:
    if not reference or not reference.exists():
        return
    try:
        stat_ref = reference.stat()
        os.chown(path, stat_ref.st_uid, stat_ref.st_gid)
    except OSError:
        return


def _radicale_collections_root(users_path: Path) -> Path:
    return users_path.parent / "collections" / "collection-root"


def ensure_calendar_collection(*, principal: str, calendar_slug: str, display_name: str = "") -> tuple[Path, Path]:
    users_path = _users_file_path()
    principal_value = _normalize_dav_principal(principal)
    slug_value = _normalize_dav_collection_slug(calendar_slug)

    collections_root = _radicale_collections_root(users_path)
    principal_dir = collections_root / principal_value
    calendar_dir = principal_dir / slug_value

    principal_dir.mkdir(parents=True, exist_ok=True)
    calendar_dir.mkdir(parents=True, exist_ok=True)
    _sync_owner_from_reference(principal_dir, users_path)
    _sync_owner_from_reference(calendar_dir, users_path)

    props_payload = {"tag": "VCALENDAR"}
    display_name_value = (display_name or "").strip()
    if display_name_value:
        props_payload["D:displayname"] = display_name_value[:120]

    props_path = calendar_dir / ".Radicale.props"
    props_path.write_text(json.dumps(props_payload, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    _sync_owner_from_reference(props_path, users_path)
    return calendar_dir, props_path


def ensure_user_default_collection(
    *,
    principal: str,
    calendar_slug: str | None = None,
    display_name: str = "Personal DAV",
    legacy_slug: str = "calendario",
) -> tuple[Path, Path, bool]:
    users_path = _users_file_path()
    principal_value = _normalize_dav_principal(principal)
    target_slug = _normalize_dav_collection_slug(calendar_slug or default_user_collection_slug())
    legacy_slug_value = _normalize_dav_collection_slug(legacy_slug) if legacy_slug else ""

    collections_root = _radicale_collections_root(users_path)
    principal_dir = collections_root / principal_value
    target_dir = principal_dir / target_slug
    legacy_dir = principal_dir / legacy_slug_value if legacy_slug_value else None
    moved_legacy = False

    principal_dir.mkdir(parents=True, exist_ok=True)
    _sync_owner_from_reference(principal_dir, users_path)

    if (
        legacy_dir
        and legacy_slug_value != target_slug
        and legacy_dir.exists()
        and legacy_dir.is_dir()
        and not target_dir.exists()
    ):
        legacy_dir.rename(target_dir)
        moved_legacy = True

    target_dir.mkdir(parents=True, exist_ok=True)
    _sync_owner_from_reference(target_dir, users_path)

    props_payload = {"tag": "VCALENDAR"}
    display_name_value = (display_name or "").strip()
    if display_name_value:
        props_payload["D:displayname"] = display_name_value[:120]
    props_path = target_dir / ".Radicale.props"
    props_path.write_text(json.dumps(props_payload, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    _sync_owner_from_reference(props_path, users_path)
    return target_dir, props_path, moved_legacy


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

    for username, password_hash in DavExternalAccount.objects.filter(is_active=True).values_list("dav_username", "password_hash"):
        if username and password_hash:
            if not _is_supported_hash(password_hash):
                logger.warning(
                    "Skipping external DAV user '%s' with unsupported hash; rotate password to reprovision.",
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
                f"Conflitto account DAV: username '{svc_username}' gia assegnato a un account applicativo/esterno."
            )
        entries[svc_username] = svc_hash
    return entries


def _join_username_regex(usernames: list[str]) -> str:
    cleaned = sorted({item for item in usernames if item})
    if not cleaned:
        return ""
    escaped = [re.escape(item) for item in cleaned]
    if len(escaped) == 1:
        return f"^{escaped[0]}$"
    return f"^(?:{'|'.join(escaped)})$"


def _rights_permissions_for_grant(access_level: str) -> str:
    return "RWrw" if access_level == DavCalendarGrant.ACCESS_READWRITE else "Rr"


def _build_rights_payload() -> str:
    lines: list[str] = [
        "[allow-discovery-root]",
        "user: .+",
        "collection:",
        "permissions: R",
        "",
    ]

    svc_username = _service_account_username()
    if svc_username:
        lines.extend(
            [
                "[allow-service-full]",
                f"user: ^{re.escape(svc_username)}$",
                "collection: .+",
                "permissions: RWrw",
                "",
            ]
        )

    app_usernames = list(
        DavAccount.objects.filter(is_active=True).order_by("dav_username").values_list("dav_username", flat=True)
    )
    for idx, username in enumerate(app_usernames, start=1):
        lines.extend(
            [
                f"[allow-app-principal-{idx}]",
                f"user: ^{re.escape(username)}$",
                "collection: {user}/?",
                "permissions: RW",
                "",
                f"[allow-app-calendars-{idx}]",
                f"user: ^{re.escape(username)}$",
                "collection: {user}/[^/]+(?:/.*)?",
                "permissions: RWrw",
                "",
            ]
        )

    app_users_regex = _join_username_regex(app_usernames)
    if app_users_regex:
        lines.extend(
            [
                "[allow-app-team-principal]",
                f"user: {app_users_regex}",
                "collection: team/?",
                "permissions: R",
                "",
                "[allow-app-team-calendars]",
                f"user: {app_users_regex}",
                "collection: team/[^/]+(?:/.*)?",
                "permissions: RWrw",
                "",
            ]
        )

    external_usernames = list(
        DavExternalAccount.objects.filter(is_active=True).order_by("dav_username").values_list("dav_username", flat=True)
    )
    for idx, username in enumerate(external_usernames, start=1):
        lines.extend(
            [
                f"[allow-ext-principal-{idx}]",
                f"user: ^{re.escape(username)}$",
                "collection: {user}/?",
                "permissions: RW",
                "",
                f"[allow-ext-calendars-{idx}]",
                f"user: ^{re.escape(username)}$",
                "collection: {user}/[^/]+(?:/.*)?",
                "permissions: RWrw",
                "",
            ]
        )

    grants_rows = DavCalendarGrant.objects.filter(
        is_active=True,
        external_account__is_active=True,
        calendar__is_active=True,
    ).values_list(
        "external_account__dav_username",
        "calendar__principal",
        "calendar__calendar_slug",
        "access_level",
    )

    grants_map: dict[tuple[str, str], str] = {}
    principals_per_user: dict[str, set[str]] = {}
    for username, principal, slug, access_level in grants_rows:
        username_value = (username or "").strip()
        principal_value = _normalize_dav_principal(principal)
        slug_value = _normalize_dav_collection_slug(slug)
        if not username_value:
            continue
        path = f"{principal_value}/{slug_value}"
        current_access = grants_map.get((username_value, path), DavCalendarGrant.ACCESS_READONLY)
        if access_level == DavCalendarGrant.ACCESS_READWRITE or current_access == DavCalendarGrant.ACCESS_READWRITE:
            grants_map[(username_value, path)] = DavCalendarGrant.ACCESS_READWRITE
        else:
            grants_map[(username_value, path)] = DavCalendarGrant.ACCESS_READONLY
        principals_per_user.setdefault(username_value, set()).add(principal_value)

    for idx, (username, principals) in enumerate(sorted(principals_per_user.items()), start=1):
        for principal in sorted(principals):
            lines.extend(
                [
                    f"[allow-ext-shared-principal-{idx}-{re.sub(r'[^a-z0-9]+', '-', principal)}]",
                    f"user: ^{re.escape(username)}$",
                    f"collection: ^{re.escape(principal)}/?$",
                    "permissions: R",
                    "",
                ]
            )

    for idx, ((username, path), access_level) in enumerate(sorted(grants_map.items()), start=1):
        lines.extend(
            [
                f"[allow-ext-shared-calendar-{idx}]",
                f"user: ^{re.escape(username)}$",
                f"collection: ^{re.escape(path)}(?:/.*)?$",
                f"permissions: {_rights_permissions_for_grant(access_level)}",
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def _copy_owner_and_mode(tmp_path: Path, *, existing_path: Path, fallback_owner_path: Path | None = None) -> None:
    uid = None
    gid = None
    mode = None
    if existing_path.exists():
        try:
            existing_stat = existing_path.stat()
            uid = existing_stat.st_uid
            gid = existing_stat.st_gid
            mode = stat.S_IMODE(existing_stat.st_mode)
        except OSError:
            uid = None
            gid = None
            mode = None
    elif fallback_owner_path is not None and fallback_owner_path.exists():
        try:
            fallback_stat = fallback_owner_path.stat()
            uid = fallback_stat.st_uid
            gid = fallback_stat.st_gid
        except OSError:
            uid = None
            gid = None

    if uid is not None and gid is not None:
        try:
            os.chown(tmp_path, uid, gid)
        except PermissionError:
            pass
    if mode is not None:
        try:
            os.chmod(tmp_path, mode)
        except PermissionError:
            pass


def sync_radicale_users_file() -> None:
    users_path = _users_file_path()
    rights_path = _rights_file_path(users_path)
    lock_path = _users_lock_path(users_path)
    users_payload = _build_users_payload()
    rights_payload = _build_rights_payload()

    users_path.parent.mkdir(parents=True, exist_ok=True)
    rights_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

        users_existed = users_path.exists()
        users_tmp = Path(f"{users_path}.tmp")
        with users_tmp.open("w", encoding="utf-8") as users_handle:
            for username in sorted(users_payload):
                users_handle.write(f"{username}:{users_payload[username]}\n")
        _copy_owner_and_mode(users_tmp, existing_path=users_path)
        os.replace(users_tmp, users_path)
        if not users_existed:
            try:
                os.chmod(users_path, 0o600)
            except PermissionError:
                pass

        rights_existed = rights_path.exists()
        rights_tmp = Path(f"{rights_path}.tmp")
        with rights_tmp.open("w", encoding="utf-8") as rights_handle:
            rights_handle.write(rights_payload)
        _copy_owner_and_mode(rights_tmp, existing_path=rights_path, fallback_owner_path=users_path)
        os.replace(rights_tmp, rights_path)
        if not rights_existed:
            try:
                os.chmod(rights_path, 0o600)
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
        _calendar_dir, _props_path, moved_legacy = ensure_user_default_collection(principal=account.dav_username)
        if moved_legacy:
            logger.info(
                "DAV collection migrated for '%s': 'calendario' -> '%s'",
                account.dav_username,
                default_user_collection_slug(),
            )
    return account, issued_password


def create_external_dav_account(*, owner, label: str = "", username_hint: str = "", raw_password: str | None = None) -> tuple[DavExternalAccount, str]:
    if not getattr(settings, "CALDAV_ENABLED", False):
        raise DavProvisioningError("Integrazione CalDAV disabilitata.")
    if not owner or not getattr(owner, "id", None):
        raise DavProvisioningError("Owner non valido per account DAV esterno.")

    base = _build_external_base_username(owner, username_hint or label or "guest")
    issued_password = (raw_password or "").strip() or _generate_app_password()
    if not issued_password:
        raise DavProvisioningError("Password DAV esterna non valida.")

    with transaction.atomic():
        account = DavExternalAccount(
            owner=owner,
            label=(label or "").strip()[:120],
            dav_username=_next_available_username(base),
            password_hash=_hash_password(issued_password),
            is_active=True,
            password_rotated_at=timezone.now(),
        )
        account.save()
        sync_radicale_users_file()
    return account, issued_password


def rotate_external_dav_password(*, owner, external_account: DavExternalAccount, raw_password: str | None = None) -> str:
    if not owner or not getattr(owner, "id", None):
        raise DavProvisioningError("Owner non valido.")
    if external_account.owner_id != owner.id:
        raise DavProvisioningError("Account DAV esterno non appartenente all'owner.")

    issued_password = (raw_password or "").strip() or _generate_app_password()
    if not issued_password:
        raise DavProvisioningError("Password DAV esterna non valida.")

    with transaction.atomic():
        locked = DavExternalAccount.objects.select_for_update().get(id=external_account.id, owner=owner)
        locked.password_hash = _hash_password(issued_password)
        locked.password_rotated_at = timezone.now()
        locked.is_active = True
        locked.save(update_fields=["password_hash", "password_rotated_at", "is_active", "updated_at"])
        sync_radicale_users_file()
    return issued_password


def set_external_dav_account_active(*, owner, external_account: DavExternalAccount, is_active: bool) -> None:
    if not owner or not getattr(owner, "id", None):
        raise DavProvisioningError("Owner non valido.")
    if external_account.owner_id != owner.id:
        raise DavProvisioningError("Account DAV esterno non appartenente all'owner.")

    external_account.is_active = bool(is_active)
    external_account.save(update_fields=["is_active", "updated_at"])
    sync_radicale_users_file()


def create_managed_calendar(*, owner, principal: str, calendar_slug: str, display_name: str = "") -> DavManagedCalendar:
    if not getattr(settings, "CALDAV_ENABLED", False):
        raise DavProvisioningError("Integrazione CalDAV disabilitata.")
    if not owner or not getattr(owner, "id", None):
        raise DavProvisioningError("Owner non valido per calendario DAV.")

    principal_value = _normalize_dav_principal(principal)
    slug_value = _normalize_dav_collection_slug(calendar_slug)
    display_name_value = (display_name or "").strip()[:120]

    ensure_calendar_collection(
        principal=principal_value,
        calendar_slug=slug_value,
        display_name=display_name_value,
    )

    calendar, _ = DavManagedCalendar.objects.update_or_create(
        owner=owner,
        principal=principal_value,
        calendar_slug=slug_value,
        defaults={
            "display_name": display_name_value,
            "is_active": True,
        },
    )
    sync_radicale_users_file()
    return calendar


def set_managed_calendar_active(*, owner, calendar: DavManagedCalendar, is_active: bool) -> None:
    if calendar.owner_id != owner.id:
        raise DavProvisioningError("Calendario DAV non appartenente all'owner.")
    calendar.is_active = bool(is_active)
    calendar.save(update_fields=["is_active", "updated_at"])
    sync_radicale_users_file()


def grant_external_access_to_calendar(
    *,
    owner,
    external_account: DavExternalAccount,
    calendar: DavManagedCalendar,
    access_level: str,
) -> DavCalendarGrant:
    if external_account.owner_id != owner.id:
        raise DavProvisioningError("Account DAV esterno non appartenente all'owner.")
    if calendar.owner_id != owner.id:
        raise DavProvisioningError("Calendario DAV non appartenente all'owner.")
    if access_level not in {DavCalendarGrant.ACCESS_READONLY, DavCalendarGrant.ACCESS_READWRITE}:
        raise DavProvisioningError("Livello accesso DAV non valido.")

    grant, _ = DavCalendarGrant.objects.update_or_create(
        owner=owner,
        external_account=external_account,
        calendar=calendar,
        defaults={
            "access_level": access_level,
            "is_active": True,
        },
    )
    sync_radicale_users_file()
    return grant


def set_calendar_grant_active(*, owner, grant: DavCalendarGrant, is_active: bool) -> None:
    if grant.owner_id != owner.id:
        raise DavProvisioningError("Grant DAV non appartenente all'owner.")
    grant.is_active = bool(is_active)
    grant.save(update_fields=["is_active", "updated_at"])
    sync_radicale_users_file()
