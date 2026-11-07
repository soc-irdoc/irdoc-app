"""Backup encryption with a dedicated key (#149)."""
import secrets

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.services import backup_crypto as bc

KEY_A = "a" * 64
KEY_B = "b" * 64
OLD_SECRET = "old-secret-key-that-was-rotated-away-0123456789"


@pytest.fixture
def keys(monkeypatch):
    """Set backup key settings and reset the module's caches around each test."""
    def set_keys(backup_key: str = "", legacy: list[str] | None = None):
        monkeypatch.setattr(settings, "BACKUP_ENCRYPTION_KEY", backup_key)
        monkeypatch.setattr(settings, "BACKUP_LEGACY_SECRET_KEYS", legacy or [])
        bc.clear_cache()
    yield set_keys
    bc.clear_cache()


def legacy_blob(secret_key: str, plaintext: bytes) -> bytes:
    """A backup as written before 0.1.10: nonce || ciphertext, no header."""
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(bc.derive_secret_key_backup_key(secret_key)).encrypt(nonce, plaintext, None)


def test_v2_round_trip_with_the_dedicated_key(keys):
    keys(KEY_A)
    blob = bc.encrypt(b"bundle")

    assert blob[:4] == b"IRDB" and blob[4] == 2
    header = bc.parse_header(blob)
    assert header.fingerprint == bc.fingerprint(bytes.fromhex(KEY_A)) == bc.active_fingerprint()
    assert bc.active_key_source() == bc.KEY_SOURCE_DEDICATED
    assert bc.decrypt(blob) == b"bundle"


def test_tampered_header_fails_authentication(keys):
    keys(KEY_A)
    blob = bytearray(bc.encrypt(b"bundle"))
    blob[4] = 2  # unchanged version, but flip a ciphertext byte and the header separately
    tampered_body = bytes(blob[:-1]) + bytes([blob[-1] ^ 1])
    with pytest.raises(bc.BackupKeyError, match="tampered"):
        bc.decrypt(tampered_body)


def test_header_is_bound_as_associated_data(keys):
    keys(KEY_A)
    blob = bc.encrypt(b"bundle")
    # Re-label the file as made with the same key but strip the AAD binding:
    # decrypting the body without the header as AAD must fail.
    body = blob[bc.HEADER_LEN:]
    with pytest.raises(Exception):
        AESGCM(bytes.fromhex(KEY_A)).decrypt(body[:12], body[12:], None)


def test_legacy_backups_decrypt_with_the_current_secret_key(keys):
    keys(KEY_A)
    blob = legacy_blob(settings.SECRET_KEY, b"old bundle")

    assert bc.parse_header(blob).version == 1
    assert bc.decrypt(blob) == b"old bundle"


def test_legacy_backups_from_a_rotated_secret_key(keys):
    blob = legacy_blob(OLD_SECRET, b"older bundle")

    keys(KEY_A)
    with pytest.raises(bc.BackupKeyError, match="BACKUP_LEGACY_SECRET_KEYS"):
        bc.decrypt(blob)

    keys(KEY_A, legacy=[OLD_SECRET])
    assert bc.decrypt(blob) == b"older bundle"


def test_wrong_key_error_names_the_fingerprint(keys):
    keys(KEY_A)
    blob = bc.encrypt(b"bundle")
    fp_a = bc.active_fingerprint()

    keys(KEY_B)
    with pytest.raises(bc.BackupKeyError) as err:
        bc.decrypt(blob)
    assert fp_a in str(err.value)
    assert "isn't configured" in str(err.value)


def test_falls_back_to_the_secret_key_derived_key_when_unset(keys, caplog):
    keys("")
    blob = bc.encrypt(b"bundle")

    assert bc.active_key_source() == bc.KEY_SOURCE_FALLBACK
    assert bc.active_key() == bc.derive_secret_key_backup_key(settings.SECRET_KEY)
    assert bc.decrypt(blob) == b"bundle"
    assert "BACKUP_ENCRYPTION_KEY is not set" in caplog.text


def test_needs_rekey(keys):
    keys(KEY_A)
    assert bc.needs_rekey(bc.parse_header(legacy_blob(settings.SECRET_KEY, b"x")))
    assert not bc.needs_rekey(bc.parse_header(bc.encrypt(b"x")))
    keys(KEY_B)
    assert bc.needs_rekey(bc.parse_header(bc.encrypt(b"x", key=bytes.fromhex(KEY_A))))


@pytest.mark.parametrize("value", ["abc", "z" * 64, "a" * 62])
def test_settings_reject_a_malformed_backup_key(monkeypatch, value):
    monkeypatch.setenv("SECRET_KEY", "s" * 40)
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", value)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_accept_empty_backup_key_and_parse_legacy_list(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "s" * 40)
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "")
    monkeypatch.setenv("BACKUP_LEGACY_SECRET_KEYS", " one , two ,")
    s = Settings(_env_file=None)
    assert s.BACKUP_ENCRYPTION_KEY == ""
    assert s.BACKUP_LEGACY_SECRET_KEYS == ["one", "two"]
