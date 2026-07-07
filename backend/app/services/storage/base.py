"""
StorageBackend Protocol — ALL file I/O goes through this abstraction.
Never touch the filesystem directly anywhere else in the codebase.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    backend_name: str

    async def store(self, data: bytes, path: str) -> str:
        """Store bytes at path. Returns the final stored path."""
        ...

    async def retrieve(self, path: str) -> bytes:
        """Retrieve file bytes by path."""
        ...

    async def delete(self, path: str) -> None:
        """Delete file at path."""
        ...

    async def get_url(self, path: str, expires_in: int = 3600) -> str:
        """Return a URL to access the file.
        Local backend: signed token endpoint /api/v1/files/{token}
        Cloud backends: presigned URL."""
        ...

    async def test_connection(self) -> bool:
        """Verify backend is reachable and credentials are valid."""
        ...
