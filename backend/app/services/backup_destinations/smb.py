"""SMB backup destination (#151), using smbprotocol's smbclient.

SMB 3 only. Encryption is required by default; an admin can turn it off for
old NAS devices, and the UI warns when they do. smbclient is synchronous, so
every operation runs in a worker thread with its own connection cache.
"""
import asyncio
import secrets
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.services.backup_destinations.base import PART_SUFFIX, RemoteBackupError, TestResult

CONNECT_TIMEOUT = 20
_CHUNK = 1024 * 1024


@dataclass
class SMBSettings:
    server: str
    share: str
    path: str = ""
    username: str = ""
    password: str | None = None
    domain: str | None = None
    port: int = 445
    require_encryption: bool = True


def _libs():
    try:
        import smbclient
        from smbprotocol.connection import Dialects
    except ImportError as exc:  # pragma: no cover - dependency is in requirements.txt
        raise RemoteBackupError("SMB support is not installed (smbprotocol missing)") from exc
    return smbclient, Dialects


class SMBDestination:
    kind = "smb"

    def __init__(self, settings: SMBSettings):
        self.s = settings

    def _unc(self, name: str | None = None) -> str:
        parts = [f"\\\\{self.s.server}", self.s.share]
        parts += [p for p in self.s.path.replace("/", "\\").split("\\") if p]
        if name:
            parts.append(name)
        return "\\".join(parts)

    def _session(self, cache: dict):
        smbclient, dialects = _libs()
        user = f"{self.s.domain}\\{self.s.username}" if self.s.domain else self.s.username
        try:
            session = smbclient.register_session(
                self.s.server,
                username=user or None,
                password=self.s.password or None,
                port=self.s.port,
                encrypt=self.s.require_encryption,
                connection_timeout=CONNECT_TIMEOUT,
                connection_cache=cache,
            )
        except Exception as exc:  # smbprotocol raises many unrelated types
            raise RemoteBackupError(f"SMB connection to {self.s.server}:{self.s.port} failed: {exc}") from exc
        dialect = session.connection.dialect
        if dialect < dialects.SMB_3_0_0:
            raise RemoteBackupError(
                f"{self.s.server} negotiated SMB dialect {dialect:#06x}; SMB 3 or newer is required"
            )
        return smbclient

    def _run(self, fn):
        def wrapper():
            cache: dict = {}
            try:
                return fn(self._session(cache), cache)
            except RemoteBackupError:
                raise
            except Exception as exc:
                raise RemoteBackupError(f"SMB operation on {self._unc()} failed: {exc}") from exc
            finally:
                smbclient, _ = _libs()
                try:
                    smbclient.reset_connection_cache(connection_cache=cache)
                except Exception:  # noqa: BLE001 - best-effort cleanup
                    pass
        return asyncio.to_thread(wrapper)

    async def upload(self, local_path: Path, name: str) -> None:
        part, final = self._unc(name + PART_SUFFIX), self._unc(name)

        def op(smbclient, cache):
            with open(local_path, "rb") as src, smbclient.open_file(part, mode="wb", connection_cache=cache) as dst:
                shutil.copyfileobj(src, dst, _CHUNK)
            smbclient.replace(part, final, connection_cache=cache)
        await self._run(op)

    async def list_backups(self) -> list[str] | None:
        return await self._run(lambda smbclient, cache: list(smbclient.listdir(self._unc(), connection_cache=cache)))

    async def delete(self, name: str) -> None:
        await self._run(lambda smbclient, cache: smbclient.remove(self._unc(name), connection_cache=cache))

    async def test(self) -> TestResult:
        probe = self._unc(f".irdoc_test_{secrets.token_hex(6)}")

        def op(smbclient, cache):
            with smbclient.open_file(probe, mode="wb", connection_cache=cache) as f:
                f.write(b"irdoc backup destination test\n")
            smbclient.remove(probe, connection_cache=cache)
        try:
            await self._run(op)
        except RemoteBackupError as exc:
            return TestResult(ok=False, error=str(exc))
        return TestResult(ok=True, details={"encryption": self.s.require_encryption})
