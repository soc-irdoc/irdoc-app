"""SFTP backup destination (#151), using asyncssh.

The server's host key must be pinned: the admin confirms its fingerprint
after the first "Test connection", and every later connection refuses any
other key. There is no "accept any host key" mode.
"""
import asyncio
import posixpath
import secrets
from dataclasses import dataclass
from pathlib import Path

from app.services.backup_destinations.base import PART_SUFFIX, RemoteBackupError, TestResult

CONNECT_TIMEOUT = 20


@dataclass
class SFTPSettings:
    host: str
    port: int = 22
    username: str = ""
    remote_dir: str = "."
    auth: str = "password"  # "password" | "key"
    password: str | None = None
    private_key: str | None = None
    passphrase: str | None = None


def _asyncssh():
    try:
        import asyncssh
    except ImportError as exc:  # pragma: no cover - dependency is in requirements.txt
        raise RemoteBackupError("SFTP support is not installed (asyncssh missing)") from exc
    return asyncssh


async def fetch_host_key(host: str, port: int) -> tuple[str, str]:
    """The server's host key as (OpenSSH public key line, SHA256 fingerprint)."""
    asyncssh = _asyncssh()
    try:
        # get_server_host_key takes no timeout argument of its own.
        key = await asyncio.wait_for(asyncssh.get_server_host_key(host, port), CONNECT_TIMEOUT)
    except TimeoutError as exc:
        raise RemoteBackupError(f"Could not reach {host}:{port}: timed out after {CONNECT_TIMEOUT}s") from exc
    except (OSError, asyncssh.Error) as exc:
        raise RemoteBackupError(f"Could not reach {host}:{port}: {exc}") from exc
    if key is None:
        raise RemoteBackupError(f"{host}:{port} did not present a host key")
    return key.export_public_key("openssh").decode().strip(), key.get_fingerprint("sha256")


class SFTPDestination:
    kind = "sftp"

    def __init__(self, settings: SFTPSettings, host_key: str | None):
        self.s = settings
        self.host_key = host_key

    def _require_pin(self) -> None:
        if not self.host_key:
            raise RemoteBackupError("The SFTP server's host key is not pinned yet. Run Test connection and confirm it.")

    async def _connect(self):
        self._require_pin()
        asyncssh = _asyncssh()
        try:
            pinned = asyncssh.import_public_key(self.host_key)
        except (ValueError, asyncssh.KeyImportError) as exc:
            raise RemoteBackupError(f"The pinned host key is invalid: {exc}") from exc

        kwargs: dict = {
            "port": self.s.port,
            "username": self.s.username,
            # Only the pinned key is trusted (trusted keys, CA keys, revoked keys).
            "known_hosts": ([pinned], [], []),
            "connect_timeout": CONNECT_TIMEOUT,
            "agent_path": None,
        }
        if self.s.auth == "key":
            if not self.s.private_key:
                raise RemoteBackupError("No private key is configured")
            try:
                kwargs["client_keys"] = [asyncssh.import_private_key(self.s.private_key, self.s.passphrase or None)]
            except (ValueError, asyncssh.KeyImportError) as exc:
                raise RemoteBackupError(f"The private key could not be read: {exc}") from exc
            kwargs["password"] = None
        else:
            kwargs["password"] = self.s.password or ""
            kwargs["client_keys"] = None
        try:
            return await asyncssh.connect(self.s.host, **kwargs)
        except asyncssh.HostKeyNotVerifiable as exc:
            raise RemoteBackupError(
                f"Host key of {self.s.host}:{self.s.port} does not match the pinned key "
                f"(possible man-in-the-middle, or the server was rebuilt). Re-pin it only if you trust the change. ({exc})"
            ) from exc
        except (OSError, asyncssh.Error) as exc:
            raise RemoteBackupError(f"SFTP connection to {self.s.host}:{self.s.port} failed: {exc}") from exc

    def _path(self, name: str) -> str:
        return posixpath.join(self.s.remote_dir or ".", name)

    async def upload(self, local_path: Path, name: str) -> None:
        self._require_pin()
        asyncssh = _asyncssh()
        final, part = self._path(name), self._path(name + PART_SUFFIX)
        async with await self._connect() as conn:
            try:
                async with conn.start_sftp_client() as sftp:
                    await sftp.put(str(local_path), part)
                    try:
                        await sftp.posix_rename(part, final)
                    except asyncssh.SFTPOpUnsupported:
                        if await sftp.exists(final):
                            await sftp.remove(final)
                        await sftp.rename(part, final)
            except (OSError, asyncssh.Error) as exc:
                raise RemoteBackupError(f"SFTP upload of {name} failed: {exc}") from exc

    async def list_backups(self) -> list[str] | None:
        self._require_pin()
        asyncssh = _asyncssh()
        async with await self._connect() as conn:
            try:
                async with conn.start_sftp_client() as sftp:
                    return [str(n) for n in await sftp.listdir(self.s.remote_dir or ".")]
            except (OSError, asyncssh.Error) as exc:
                raise RemoteBackupError(f"SFTP listing failed: {exc}") from exc

    async def delete(self, name: str) -> None:
        self._require_pin()
        asyncssh = _asyncssh()
        async with await self._connect() as conn:
            try:
                async with conn.start_sftp_client() as sftp:
                    await sftp.remove(self._path(name))
            except (OSError, asyncssh.Error) as exc:
                raise RemoteBackupError(f"SFTP delete of {name} failed: {exc}") from exc

    async def test(self) -> TestResult:
        """Connect, write and delete a small file. Errors are returned verbatim."""
        if not self.host_key:
            key, fp = await fetch_host_key(self.s.host, self.s.port)
            return TestResult(ok=False, needs_host_key_confirmation=True, host_key=key, host_key_fingerprint=fp,
                              error="Confirm the server's host key fingerprint to continue.")
        asyncssh = _asyncssh()
        probe = self._path(f".irdoc_test_{secrets.token_hex(6)}")
        try:
            async with await self._connect() as conn:
                async with conn.start_sftp_client() as sftp:
                    async with sftp.open(probe, "wb") as f:
                        await f.write(b"irdoc backup destination test\n")
                    await sftp.remove(probe)
        except RemoteBackupError as exc:
            return TestResult(ok=False, error=str(exc))
        except (OSError, asyncssh.Error) as exc:
            return TestResult(ok=False, error=f"Could not write to {self.s.remote_dir}: {exc}")
        return TestResult(ok=True)
