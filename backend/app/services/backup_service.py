"""
Backup service — core logic for the built-in backup system.

Produces an encrypted, self-contained backup bundle containing:
  - a gzip-compressed PostgreSQL dump (via pg_dump)
  - a tar archive of the storage directory
  - a JSON manifest

The bundle is AES-256-GCM encrypted (key derived from SECRET_KEY via HKDF) and
written to /app/backups. Optionally uploaded to the org's configured cloud storage.
"""
import asyncio
import functools
import gzip
import io
import json
import logging
import os
import re
import secrets
import tarfile
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.backup import BackupConfig, BackupRecord
from app.models.storage import StorageConfig
from app.services.integration_service import decrypt_config
from app.services.storage.resolver import get_storage_backend_from_config

logger = logging.getLogger(__name__)

BACKUP_DIR = Path("/app/backups")
SCHEMA_VERSION = "011"
_FILENAME_RE = re.compile(r"^irdoc_backup_[0-9A-Za-z]+\.enc$")

_CONFIG_FIELDS = {"enabled", "schedule", "retention_days", "destination"}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
async def get_or_create_config(db: AsyncSession) -> BackupConfig:
    """Get the singleton BackupConfig row, creating it with defaults if absent."""
    result = await db.execute(select(BackupConfig))
    config = result.scalars().first()
    if config is None:
        config = BackupConfig(
            enabled=False,
            schedule="daily",
            retention_days=90,
            destination="local",
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


async def update_config(db: AsyncSession, **kwargs) -> BackupConfig:
    """Update the singleton config from kwargs (only known fields), commit, return it."""
    config = await get_or_create_config(db)
    for key, value in kwargs.items():
        if key in _CONFIG_FIELDS and value is not None:
            setattr(config, key, value)
    await db.commit()
    await db.refresh(config)
    return config


# ---------------------------------------------------------------------------
# Crypto helpers
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def _derive_key() -> bytes:
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"irdoc-backup-v1",
        info=b"backup-encryption-key",
    )
    return hkdf.derive(settings.SECRET_KEY.encode())


def _encrypt(plaintext: bytes) -> bytes:
    key = _derive_key()
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    return nonce + ciphertext


# ---------------------------------------------------------------------------
# Bundle building
# ---------------------------------------------------------------------------
async def _dump_database() -> bytes:
    """Run pg_dump against the configured database, returning the raw SQL bytes."""
    parsed = urlparse(settings.DATABASE_URL)
    host = parsed.hostname or "localhost"
    port = str(parsed.port or 5432)
    user = parsed.username or "postgres"
    password = parsed.password or ""
    dbname = (parsed.path or "/").lstrip("/")

    env = os.environ.copy()
    env["PGPASSWORD"] = password

    proc = await asyncio.create_subprocess_exec(
        "pg_dump", "-h", host, "-p", port, "-U", user, dbname,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError("pg_dump timed out after 300s")

    if proc.returncode != 0:
        raise RuntimeError(
            f"pg_dump failed (exit {proc.returncode}): {stderr.decode(errors='replace')[:500]}"
        )
    return stdout


def _archive_storage() -> bytes:
    """Tar the storage directory into in-memory bytes. Empty bytes if dir is missing."""
    storage_path = Path(settings.STORAGE_PATH)
    if not storage_path.exists():
        return b""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        tar.add(storage_path, arcname="storage")
    return buf.getvalue()


def _build_bundle(db_dump: bytes, storage_archive: bytes, timestamp: str) -> tuple[bytes, dict]:
    """Bundle gzip'd db dump + storage archive + manifest into a single .tar.gz."""
    db_gz = gzip.compress(db_dump)
    manifest = {
        "version": "1.0",
        "created_at": timestamp,
        "schema_version": SCHEMA_VERSION,
        "components": ["postgresql", "storage"],
        "db_size_bytes": len(db_dump),
        "storage_size_bytes": len(storage_archive),
    }
    manifest_bytes = json.dumps(manifest, indent=2).encode()

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        _add_bytes(tar, "database.sql.gz", db_gz)
        _add_bytes(tar, "storage.tar", storage_archive)
        _add_bytes(tar, "manifest.json", manifest_bytes)
    return buf.getvalue(), manifest


def _add_bytes(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


# ---------------------------------------------------------------------------
# Cloud upload / delete
# ---------------------------------------------------------------------------
async def _get_cloud_backend(db: AsyncSession):
    """Return an instantiated storage backend for the org's StorageConfig, or None."""
    result = await db.execute(select(StorageConfig))
    storage_config = result.scalars().first()
    if storage_config is None:
        return None
    decrypted_cfg = decrypt_config(storage_config.config)
    backend_obj = types.SimpleNamespace(
        backend=storage_config.backend, config=decrypted_cfg
    )
    return get_storage_backend_from_config(backend_obj)


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------
async def _run_retention(db: AsyncSession, config: BackupConfig) -> None:
    cutoff = datetime.now(UTC) - timedelta(days=config.retention_days)

    # Local files (.enc + .json sidecar)
    if BACKUP_DIR.exists():
        for enc_file in BACKUP_DIR.glob("irdoc_backup_*.enc"):
            if not _FILENAME_RE.match(enc_file.name):
                continue
            try:
                mtime = datetime.fromtimestamp(enc_file.stat().st_mtime, UTC)
            except OSError:
                continue
            if mtime < cutoff:
                enc_file.unlink(missing_ok=True)
                enc_file.with_suffix(".json").unlink(missing_ok=True)

    # Old DB records (and cloud objects for those records)
    result = await db.execute(
        select(BackupRecord).where(BackupRecord.created_at < cutoff)
    )
    old_records = result.scalars().all()

    cloud_backend = None
    if config.destination == "cloud":
        try:
            cloud_backend = await _get_cloud_backend(db)
        except Exception:
            cloud_backend = None

    for record in old_records:
        if cloud_backend is not None and record.destination == "cloud":
            try:
                await cloud_backend.delete(f"backups/{record.filename}")
            except Exception:
                pass
        await db.delete(record)
    await db.commit()


# ---------------------------------------------------------------------------
# Run backup
# ---------------------------------------------------------------------------
async def run_backup(db: AsyncSession) -> BackupRecord:
    config = await get_or_create_config(db)
    config.last_backup_status = "running"
    await db.commit()

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    filename = f"irdoc_backup_{timestamp}.enc"

    try:
        db_dump = await _dump_database()
        storage_archive = _archive_storage()
        bundle, manifest = _build_bundle(db_dump, storage_archive, timestamp)
        encrypted = _encrypt(bundle)

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        enc_path = BACKUP_DIR / filename
        enc_path.write_bytes(encrypted)
        enc_path.with_suffix(".json").write_text(json.dumps(manifest, indent=2))

        # Attempt cloud upload BEFORE committing the success record so that a
        # failed upload never produces a contradictory committed success record.
        if config.destination == "cloud":
            backend = await _get_cloud_backend(db)
            if backend is not None:
                await backend.store(encrypted, f"backups/{filename}")

        record = BackupRecord(
            filename=filename,
            size_bytes=len(encrypted),
            destination=config.destination,
            status="success",
        )
        db.add(record)

        now = datetime.now(UTC)
        config.last_backup_status = "success"
        config.last_backup_at = now
        config.last_backup_size_bytes = len(encrypted)
        config.last_backup_error = None
        await db.commit()
        await db.refresh(record)

        await _run_retention(db, config)
        return record

    except Exception as exc:
        logger.exception("Backup failed")
        await db.rollback()
        # Re-fetch config after rollback — object is expired
        result = await db.execute(select(BackupConfig))
        config = result.scalars().first()
        if config is not None:
            config.last_backup_status = "failed"
            config.last_backup_error = str(exc)
        failed_record = BackupRecord(
            filename=filename,
            size_bytes=None,
            destination=config.destination if config else "local",
            status="failed",
            error=str(exc),
        )
        db.add(failed_record)
        await db.commit()
        raise


# ---------------------------------------------------------------------------
# Records / local path
# ---------------------------------------------------------------------------
async def list_records(db: AsyncSession) -> list[BackupRecord]:
    result = await db.execute(
        select(BackupRecord).order_by(BackupRecord.created_at.desc())
    )
    return list(result.scalars().all())


def get_local_backup_path(filename: str) -> Path:
    """Resolve a local backup file path, guarding against directory traversal."""
    if not _FILENAME_RE.match(filename) or "/" in filename or "\\" in filename or ".." in filename:
        raise FileNotFoundError(f"Invalid backup filename: {filename}")
    backup_dir = os.path.realpath(str(BACKUP_DIR))
    full_path = os.path.realpath(os.path.join(backup_dir, filename))
    if not (full_path == backup_dir or full_path.startswith(backup_dir + os.sep)):
        # Belt-and-suspenders on top of the regex check above.
        raise FileNotFoundError(f"Invalid backup filename: {filename}")
    path = Path(full_path)
    if not path.is_file():
        raise FileNotFoundError(f"Backup not found: {filename}")
    return path
