# backend/app/services/mfa_service.py
import base64
import hmac
import secrets
import time as _time

import pyotp
from argon2.exceptions import Argon2Error, VerifyMismatchError
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import get_settings
from app.core.security import ph


def _get_fernet() -> Fernet:
    settings = get_settings()
    kdf = HKDF(algorithm=SHA256(), length=32, salt=None, info=b"irdoc-mfa-secret")
    key = kdf.derive(settings.SECRET_KEY.encode())
    return Fernet(base64.urlsafe_b64encode(key))


def generate_totp_secret(email: str) -> tuple[str, str]:
    """Return (raw_base32_secret, otpauth_uri)."""
    secret = pyotp.random_base32()
    uri = pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="IRDoc")
    return secret, uri


def verify_totp(
    encrypted_secret: str,
    code: str,
    last_counter: int | None = None,
) -> tuple[bool, int | None]:
    """Verify a 6-digit TOTP code with replay protection.

    Allows ±1 step (30 s) clock skew. Returns (is_valid, counter_used).
    Pass last_counter to reject a code whose time-step has already been used.
    """
    secret = decrypt_secret(encrypted_secret)
    totp = pyotp.TOTP(secret)
    now = _time.time()
    base = int(now / 30)

    for offset in (-1, 0, 1):
        if hmac.compare_digest(totp.at(now, offset), str(code)):
            candidate = base + offset
            if last_counter is not None and candidate <= last_counter:
                return False, None  # replay detected
            return True, candidate

    return False, None


def generate_backup_codes() -> tuple[list[str], list[str]]:
    """Return (plain_codes, argon2id_hashed_codes). 10 codes, format 'xxxx-xxxx'."""
    plain = [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(10)]
    hashed = [ph.hash(code) for code in plain]
    return plain, hashed


def verify_backup_code(user: object, code: str) -> bool:
    """Check code against user.backup_codes. Removes matched code. Returns True if valid."""
    if not user.backup_codes:
        return False
    for i, hashed in enumerate(list(user.backup_codes)):
        try:
            if ph.verify(hashed, code):
                codes = list(user.backup_codes)
                codes.pop(i)
                user.backup_codes = codes
                return True
        except (VerifyMismatchError, Argon2Error):
            continue
    return False


def encrypt_secret(secret: str) -> str:
    return _get_fernet().encrypt(secret.encode()).decode()


def decrypt_secret(blob: str) -> str:
    return _get_fernet().decrypt(blob.encode()).decode()
