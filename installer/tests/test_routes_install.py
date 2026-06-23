import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_root_redirects_to_prerequisites(client):
    resp = await client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "/prerequisites" in resp.headers["location"]


@pytest.mark.asyncio
async def test_prerequisites_page_loads(client):
    resp = await client.get("/prerequisites")
    assert resp.status_code == 200
    assert "Prerequisites" in resp.text


@pytest.mark.asyncio
async def test_https_mode_page_loads(client):
    resp = await client.get("/https-mode")
    assert resp.status_code == 200
    assert "HTTPS" in resp.text


@pytest.mark.asyncio
async def test_set_behind_lb_mode(client):
    resp = await client.post("/https-mode/set", data={"mode": "behind_lb"}, follow_redirects=False)
    assert resp.status_code in (302, 307)
    from installer.wizard import state
    assert state.https_mode == "behind_lb"


@pytest.mark.asyncio
async def test_upload_pfx_invalid_passphrase_returns_error(client, tmp_path):
    # Generate a real PFX with a known passphrase, submit wrong one
    from installer.tests.test_ssl import _make_test_pfx
    pfx_bytes = _make_test_pfx(b"correct")
    resp = await client.post(
        "/https-mode/upload-pfx",
        files={"pfx_file": ("cert.pfx", pfx_bytes, "application/octet-stream")},
        data={"passphrase": "wrong"},
    )
    assert resp.status_code == 200
    assert "passphrase" in resp.text.lower() or "invalid" in resp.text.lower()
