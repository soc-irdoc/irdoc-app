# backend/tests/unit/test_mfa_service.py
import pytest
import pyotp
from app.services.mfa_service import (
    generate_totp_secret,
    verify_totp,
    generate_backup_codes,
    verify_backup_code,
    encrypt_secret,
    decrypt_secret,
)


def test_generate_totp_secret_returns_valid_uri():
    secret, uri = generate_totp_secret("analyst@acme.com")
    assert len(secret) >= 16
    assert uri.startswith("otpauth://totp/")
    assert "IRDoc" in uri
    assert secret in uri


def test_verify_totp_accepts_current_code():
    secret, _ = generate_totp_secret("analyst@acme.com")
    current_code = pyotp.TOTP(secret).now()
    is_valid, _counter = verify_totp(encrypt_secret(secret), current_code)
    assert is_valid is True


def test_verify_totp_rejects_wrong_code():
    secret, _ = generate_totp_secret("analyst@acme.com")
    is_valid, counter = verify_totp(encrypt_secret(secret), "000000")
    assert is_valid is False
    assert counter is None


def test_generate_backup_codes_count_and_format():
    plain, hashed = generate_backup_codes()
    assert len(plain) == 10
    assert len(hashed) == 10
    for code in plain:
        parts = code.split("-")
        assert len(parts) == 2
        assert len(parts[0]) == 4
        assert len(parts[1]) == 4


def test_backup_codes_are_unique():
    plain, _ = generate_backup_codes()
    assert len(set(plain)) == 10


def test_verify_backup_code_accepts_valid_code():
    from types import SimpleNamespace
    plain, hashed = generate_backup_codes()
    user = SimpleNamespace(backup_codes=list(hashed))
    assert verify_backup_code(user, plain[0]) is True


def test_verify_backup_code_removes_used_code():
    from types import SimpleNamespace
    plain, hashed = generate_backup_codes()
    user = SimpleNamespace(backup_codes=list(hashed))
    verify_backup_code(user, plain[0])
    assert len(user.backup_codes) == 9


def test_verify_backup_code_is_single_use():
    from types import SimpleNamespace
    plain, hashed = generate_backup_codes()
    user = SimpleNamespace(backup_codes=list(hashed))
    verify_backup_code(user, plain[0])
    assert verify_backup_code(user, plain[0]) is False


def test_verify_backup_code_rejects_invalid():
    from types import SimpleNamespace
    _, hashed = generate_backup_codes()
    user = SimpleNamespace(backup_codes=list(hashed))
    assert verify_backup_code(user, "0000-0000") is False


def test_encrypt_decrypt_roundtrip():
    secret = "JBSWY3DPEHPK3PXP"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    assert decrypt_secret(encrypted) == secret


def test_encrypt_produces_different_ciphertext_each_time():
    secret = "JBSWY3DPEHPK3PXP"
    assert encrypt_secret(secret) != encrypt_secret(secret)
