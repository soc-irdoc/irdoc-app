"""Unit tests for LocalStorageBackend."""

import pytest
import pytest_asyncio

from app.services.storage.local import LocalStorageBackend


@pytest_asyncio.fixture
async def backend(tmp_path):
    return LocalStorageBackend(str(tmp_path))


@pytest.mark.asyncio
async def test_store_and_retrieve(backend):
    data = b"Hello, IRDoc!"
    path = await backend.store(data, "test/file.txt")
    retrieved = await backend.retrieve(path)
    assert retrieved == data


@pytest.mark.asyncio
async def test_delete(backend):
    await backend.store(b"to delete", "del/file.txt")
    await backend.delete("del/file.txt")
    with pytest.raises(FileNotFoundError):
        await backend.retrieve("del/file.txt")


@pytest.mark.asyncio
async def test_delete_missing_file_no_error(backend):
    # Deleting non-existent file should not raise
    await backend.delete("nonexistent/file.txt")


@pytest.mark.asyncio
async def test_get_url_returns_signed_path(backend):
    await backend.store(b"data", "attachments/inc1/file.pdf")
    url = await backend.get_url("attachments/inc1/file.pdf", expires_in=3600)
    assert url.startswith("/api/v1/files/")


@pytest.mark.asyncio
async def test_test_connection(backend):
    assert await backend.test_connection() is True


@pytest.mark.asyncio
async def test_stores_in_subdirectory(backend, tmp_path):
    await backend.store(b"nested", "a/b/c/file.bin")
    assert (tmp_path / "a" / "b" / "c" / "file.bin").exists()
