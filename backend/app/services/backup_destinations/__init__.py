"""Backup destinations (#151): cloud (Admin > Storage), SFTP and SMB."""
from dataclasses import fields

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backup import BackupRemoteConfig
from app.services.backup_destinations.base import (
    BACKUP_NAME_RE,
    BackupDestination,
    RemoteBackupError,
    TestResult,
    expired_backups,
)
from app.services.backup_destinations.cloud import CloudDestination, load_cloud_backend
from app.services.backup_destinations.sftp import SFTPDestination, SFTPSettings
from app.services.backup_destinations.smb import SMBDestination, SMBSettings

REMOTE_KINDS = ("sftp", "smb")
DESTINATIONS = ("local", "cloud", *REMOTE_KINDS)

# Never returned by the API, only "set / not set".
SECRET_FIELDS: dict[str, tuple[str, ...]] = {
    "sftp": ("password", "private_key", "passphrase"),
    "smb": ("password",),
}
_SETTINGS = {"sftp": SFTPSettings, "smb": SMBSettings}

__all__ = [
    "BACKUP_NAME_RE", "BackupDestination", "DESTINATIONS", "REMOTE_KINDS", "RemoteBackupError",
    "SECRET_FIELDS", "TestResult", "build_destination", "expired_backups", "get_remote_config",
    "resolve_destination",
]


def build_destination(kind: str, config: dict, host_key: str | None = None):
    """A destination from plain (decrypted) settings."""
    cls = _SETTINGS.get(kind)
    if cls is None:
        raise RemoteBackupError(f"Unknown backup destination '{kind}'")
    known = {f.name for f in fields(cls)}
    try:
        settings = cls(**{k: v for k, v in config.items() if k in known})
    except TypeError as exc:
        raise RemoteBackupError(f"Incomplete {kind.upper()} settings: {exc}") from exc
    if kind == "sftp":
        return SFTPDestination(settings, host_key)
    return SMBDestination(settings)


async def get_remote_config(db: AsyncSession, kind: str) -> BackupRemoteConfig | None:
    return (await db.execute(
        select(BackupRemoteConfig).where(BackupRemoteConfig.kind == kind)
    )).scalars().first()


async def resolve_destination(db: AsyncSession, kind: str):
    """The configured destination for ``kind`` ("cloud", "sftp" or "smb")."""
    if kind == "cloud":
        return CloudDestination(await load_cloud_backend(db))
    if kind not in REMOTE_KINDS:
        raise RemoteBackupError(f"Unknown backup destination '{kind}'")
    row = await get_remote_config(db, kind)
    if row is None:
        raise RemoteBackupError(f"{kind.upper()} destination selected, but it is not configured")
    from app.services.integration_service import decrypt_config
    return build_destination(kind, decrypt_config(row.config or {}), row.host_key)
