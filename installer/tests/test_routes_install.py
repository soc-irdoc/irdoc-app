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


@pytest.mark.asyncio
async def test_core_config_page_loads(client):
    resp = await client.get("/core-config")
    assert resp.status_code == 200
    assert "Base URL" in resp.text or "base_url" in resp.text.lower()


@pytest.mark.asyncio
async def test_generate_secrets_returns_json(client):
    resp = await client.get("/api/generate-secrets")
    assert resp.status_code == 200
    data = resp.json()
    assert "db_password" in data
    assert "redis_password" in data
    assert "secret_key" in data


@pytest.mark.asyncio
async def test_core_config_post_saves_state(client):
    resp = await client.post("/core-config", data={
        "base_url": "https://irdoc.example.com",
        "db_password": "dbpass123",
        "redis_password": "redispass123",
        "secret_key": "hexsecret" * 4,
        "access_token_expire_minutes": "15",
        "refresh_token_expire_days": "30",
        "license_key": "",
    }, follow_redirects=False)
    assert resp.status_code in (302, 307)
    from installer.wizard import state
    assert state.base_url == "https://irdoc.example.com"


@pytest.mark.asyncio
async def test_admin_user_page_loads(client):
    resp = await client.get("/admin-user")
    assert resp.status_code == 200
    assert "email" in resp.text.lower()


@pytest.mark.asyncio
async def test_admin_user_post_validates_password_length(client):
    resp = await client.post("/admin-user", data={
        "admin_name": "Admin", "admin_email": "admin@example.com",
        "admin_password": "short", "admin_password_confirm": "short",
    })
    assert resp.status_code == 422 or "12" in resp.text


@pytest.mark.asyncio
async def test_admin_user_post_redirects_on_success(client):
    resp = await client.post("/admin-user", data={
        "admin_name": "Admin User", "admin_email": "admin@example.com",
        "admin_password": "StrongPass123!", "admin_password_confirm": "StrongPass123!",
    }, follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "/review" in resp.headers["location"]
