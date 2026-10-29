"""Security headers: the app may frame stored files (PDF preview, #137), and nothing else."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stored_file_may_be_framed_by_the_app_only(client: AsyncClient):
    storage = MagicMock(retrieve=AsyncMock(return_value=b"%PDF-1.7\n"))
    with patch("app.api.v1.attachments.verify_file_token", return_value="attachments/i/f.pdf"), \
         patch("app.api.v1.attachments.get_storage_backend", return_value=storage):
        resp = await client.get("/api/v1/files/some-token")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.headers["x-frame-options"] == "SAMEORIGIN"
    csp = resp.headers["content-security-policy"]
    assert "frame-ancestors 'self'" in csp
    assert "default-src 'none'" in csp  # no scripts in served files
    assert resp.headers["x-content-type-options"] == "nosniff"


@pytest.mark.asyncio
async def test_rest_of_the_app_may_not_be_framed(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]
