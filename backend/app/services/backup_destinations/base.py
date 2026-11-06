"""Where backup files go after the local copy is written (#151)."""
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

# Only files with exactly this name are ever listed, rotated or deleted on a
# remote: nothing else in the folder is touched.
BACKUP_NAME_RE = re.compile(r"^irdoc_backup_(\d{8}T\d{6}Z)\.enc$")
PART_SUFFIX = ".part"


class RemoteBackupError(Exception):
    """A remote destination failed; the message is shown to the admin verbatim."""


@dataclass
class TestResult:
    ok: bool
    error: str | None = None
    # SFTP: the server's key is not pinned yet; the admin must confirm it.
    needs_host_key_confirmation: bool = False
    host_key: str | None = None
    host_key_fingerprint: str | None = None
    details: dict = field(default_factory=dict)


def backup_timestamp(name: str) -> datetime | None:
    """When a backup was made, from its file name (remote mtimes aren't trusted)."""
    match = BACKUP_NAME_RE.match(name)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)


def expired_backups(names: list[str], cutoff: datetime) -> list[str]:
    """Names of real backup files older than ``cutoff``; anything else is ignored."""
    out = []
    for name in names:
        ts = backup_timestamp(name)
        if ts is not None and ts < cutoff:
            out.append(name)
    return sorted(out)


class BackupDestination(Protocol):
    kind: str

    async def upload(self, local_path: Path, name: str) -> None:
        """Store ``local_path`` remotely as ``name``, atomically (no half-written file under that name)."""

    async def list_backups(self) -> list[str] | None:
        """File names in the remote folder, or None if the destination can't list (cloud)."""

    async def delete(self, name: str) -> None: ...

    async def test(self) -> TestResult: ...
