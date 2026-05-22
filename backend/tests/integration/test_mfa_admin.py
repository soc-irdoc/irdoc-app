import pytest
import pyotp
from httpx import AsyncClient

from app.core.security import create_access_token
from app.services.mfa_service import encrypt_secret, generate_backup_codes


@pytest.fixture
async def enrolled_admin(admin_user, db_session):
    """admin_user with MFA fully enrolled."""
    user, org = admin_user
    secret = pyotp.random_base32()
    _, hashed_codes = generate_backup_codes()
    user.mfa_enabled = True
    user.totp_secret = encrypt_secret(secret)
    user.backup_codes = hashed_codes
    await db_session.commit()
    return user, org


@pytest.mark.anyio
async def test_admin_can_reset_user_mfa(
    client: AsyncClient, enrolled_admin, db_session
):
    user, org = enrolled_admin
    # Use pre-MFA access token (not auth_headers — that would trigger challenge)
    access_token = create_access_token(str(user.id), str(user.org_id))
    resp = await client.post(
        f"/api/v1/users/{user.id}/mfa/reset",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200

    await db_session.refresh(user)
    assert user.mfa_enabled is False
    assert user.totp_secret is None
    assert user.backup_codes is None
    assert user.mfa_enrolled_at is None


@pytest.mark.anyio
async def test_non_admin_cannot_reset_others_mfa(
    client: AsyncClient, admin_user, db_session
):
    """analyst role should get 403 when resetting another user's MFA."""
    from app.models.user import User
    from app.core.security import hash_password
    import uuid

    target_user, org = admin_user

    # Create an analyst user in the same org
    analyst = User(
        id=uuid.uuid4(),
        org_id=target_user.org_id,
        email="analyst_mfareset@test.com",
        full_name="Test Analyst",
        password_hash=hash_password("Pass123!"),
        role="analyst",
        is_active=True,
        must_reset_password=False,
    )
    db_session.add(analyst)
    await db_session.commit()

    analyst_token = create_access_token(str(analyst.id), str(analyst.org_id))
    resp = await client.post(
        f"/api/v1/users/{target_user.id}/mfa/reset",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_admin_can_set_org_mfa_required(
    client: AsyncClient, admin_user, db_session
):
    user, org = admin_user
    access_token = create_access_token(str(user.id), str(user.org_id))
    resp = await client.patch(
        "/api/v1/admin/org",
        json={"mfa_required": True},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200

    from app.models.organization import Organization
    await db_session.refresh(org)
    assert (org.settings or {}).get("mfa_required") is True


@pytest.mark.anyio
async def test_admin_can_disable_org_mfa_required(
    client: AsyncClient, admin_user, db_session
):
    user, org = admin_user
    # First enable it
    org.settings = {"mfa_required": True}
    await db_session.commit()

    access_token = create_access_token(str(user.id), str(user.org_id))
    resp = await client.patch(
        "/api/v1/admin/org",
        json={"mfa_required": False},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200

    await db_session.refresh(org)
    assert (org.settings or {}).get("mfa_required") is False
