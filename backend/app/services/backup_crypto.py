"""Backup file encryption (#149).

v2 file layout (0.1.10+)::

    b"IRDB" | 0x02 | key fingerprint (8 bytes) | nonce (12) | AES-256-GCM ciphertext + tag

The 13-byte header is authenticated as AES-GCM associated data, so it can't
be altered without the decryption failing. The fingerprint (first 8 bytes of
SHA-256 of the key) says which key a file needs, so restore can name the
missing key instead of failing with a bare InvalidTag.

v1 files (before 0.1.10) have no header: ``nonce (12) | ciphertext + tag``,
encrypted with a key derived from SECRET_KEY. They still decrypt, with the
current SECRET_KEY or any of BACKUP_LEGACY_SECRET_KEYS.

The key is BACKUP_ENCRYPTION_KEY. When it isn't set, the SECRET_KEY-derived
key is used (and logged as a warning), so an upgrade never breaks backups.
"""
import functools
import hashlib
import logging
import secrets
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import settings

logger = logging.getLogger(__name__)

MAGIC = b"IRDB"
FORMAT_V2 = 0x02
FINGERPRINT_LEN = 8
HEADER_LEN = len(MAGIC) + 1 + FINGERPRINT_LEN  # 13
NONCE_LEN = 12

KEY_SOURCE_DEDICATED = "dedicated"
KEY_SOURCE_FALLBACK = "secret_key_fallback"


class BackupKeyError(Exception):
    """The backup can't be decrypted with any configured key."""


@dataclass(frozen=True)
class BackupHeader:
    version: int  # 1 = legacy (no header), 2 = current
    fingerprint: str | None  # hex, None for v1


def derive_secret_key_backup_key(secret_key: str) -> bytes:
    """The pre-0.1.10 backup key: HKDF-SHA256 over SECRET_KEY."""
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"irdoc-backup-v1",
        info=b"backup-encryption-key",
    ).derive(secret_key.encode())


def fingerprint(key: bytes) -> str:
    return hashlib.sha256(key).digest()[:FINGERPRINT_LEN].hex()


@functools.lru_cache(maxsize=None)
def _active() -> tuple[bytes, str]:
    if settings.BACKUP_ENCRYPTION_KEY:
        return bytes.fromhex(settings.BACKUP_ENCRYPTION_KEY), KEY_SOURCE_DEDICATED
    logger.warning(
        "BACKUP_ENCRYPTION_KEY is not set: backups are encrypted with a key derived from "
        "SECRET_KEY, so rotating SECRET_KEY will make them undecryptable. Set "
        "BACKUP_ENCRYPTION_KEY (openssl rand -hex 32) and run `python -m app.cli.backup rekey`."
    )
    return derive_secret_key_backup_key(settings.SECRET_KEY), KEY_SOURCE_FALLBACK


def active_key() -> bytes:
    return _active()[0]


def active_key_source() -> str:
    return _active()[1]


def active_fingerprint() -> str:
    return fingerprint(active_key())


@functools.lru_cache(maxsize=None)
def _candidate_keys() -> tuple[bytes, ...]:
    """Every key a backup may have been made with, active key first, no duplicates."""
    keys = [active_key(), derive_secret_key_backup_key(settings.SECRET_KEY)]
    keys += [derive_secret_key_backup_key(k) for k in settings.BACKUP_LEGACY_SECRET_KEYS]
    seen: dict[bytes, None] = {}
    for k in keys:
        seen.setdefault(k, None)
    return tuple(seen)


def clear_cache() -> None:
    """Forget cached keys (tests, or after settings change)."""
    _active.cache_clear()
    _candidate_keys.cache_clear()


def parse_header(blob: bytes) -> BackupHeader:
    if blob[: len(MAGIC)] == MAGIC and len(blob) >= HEADER_LEN:
        version = blob[len(MAGIC)]
        if version != FORMAT_V2:
            raise BackupKeyError(f"Unsupported backup format version {version}")
        return BackupHeader(version=2, fingerprint=blob[len(MAGIC) + 1 : HEADER_LEN].hex())
    return BackupHeader(version=1, fingerprint=None)


def read_header(path: Path) -> BackupHeader:
    with open(path, "rb") as f:
        return parse_header(f.read(HEADER_LEN))


def encrypt(plaintext: bytes, key: bytes | None = None) -> bytes:
    """Encrypt in the v2 format with ``key`` (default: the active key)."""
    key = key or active_key()
    header = MAGIC + bytes([FORMAT_V2]) + bytes.fromhex(fingerprint(key))
    nonce = secrets.token_bytes(NONCE_LEN)
    return header + nonce + AESGCM(key).encrypt(nonce, plaintext, header)


def decrypt(blob: bytes) -> bytes:
    header = parse_header(blob)
    if header.version == 2:
        key = next((k for k in _candidate_keys() if fingerprint(k) == header.fingerprint), None)
        if key is None:
            raise BackupKeyError(
                f"This backup was made with key {header.fingerprint}, which isn't configured. "
                f"Set BACKUP_ENCRYPTION_KEY to that key (active key: {active_fingerprint()})."
            )
        body = blob[HEADER_LEN:]
        try:
            return AESGCM(key).decrypt(body[:NONCE_LEN], body[NONCE_LEN:], blob[:HEADER_LEN])
        except InvalidTag as exc:
            raise BackupKeyError("Backup is corrupted or was tampered with (authentication failed)") from exc

    for key in _candidate_keys():
        try:
            return AESGCM(key).decrypt(blob[:NONCE_LEN], blob[NONCE_LEN:], None)
        except InvalidTag:
            continue
    raise BackupKeyError(
        "Legacy backup (made before 0.1.10) could not be decrypted with the current SECRET_KEY "
        "or any BACKUP_LEGACY_SECRET_KEYS. Add the SECRET_KEY that was in use when it was made "
        "to BACKUP_LEGACY_SECRET_KEYS."
    )


def needs_rekey(header: BackupHeader) -> bool:
    """Not yet encrypted with the active key."""
    return header.version != 2 or header.fingerprint != active_fingerprint()
