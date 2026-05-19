import pytest
import pyotp
from httpx import AsyncClient

from app.core.security import create_mfa_setup_token, create_access_token
from app.services.mfa_service import decrypt_secret


async def test_get_setup_with_mfa_setup_token_returns_uri(
    client: AsyncClient, admin_user
):
    user, org = admin_user
    setup_token = create_mfa_setup_token(str(user.id), str(user.org_id))
    resp = await client.get(
        "/api/v1/auth/mfa/setup",
        headers={"Authorization": f"Bearer {setup_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["secret_uri"].startswith("otpauth://totp/")
    assert "IRDoc" in data["secret_uri"]


async def test_get_setup_with_access_token_returns_uri(
    client: AsyncClient, admin_user, auth_headers
):
    """Voluntary setup from settings page uses regular access token."""
    resp = await client.get(
        "/api/v1/auth/mfa/setup",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "secret_uri" in resp.json()["data"]


async def test_setup_complete_with_valid_code_enables_mfa(
    client: AsyncClient, admin_user, db_session
):
    user, org = admin_user
    setup_token = create_mfa_setup_token(str(user.id), str(user.org_id))

    # GET /setup to generate and store the pending secret
    setup_resp = await client.get(
        "/api/v1/auth/mfa/setup",
        headers={"Authorization": f"Bearer {setup_token}"},
    )
    assert setup_resp.status_code == 200

    # Reload user to get the stored secret
    await db_session.refresh(user)
    raw_secret = decrypt_secret(user.totp_secret)

    # POST /setup/complete with valid code
    valid_code = pyotp.TOTP(raw_secret).now()
    complete_resp = await client.post(
        "/api/v1/auth/mfa/setup/complete",
        json={"code": valid_code},
        headers={"Authorization": f"Bearer {setup_token}"},
    )
    assert complete_resp.status_code == 200
    data = complete_resp.json()["data"]
    assert data["access_token"] is not None
    assert len(data["backup_codes"]) == 10

    # Verify user is now enrolled
    await db_session.refresh(user)
    assert user.mfa_enabled is True
    assert user.mfa_enrolled_at is not None


async def test_setup_complete_with_wrong_code_returns_400(
    client: AsyncClient, admin_user, db_session
):
    user, org = admin_user
    setup_token = create_mfa_setup_token(str(user.id), str(user.org_id))
    await client.get(
        "/api/v1/auth/mfa/setup",
        headers={"Authorization": f"Bearer {setup_token}"},
    )

    complete_resp = await client.post(
        "/api/v1/auth/mfa/setup/complete",
        json={"code": "000000"},
        headers={"Authorization": f"Bearer {setup_token}"},
    )
    assert complete_resp.status_code == 400


async def test_get_setup_with_no_token_returns_401(client: AsyncClient):
    resp = await client.get("/api/v1/auth/mfa/setup")
    assert resp.status_code in (401, 403)
