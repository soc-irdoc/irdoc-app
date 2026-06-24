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


@pytest.mark.asyncio
async def test_review_page_loads(client):
    from installer.wizard import state
    state.base_url = "https://test.example.com"
    state.db_password = "dbpass"
    state.admin_email = "admin@example.com"
    resp = await client.get("/review")
    assert resp.status_code == 200
    assert "test.example.com" in resp.text


@pytest.mark.asyncio
async def test_review_confirm_writes_env_file(client, tmp_path, monkeypatch):
    from installer import wizard as wiz
    from installer.wizard import state
    monkeypatch.setattr(wiz, "DOCKER_DIR", tmp_path)
    (tmp_path / "nginx").mkdir()
    (tmp_path / "ssl").mkdir()
    state.https_mode = "behind_lb"
    state.db_password = "dbpw"
    state.redis_password = "rpw"
    state.secret_key = "sk" * 16
    state.base_url = "https://x.com"
    state.access_token_expire_minutes = 15
    state.refresh_token_expire_days = 30
    state.license_key = ""
    resp = await client.post("/review/confirm", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert (tmp_path / ".env").exists()
    assert (tmp_path / "nginx" / "nginx.conf").exists()


@pytest.mark.asyncio
async def test_install_flow_state_accumulates(client):
    """Walk through the full install flow, verifying state accumulates correctly."""
    from installer.wizard import state
    # Reset state
    state.https_mode = None
    state.db_password = ""
    state.admin_email = None

    # Step 2: set HTTPS mode
    await client.post("/https-mode/set", data={"mode": "behind_lb"})
    assert state.https_mode == "behind_lb"

    # Step 3-4: configure secrets
    await client.post("/core-config", data={
        "base_url": "https://irdoc.test",
        "db_password": "dbpass123456",
        "redis_password": "redispass456",
        "secret_key": "a" * 64,
        "access_token_expire_minutes": "15",
        "refresh_token_expire_days": "30",
        "license_key": "",
    })
    assert state.base_url == "https://irdoc.test"
    assert state.db_password == "dbpass123456"

    # Step 5: admin user
    await client.post("/admin-user", data={
        "admin_name": "Test Admin",
        "admin_email": "admin@irdoc.test",
        "admin_password": "StrongPass123!",
        "admin_password_confirm": "StrongPass123!",
    })
    assert state.admin_name == "Test Admin"
    assert state.admin_email == "admin@irdoc.test"
