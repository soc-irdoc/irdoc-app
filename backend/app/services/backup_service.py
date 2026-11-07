"""
Backup service - core logic for the built-in backup system.

Produces an encrypted, self-contained backup bundle containing:
  - a gzip-compressed PostgreSQL dump (via pg_dump)
  - a tar archive of the storage directory
  - a JSON manifest

The bundle is AES-256-GCM encrypted with BACKUP_ENCRYPTION_KEY (see
backup_crypto; falls back to a key derived from SECRET_KEY) and
written to /app/backups. Optionally uploaded to the org's configured cloud storage.
"""
import asyncio
import gzip
import io
import json
import logging
import os
import re
import tarfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.backup import BackupConfig, BackupRecord
from app.services import backup_crypto

logger = logging.getLogger(__name__)

BACKUP_DIR = Path("/app/backups")
SCHEMA_VERSION = "011"
_FILENAME_RE = re.compile(r"^irdoc_backup_[0-9A-Za-z]+\.enc$")

_CONFIG_FIELDS = {"enabled", "schedule", "retention_days", "destination"}


class RemoteUploadError(Exception):
    """The local backup was written, but copying it to the remote failed."""


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
def _encrypt(plaintext: bytes) -> bytes:
    return backup_crypto.encrypt(plaintext)


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
# Remote destinations (cloud / SFTP / SMB, #151)
# ---------------------------------------------------------------------------
async def upload_remote_copy(db: AsyncSession, destination: str, path: Path) -> None:
    """(Re)upload a local backup file to its remote destination."""
    from app.services import backup_destinations
    dest = await backup_destinations.resolve_destination(db, destination)
    await dest.upload(path, path.name)


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------
async def _run_remote_retention(db: AsyncSession, config: BackupConfig, cutoff: datetime,
                                old_records: list[BackupRecord]) -> None:
    """Delete expired backups on the remote. Only exact irdoc_backup_*.enc names are touched."""
    from app.services import backup_destinations
    try:
        dest = await backup_destinations.resolve_destination(db, config.destination)
        names = await dest.list_backups()
        if names is None:  # cloud can't list: go by the records
            names = [r.filename for r in old_records if r.destination == config.destination]
        for name in backup_destinations.expired_backups(names, cutoff):
            try:
                await dest.delete(name)
            except Exception:  # noqa: BLE001 - retention is best effort
                logger.warning("Backup retention: could not delete remote %s", name, exc_info=True)
    except Exception:  # noqa: BLE001 - never fail a backup because of retention
        logger.warning("Backup retention on %s failed", config.destination, exc_info=True)


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

    old_records = list((await db.execute(
        select(BackupRecord).where(BackupRecord.created_at < cutoff)
    )).scalars().all())

    if config.destination != "local":
        await _run_remote_retention(db, config, cutoff, old_records)

    for record in old_records:
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
        key_fp = backup_crypto.active_fingerprint()
        manifest["format_version"] = backup_crypto.FORMAT_V2
        manifest["key_fingerprint"] = key_fp

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        enc_path = BACKUP_DIR / filename
        # Write-then-rename so a crash never leaves a half-written backup.
        part_path = enc_path.with_name(filename + ".part")
        part_path.write_bytes(encrypted)
        os.replace(part_path, enc_path)
        enc_path.with_suffix(".json").write_text(json.dumps(manifest, indent=2))

        # The local copy is always written first and kept (#151). Upload BEFORE
        # committing the success record so a failed upload never leaves a
        # contradictory success record; the failure path below records the
        # remote error and keeps the local file.
        if config.destination != "local":
            try:
                await upload_remote_copy(db, config.destination, enc_path)
            except Exception as exc:
                raise RemoteUploadError(f"Remote upload ({config.destination}) failed: {exc}") from exc

        record = BackupRecord(
            filename=filename,
            size_bytes=len(encrypted),
            destination=config.destination,
            status="success",
            key_fingerprint=key_fp,
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
        # Re-fetch config after rollback - object is expired
        result = await db.execute(select(BackupConfig))
        config = result.scalars().first()
        if config is not None:
            config.last_backup_status = "failed"
            config.last_backup_error = str(exc)
        local_kept = isinstance(exc, RemoteUploadError) and (BACKUP_DIR / filename).is_file()
        failed_record = BackupRecord(
            filename=filename,
            size_bytes=(BACKUP_DIR / filename).stat().st_size if local_kept else None,
            key_fingerprint=backup_crypto.active_fingerprint() if local_kept else None,
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


def count_backups_needing_rekey() -> int:
    """Local backup files not encrypted with the active key (#149).

    Read from the file headers rather than the DB, so it is right for files
    made before key fingerprints were recorded.
    """
    if not BACKUP_DIR.is_dir():
        return 0
    count = 0
    for path in BACKUP_DIR.glob("irdoc_backup_*.enc"):
        if not _FILENAME_RE.match(path.name):
            continue
        try:
            if backup_crypto.needs_rekey(backup_crypto.read_header(path)):
                count += 1
        except (OSError, backup_crypto.BackupKeyError):
            count += 1
    return count


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
