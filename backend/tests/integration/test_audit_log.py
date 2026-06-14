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
    import os
    if "sqlite" in os.getenv("TEST_DATABASE_URL", "sqlite"):
        pytest.skip("high_risk filter requires PostgreSQL JSONB path queries")

    user, org = admin_user
    await audit_service.log(db_session, org_id=str(org.id), action="incident.deleted",
        entity_type="incident", risk_level="high")
    await audit_service.log(db_session, org_id=str(org.id), action="incident.created",
        entity_type="incident")
    await db_session.commit()

    items, total = await audit_service.get_audit_log(
        db_session, str(org.id), category="high_risk"
    )
    assert total == 1
    assert items[0].action == "incident.deleted"


@pytest.mark.asyncio
async def test_create_incident_writes_audit(client: AsyncClient, auth_headers, db_session: AsyncSession):
    resp = await client.post(
        "/api/v1/incidents",
        json={"title": "Ransomware Alert", "severity": "sev1"},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    result = await db_session.execute(select(AuditLog).where(AuditLog.action == "incident.created"))
    entry = result.scalar_one_or_none()
    assert entry is not None
    assert entry.actor_label == "admin@test.com"
    assert "Ransomware Alert" in (entry.entity_label or "")


@pytest.mark.asyncio
async def test_update_incident_status_writes_audit(client: AsyncClient, auth_headers, db_session: AsyncSession):
    create_resp = await client.post(
        "/api/v1/incidents",
        json={"title": "Test Inc", "severity": "sev2"},
        headers=auth_headers,
    )
    incident_id = create_resp.json()["data"]["id"]

    await client.put(
        f"/api/v1/incidents/{incident_id}",
        json={"status": "monitoring"},
        headers=auth_headers,
    )

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "incident.status_changed")
    )
    entry = result.scalar_one_or_none()
    assert entry is not None
    assert entry.diff == {"from": "open", "to": "monitoring"}


@pytest.mark.asyncio
async def test_delete_incident_writes_high_risk_audit(client: AsyncClient, auth_headers, db_session: AsyncSession):
    create_resp = await client.post(
        "/api/v1/incidents",
        json={"title": "To Delete", "severity": "sev4"},
        headers=auth_headers,
    )
    incident_id = create_resp.json()["data"]["id"]

    await client.delete(f"/api/v1/incidents/{incident_id}", headers=auth_headers)

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "incident.deleted")
    )
    entry = result.scalar_one_or_none()
    assert entry is not None
    assert entry.diff.get("_risk_level") == "high"
