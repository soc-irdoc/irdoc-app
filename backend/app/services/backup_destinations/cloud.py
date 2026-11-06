"""The Admin > Storage backend as a backup destination."""
import types
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage import StorageConfig
from app.services.backup_destinations.base import RemoteBackupError, TestResult

_PREFIX = "backups/"


async def load_cloud_backend(db: AsyncSession):
    """The configured cloud storage backend.

    Uses the active StorageConfig row. Fails loudly instead of silently
    "succeeding" when nothing usable is configured, and refuses the local
    backend: backups would land in the storage folder and be archived into
    every later backup.
    """
    from app.services.integration_service import decrypt_config
    from app.services.storage.resolver import get_storage_backend_from_config

    rows = (await db.execute(
        select(StorageConfig).order_by(StorageConfig.is_active.desc())
    )).scalars().all()
    row = next((r for r in rows if r.is_active), rows[0] if rows else None)
    if row is None:
        raise RemoteBackupError("Cloud destination selected, but no cloud storage is configured (Admin > Storage)")
    if row.backend == "local":
        raise RemoteBackupError("Cloud destination needs a cloud storage backend; Admin > Storage is set to local")
    return get_storage_backend_from_config(
        types.SimpleNamespace(backend=row.backend, config=decrypt_config(row.config))
    )


class CloudDestination:
    kind = "cloud"

    def __init__(self, backend):
        self.backend = backend

    async def upload(self, local_path: Path, name: str) -> None:
        await self.backend.store(local_path.read_bytes(), _PREFIX + name)

    async def list_backups(self) -> list[str] | None:
        return None  # StorageBackend can't list; retention uses the backup records

    async def delete(self, name: str) -> None:
        await self.backend.delete(_PREFIX + name)

    async def test(self) -> TestResult:
        ok = await self.backend.test_connection()
        return TestResult(ok=bool(ok), error=None if ok else "Storage backend test failed")
