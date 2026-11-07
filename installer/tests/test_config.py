import os
import platform
import stat
from pathlib import Path
import pytest
from installer.core.config import generate_secrets, assemble_env, read_existing_env, write_env


def test_generate_secrets_returns_all_keys():
    s = generate_secrets()
    assert set(s.keys()) == {"db_password", "redis_password", "secret_key", "backup_encryption_key"}


def test_backup_key_is_64_hex_chars():
    key = generate_secrets()["backup_encryption_key"]
    assert len(key) == 64 and bytes.fromhex(key)


def test_generate_secrets_are_strong():
    s = generate_secrets()
    assert len(s["db_password"]) >= 24
    assert len(s["redis_password"]) >= 24
    assert len(s["secret_key"]) >= 32


def test_generate_secrets_differ_each_call():
    a, b = generate_secrets(), generate_secrets()
    assert a["db_password"] != b["db_password"]


def test_assemble_env_contains_required_keys():
    state = {
        "db_password": "dbpass",
        "redis_password": "redispass",
        "secret_key": "secretkey",
        "base_url": "https://irdoc.example.com",
        "access_token_expire_minutes": 15,
        "refresh_token_expire_days": 30,
        "license_key": "",
        "version": "1.2.0",
    }
    content = assemble_env(state)
    assert "DB_PASSWORD=dbpass" in content
    assert "REDIS_PASSWORD=redispass" in content
    assert "SECRET_KEY=secretkey" in content
    assert "BASE_URL=https://irdoc.example.com" in content
    assert "DATABASE_URL=postgresql+asyncpg://irp:dbpass@irdoc-db/irp" in content
    assert "REDIS_URL=redis://:redispass@irdoc-redis:6379/0" in content
    assert "ALLOW_REGISTRATION=false" in content
    assert "VERSION=1.2.0" in content


def test_assemble_env_license_key_optional():
    state = {
        "db_password": "x", "redis_password": "y", "secret_key": "z",
        "base_url": "https://x.com", "access_token_expire_minutes": 15,
        "refresh_token_expire_days": 30, "license_key": "MY-KEY",
    }
    content = assemble_env(state)
    assert "LICENSE_KEY=MY-KEY" in content


def test_read_existing_env(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DB_PASSWORD=hello\nREDIS_PASSWORD=world\n# comment\n")
    result = read_existing_env(env_file)
    assert result["DB_PASSWORD"] == "hello"
    assert result["REDIS_PASSWORD"] == "world"
    assert "# comment" not in result


def test_assemble_env_omits_cors_origins_when_not_set():
    state = {
        "db_password": "x", "redis_password": "y", "secret_key": "z",
        "base_url": "https://x.com", "access_token_expire_minutes": 15,
        "refresh_token_expire_days": 30, "license_key": "",
    }
    content = assemble_env(state)
    assert "CORS_ORIGINS" not in content


def test_assemble_env_includes_base_url_and_extra_cors_origins():
    state = {
        "db_password": "x", "redis_password": "y", "secret_key": "z",
        "base_url": "https://irdoc.example.com", "access_token_expire_minutes": 15,
        "refresh_token_expire_days": 30, "license_key": "",
        "cors_origins": "http://localhost:3000, http://192.168.1.50",
    }
    content = assemble_env(state)
    assert "CORS_ORIGINS=https://irdoc.example.com,http://localhost:3000, http://192.168.1.50" in content


def test_write_env_creates_file_with_restricted_permissions(tmp_path):
    path = tmp_path / ".env"
    write_env(path, "KEY=value\n")
    assert path.read_text() == "KEY=value\n"
    # Windows does not support POSIX chmod; skip the permission check there.
    if platform.system() != "Windows":
        mode = stat.S_IMODE(os.stat(path).st_mode)
        assert mode == 0o600


# ── Backup encryption key (#149) ────────────────────────────────────────────

_BASE = {
    "db_password": "x", "redis_password": "y", "secret_key": "z",
    "base_url": "https://x.com", "access_token_expire_minutes": 15,
    "refresh_token_expire_days": 30, "license_key": "",
}


def test_assemble_env_writes_the_given_backup_key():
    content = assemble_env({**_BASE, "backup_encryption_key": "ab" * 32})
    assert f"BACKUP_ENCRYPTION_KEY={'ab' * 32}" in content


def test_assemble_env_never_writes_an_empty_backup_key():
    content = assemble_env(_BASE)
    line = next(l for l in content.splitlines() if l.startswith("BACKUP_ENCRYPTION_KEY="))
    assert len(line.split("=", 1)[1]) == 64


def test_assemble_env_carries_legacy_secret_keys_over():
    content = assemble_env({**_BASE, "backup_encryption_key": "ab" * 32, "backup_legacy_secret_keys": "old1,old2"})
    assert "BACKUP_LEGACY_SECRET_KEYS=old1,old2" in content
    assert "BACKUP_LEGACY_SECRET_KEYS" not in assemble_env(_BASE)
