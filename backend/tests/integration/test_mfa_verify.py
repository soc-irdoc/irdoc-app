import pytest
import pyotp
from httpx import AsyncClient

from app.core.security import create_mfa_challenge_token, create_access_token
from app.services.mfa_service import encrypt_secret, generate_backup_codes


@pytest.fixture
async def enrolled_user(admin_user, db_session):
    """admin_user with MFA fully enrolled. Also returns a pre-issued access token."""
    user, org = admin_user

    # Issue an access token BEFORE enabling MFA so tests that need auth_headers-style
    # access can use it without triggering the MFA challenge flow.
    pre_access_token = create_access_token(str(user.id), str(user.org_id))

    secret = pyotp.random_base32()
    plain_codes, hashed_codes = generate_backup_codes()
    user.mfa_enabled = True
    user.totp_secret = encrypt_secret(secret)
    user.backup_codes = hashed_codes
    await db_session.commit()
    return user, secret, plain_codes, pre_access_token


@pytest.mark.anyio
async def test_verify_with_valid_totp_returns_access_token(
    client: AsyncClient, enrolled_user
):
    user, secret, _, _tok = enrolled_user
    challenge_token = create_mfa_challenge_token(str(user.id), str(user.org_id))
    valid_code = pyotp.TOTP(secret).now()

    resp = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"code": valid_code},
        headers={"Authorization": f"Bearer {challenge_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["access_token"] is not None
    assert data["user"] is not None


@pytest.mark.anyio
async def test_verify_with_wrong_totp_returns_401(
    client: AsyncClient, enrolled_user
):
    user, _, _, _tok = enrolled_user
    challenge_token = create_mfa_challenge_token(str(user.id), str(user.org_id))

    resp = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"code": "000000"},
        headers={"Authorization": f"Bearer {challenge_token}"},
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_verify_with_backup_code_returns_access_token(
    client: AsyncClient, enrolled_user, db_session
):
    user, _, plain_codes, _tok = enrolled_user
    challenge_token = create_mfa_challenge_token(str(user.id), str(user.org_id))

    resp = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"code": plain_codes[0]},
        headers={"Authorization": f"Bearer {challenge_token}"},
    )
    assert resp.status_code == 200

    # Confirm code was consumed
    await db_session.refresh(user)
    assert len(user.backup_codes) == 9


@pytest.mark.anyio
async def test_regenerate_backup_codes_returns_ten_new_codes(
    client: AsyncClient, enrolled_user
):
    user, _, _, pre_access_token = enrolled_user
    headers = {"Authorization": f"Bearer {pre_access_token}"}
    resp = await client.post(
        "/api/v1/auth/mfa/backup-codes/regenerate",
        headers=headers,
    )
    assert resp.status_code == 200
    codes = resp.json()["data"]["codes"]
    assert len(codes) == 10
    for code in codes:
        assert "-" in code


@pytest.mark.anyio
async def test_disable_mfa_clears_fields(
    client: AsyncClient, enrolled_user, db_session
):
    user, _, _, pre_access_token = enrolled_user
    headers = {"Authorization": f"Bearer {pre_access_token}"}
    resp = await client.delete("/api/v1/auth/mfa/disable", headers=headers)
    assert resp.status_code == 200

    await db_session.refresh(user)
    assert user.mfa_enabled is False
    assert user.totp_secret is None
    assert user.backup_codes is None


@pytest.mark.anyio
async def test_disable_mfa_blocked_when_org_requires_it(
    client: AsyncClient, enrolled_user, db_session
):
    user, _, _, pre_access_token = enrolled_user
    from app.models.organization import Organization
    org = await db_session.get(Organization, user.org_id)
    settings = org.settings or {}
    settings["mfa_required"] = True
    org.settings = settings
    await db_session.commit()

    headers = {"Authorization": f"Bearer {pre_access_token}"}
    resp = await client.delete("/api/v1/auth/mfa/disable", headers=headers)
    assert resp.status_code == 409
