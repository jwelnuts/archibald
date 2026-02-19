import os

import pyotp


def issuer_name() -> str:
    return (os.getenv("VAULT_TOTP_ISSUER") or "MIO Vault").strip()


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(username: str, secret: str) -> str:
    totp = pyotp.TOTP(secret)
    account_name = (username or "user").strip()
    return totp.provisioning_uri(name=account_name, issuer_name=issuer_name())


def verify_code(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return bool(totp.verify(str(code).strip(), valid_window=1))
