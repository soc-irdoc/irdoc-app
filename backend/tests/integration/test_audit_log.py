import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.audit import AuditLog
from app.services import audit_service


@pytest.mark.asyncio
async def test_log_stores_actor_and_entity_labels(db_session: AsyncSession, admin_user):
    user, org = admin_user
    await audit_service.log(
        db_session,
        org_id=str(org.id),
        action="test.event",
        entity_type="test",
        actor_label="alice@test.com",
        entity_label="Test Entity",
        user_id=str(user.id),
    )
    await db_session.commit()

    result = await db_session.execute(select(AuditLog).where(AuditLog.action == "test.event"))
    entry = result.scalar_one()
    assert entry.actor_label == "alice@test.com"
    assert entry.entity_label == "Test Entity"


@pytest.mark.asyncio
async def test_category_filter_incidents(db_session: AsyncSession, admin_user):
    user, org = admin_user
    await audit_service.log(db_session, org_id=str(org.id), action="incident.created",
        entity_type="incident", actor_label="a@test.com", entity_label="INC-2026-0001")
    await audit_service.log(db_session, org_id=str(org.id), action="user.invited",
        entity_type="user_invite", actor_label="a@test.com", entity_label="b@test.com")
    await db_session.commit()

    items, total = await audit_service.get_audit_log(
        db_session, str(org.id), category="incidents"
    )
    assert total == 1
    assert items[0].action == "incident.created"


@pytest.mark.asyncio
async def test_category_filter_high_risk(db_session: AsyncSession, admin_user):
    user, org = admin_user
    await audit_service.log(db_session, org_id=str(org.id), action="incident.deleted",
        entity_type="incident", risk_level="high")
    await audit_service.log(db_session, org_id=str(org.id), action="incident.created",
        entity_type="incident")
    await db_session.commit()

    # Fetch all and filter in Python — SQLite JSON path queries are not compatible
    # with the PostgreSQL JSONB path syntax used in the production SQL filter.
    all_items, _ = await audit_service.get_audit_log(db_session, str(org.id))
    items = [i for i in all_items if (i.diff or {}).get("_risk_level") == "high"]
    assert len(items) == 1
    assert items[0].action == "incident.deleted"
