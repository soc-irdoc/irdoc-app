"""SSO role mapping: which role a sign-in resolves to, and that it is applied
to existing users on every sign-in (Refs #172)."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User
from app.services.sso_service import provision_oidc_user, resolve_sso_role

GROUP_SOC = "11111111-1111-1111-1111-111111111111"
GROUP_ADMINS = "22222222-2222-2222-2222-222222222222"
USER_OID = "33333333-3333-3333-3333-333333333333"


# ─── resolve_sso_role ────────────────────────────────────────────────────────

def test_no_mappings_resolves_to_none():
    assert resolve_sso_role({"groups": [GROUP_SOC]}, {}) is None
    assert resolve_sso_role({"groups": [GROUP_SOC]}, None) is None


def test_group_match():
    assert resolve_sso_role({"groups": [GROUP_SOC]}, {GROUP_SOC: "senior_analyst"}) == "senior_analyst"


def test_app_role_match():
    assert resolve_sso_role({"roles": ["IRDoc.Admin"]}, {"IRDoc.Admin": "admin"}) == "admin"


def test_user_object_id_match():
    assert resolve_sso_role({"oid": USER_OID}, {USER_OID: "admin"}) == "admin"


def test_most_privileged_match_wins_regardless_of_order():
    mappings = {GROUP_SOC: "analyst", GROUP_ADMINS: "admin"}
    assert resolve_sso_role({"groups": [GROUP_SOC, GROUP_ADMINS]}, mappings) == "admin"
    assert resolve_sso_role({"groups": [GROUP_ADMINS, GROUP_SOC]}, mappings) == "admin"


def test_mapping_keys_match_case_and_whitespace_insensitively():
    assert resolve_sso_role({"groups": [GROUP_SOC.upper()]}, {f" {GROUP_SOC} ": "senior_analyst"}) == "senior_analyst"


def test_no_match_resolves_to_none():
    assert resolve_sso_role({"groups": [GROUP_SOC]}, {GROUP_ADMINS: "admin"}) is None
    assert resolve_sso_role({}, {GROUP_ADMINS: "admin"}) is None


def test_invalid_mapped_role_is_ignored():
    assert resolve_sso_role({"groups": [GROUP_SOC]}, {GROUP_SOC: "superuser"}) is None


# ─── provision_oidc_user ─────────────────────────────────────────────────────

async def _make_user(db: AsyncSession, org, email: str, role: str) -> User:
    user = User(
        org_id=org.id, email=email, full_name="Doe, Jane", role=role,
        password_hash="x", avatar_initials="DJ",
    )
    db.add(user)
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_new_user_gets_mapped_role(db_session: AsyncSession, admin_user):
    _, org = admin_user
    user = await provision_oidc_user(
        db_session, org=org, email="new@test.com", full_name="Doe, Jane", mapped_role="senior_analyst",
    )
    assert user.role == "senior_analyst"
    assert user.auth_provider == "oidc"


@pytest.mark.asyncio
async def test_new_user_without_match_defaults_to_analyst(db_session: AsyncSession, admin_user):
    _, org = admin_user
    user = await provision_oidc_user(
        db_session, org=org, email="new2@test.com", full_name="Doe, Jane", mapped_role=None,
    )
    assert user.role == "analyst"


@pytest.mark.asyncio
async def test_existing_user_is_updated_to_mapped_role(db_session: AsyncSession, admin_user):
    _, org = admin_user
    existing = await _make_user(db_session, org, "jane@test.com", "analyst")

    user = await provision_oidc_user(
        db_session, org=org, email="jane@test.com", full_name="Doe, Jane", mapped_role="admin",
    )
    await db_session.flush()

    assert user.id == existing.id
    assert user.role == "admin"
    audit = (await db_session.execute(
        select(AuditLog).where(AuditLog.action == "user.role_changed", AuditLog.entity_id == existing.id)
    )).scalar_one()
    assert audit.diff == {"old_role": "analyst", "new_role": "admin", "via": "sso"}


@pytest.mark.asyncio
async def test_existing_user_keeps_manual_role_when_nothing_matches(db_session: AsyncSession, admin_user):
    _, org = admin_user
    await _make_user(db_session, org, "senior@test.com", "senior_analyst")

    user = await provision_oidc_user(
        db_session, org=org, email="senior@test.com", full_name="Doe, Jane", mapped_role=None,
    )
    assert user.role == "senior_analyst"


@pytest.mark.asyncio
async def test_last_admin_is_not_demoted_by_a_mapping(db_session: AsyncSession, admin_user):
    admin, org = admin_user  # the only admin in the org

    user = await provision_oidc_user(
        db_session, org=org, email=admin.email, full_name="Test Admin", mapped_role="analyst",
    )
    assert user.role == "admin"


@pytest.mark.asyncio
async def test_admin_is_demoted_when_another_admin_remains(db_session: AsyncSession, admin_user):
    _, org = admin_user
    await _make_user(db_session, org, "second.admin@test.com", "admin")

    user = await provision_oidc_user(
        db_session, org=org, email="second.admin@test.com", full_name="Doe, Jane", mapped_role="analyst",
    )
    assert user.role == "analyst"


@pytest.mark.asyncio
async def test_role_is_not_synced_onto_a_user_in_another_org(db_session: AsyncSession, admin_user):
    from app.models.organization import Organization

    _, org = admin_user
    other = Organization(name="Other Org", slug="other")
    db_session.add(other)
    await db_session.flush()
    await _make_user(db_session, other, "outsider@test.com", "viewer")

    user = await provision_oidc_user(
        db_session, org=org, email="outsider@test.com", full_name="Doe, Jane", mapped_role="admin",
    )
    assert user.role == "viewer"
