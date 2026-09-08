"""
LocalStorageBackend — files stored on the container filesystem.
Files are served via signed token endpoint, never directly from web root.
"""
import os
import os.path
from pathlib import Path

from app.core.security import sign_file_token


class LocalStorageBackend:
    backend_name = "local"

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        # realpath (not abspath) so a symlink placed inside base_path can't be
        # used to slip the containment check in _resolve() below.
        self._base_path_str = os.path.realpath(str(self.base_path))

    def _resolve(self, path: str) -> Path:
        """Join `path` onto base_path and verify the result can't escape it.

        Callers today only ever pass server-generated paths (UUID-based
        attachment keys, validated backup filenames), but this is a shared
        backend class reachable from several call sites — defend the sink
        itself rather than relying on every caller staying disciplined.
        """
        full_path = os.path.realpath(os.path.join(self._base_path_str, path))
        if not (full_path == self._base_path_str or full_path.startswith(self._base_path_str + os.sep)):
            raise ValueError(f"Path escapes storage root: {path!r}")
        return Path(full_path)

    async def store(self, data: bytes, path: str) -> str:
        full_path = self._resolve(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        return path

    async def retrieve(self, path: str) -> bytes:
        full_path = self._resolve(path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return full_path.read_bytes()

    async def delete(self, path: str) -> None:
        full_path = self._resolve(path)
        if full_path.exists():
            full_path.unlink()

    async def get_url(self, path: str, expires_in: int = 3600) -> str:
        token = sign_file_token(path, expires_in)
        return f"/api/v1/files/{token}"

    async def test_connection(self) -> bool:
        return self.base_path.exists() and os.access(self.base_path, os.W_OK)
