import pytest
import pyotp
from httpx import AsyncClient

from app.services.mfa_service import encrypt_secret, generate_backup_codes


async def test_login_without_mfa_returns_access_token(client: AsyncClient, admin_user):
    """Normal login — no MFA configured, no org requirement."""
    _user, _org = admin_user
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "TestPass123!",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["access_token"] is not None
    assert data.get("mfa_challenge_token") is None
    assert data.get("mfa_setup_token") is None


async def test_login_with_mfa_enabled_returns_challenge_token(
    client: AsyncClient, admin_user, db_session
):
    user, _org = admin_user
    secret = pyotp.random_base32()
    _, hashed_codes = generate_backup_codes()
    user.mfa_enabled = True
    user.totp_secret = encrypt_secret(secret)
    user.backup_codes = hashed_codes
    await db_session.commit()

    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "TestPass123!",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data.get("mfa_challenge_token") is not None
    assert data.get("access_token") is None
    assert data.get("user") is None  # user not returned until MFA confirmed


async def test_login_under_org_mfa_requirement_returns_setup_token(
    client: AsyncClient, admin_user, db_session
):
    user, org = admin_user
    # Set org to require MFA
    settings = org.settings or {}
    settings["mfa_required"] = True
    org.settings = settings
    await db_session.commit()

    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "TestPass123!",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data.get("mfa_setup_token") is not None
    assert data.get("access_token") is None


async def test_login_wrong_password_still_returns_401(client: AsyncClient, admin_user):
    _user, _org = admin_user
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401
