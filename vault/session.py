import os
import time


SESSION_VERIFIED_AT = "vault_totp_verified_at"


def _timeout_seconds() -> int:
    raw = (os.getenv("VAULT_SESSION_TIMEOUT_SECONDS") or "600").strip()
    try:
        return max(int(raw), 60)
    except ValueError:
        return 600


def mark_verified(request) -> None:
    request.session[SESSION_VERIFIED_AT] = int(time.time())


def clear_verified(request) -> None:
    request.session.pop(SESSION_VERIFIED_AT, None)


def is_verified(request) -> bool:
    stamp = request.session.get(SESSION_VERIFIED_AT)
    if not stamp:
        return False
    try:
        verified_at = int(stamp)
    except (TypeError, ValueError):
        return False
    return (int(time.time()) - verified_at) <= _timeout_seconds()
