# backend/app/services/mfa_service.py
import base64
import secrets

import pyotp
from argon2 import PasswordHasher
from cryptography.fernet import Fernet

from app.core.config import get_settings

_ph = PasswordHasher()


def _get_fernet() -> Fernet:
    settings = get_settings()
    # Derive a 32-byte key from SECRET_KEY (hex string, first 32 bytes)
    raw = settings.SECRET_KEY.encode()[:32].ljust(32, b"\x00")
    return Fernet(base64.urlsafe_b64encode(raw))


def generate_totp_secret(email: str) -> tuple[str, str]:
    """Return (raw_base32_secret, otpauth_uri)."""
    secret = pyotp.random_base32()
    uri = pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="IRDoc")
    return secret, uri


def verify_totp(encrypted_secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code. Allows ±1 step (30s) clock skew."""
    secret = decrypt_secret(encrypted_secret)
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def generate_backup_codes() -> tuple[list[str], list[str]]:
    """Return (plain_codes, argon2id_hashed_codes). 10 codes, format 'xxxx-xxxx'."""
    plain = [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(10)]
    hashed = [_ph.hash(code) for code in plain]
    return plain, hashed


def verify_backup_code(user: object, code: str) -> bool:
    """Check code against user.backup_codes. Removes matched code. Returns True if valid."""
    if not user.backup_codes:
        return False
    for i, hashed in enumerate(list(user.backup_codes)):
        try:
            if _ph.verify(hashed, code):
                codes = list(user.backup_codes)
                codes.pop(i)
                user.backup_codes = codes
                return True
        except Exception:
            continue
    return False


def encrypt_secret(secret: str) -> str:
    return _get_fernet().encrypt(secret.encode()).decode()


def decrypt_secret(blob: str) -> str:
    return _get_fernet().decrypt(blob.encode()).decode()
