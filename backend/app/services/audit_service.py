"""
Audit log service — writes to audit_log table and reads/exports.

Usage in services:
    await audit_service.log(db, user_id=user.id, org_id=org.id,
        action="incident.created", entity_type="incident", entity_id=str(inc.id),
        request=request)
"""
import csv
import io
import uuid
from datetime import datetime
from typing import Any

from fastapi import Request
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

CATEGORY_ENTITY_TYPES: dict[str, list[str]] = {
    "incidents": ["incident"],
    "users": ["user", "user_invite"],
    "auth": ["auth"],
    "settings": ["organization", "storage_config", "sso_config"],
    "integrations": ["integration", "device"],
    "api_keys": ["api_key"],
}


async def log(
    db: AsyncSession,
    *,
    org_id: str,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_label: str | None = None,
    entity_label: str | None = None,
    user_id: str | None = None,
    api_key_id: str | None = None,
    diff: dict | None = None,
    request: Request | None = None,
    risk_level: str = "normal",
) -> None:
    """Write a single audit log entry. Flushes but does not commit — caller owns the transaction."""
    ip = None
    user_agent = None
    if request:
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    parsed_user_id: uuid.UUID | None = None
    if user_id:
        try:
            parsed_user_id = uuid.UUID(str(user_id))
        except (ValueError, AttributeError):
            pass

    parsed_api_key_id: uuid.UUID | None = None
    if api_key_id:
        try:
            parsed_api_key_id = uuid.UUID(str(api_key_id))
        except (ValueError, AttributeError):
            pass

    parsed_org_id: uuid.UUID | None = None
    try:
        parsed_org_id = uuid.UUID(str(org_id))
    except (ValueError, AttributeError):
        pass

    parsed_entity_id: uuid.UUID | None = None
    if entity_id:
        try:
            parsed_entity_id = uuid.UUID(str(entity_id))
        except (ValueError, AttributeError):
            pass

    entry_diff = dict(diff) if diff else {}
    if risk_level == "high":
        entry_diff["_risk_level"] = "high"

    entry = AuditLog(
        org_id=parsed_org_id,
        user_id=parsed_user_id,
        api_key_id=parsed_api_key_id,
        action=action,
        entity_type=entity_type,
        entity_id=parsed_entity_id,
        actor_label=actor_label,
        entity_label=entity_label,
        diff=entry_diff,
        ip_address=ip,
        user_agent=user_agent,
    )
    db.add(entry)
    await db.flush()


async def get_audit_log(
    db: AsyncSession,
    org_id: str,
    *,
    page: int = 1,
    per_page: int = 50,
    user_id: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    incident_id: str | None = None,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    category: str | None = None,
) -> tuple[list[AuditLog], int]:
    """Return (items, total) with filters applied."""
    filters: list[Any] = []

    try:
        filters.append(AuditLog.org_id == uuid.UUID(str(org_id)))
    except (ValueError, AttributeError):
        return [], 0

    if user_id:
        try:
            filters.append(AuditLog.user_id == uuid.UUID(str(user_id)))
        except (ValueError, AttributeError):
            pass

    if action:
        filters.append(AuditLog.action == action)

    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)

    if incident_id:
        try:
            filters.append(AuditLog.entity_id == uuid.UUID(str(incident_id)))
        except (ValueError, AttributeError):
            pass

    if from_dt:
        filters.append(AuditLog.created_at >= from_dt)

    if to_dt:
        filters.append(AuditLog.created_at <= to_dt)

    if category == "high_risk":
        filters.append(AuditLog.diff["_risk_level"].as_string() == "high")
    elif category and category in CATEGORY_ENTITY_TYPES:
        filters.append(AuditLog.entity_type.in_(CATEGORY_ENTITY_TYPES[category]))

    # Total count
    count_q = select(func.count()).select_from(AuditLog)
    if filters:
        count_q = count_q.where(and_(*filters))
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # Paginated items
    items_q = select(AuditLog)
    if filters:
        items_q = items_q.where(and_(*filters))
    items_q = (
        items_q.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    items_result = await db.execute(items_q)
    items = list(items_result.scalars().all())

    return items, total


async def export_csv(
    db: AsyncSession,
    org_id: str,
    *,
    user_id: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    incident_id: str | None = None,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    category: str | None = None,
) -> str:
    """Return a CSV string of filtered audit log rows (up to 10,000 rows)."""
    items, _ = await get_audit_log(
        db, org_id, page=1, per_page=10000,
        user_id=user_id, action=action, entity_type=entity_type,
        incident_id=incident_id, from_dt=from_dt, to_dt=to_dt,
        category=category,
    )
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "id", "created_at", "action", "entity_type", "entity_id",
        "actor_label", "entity_label",
        "user_id", "api_key_id", "ip_address", "user_agent", "diff",
    ])
    writer.writeheader()
    for item in items:
        writer.writerow({
            "id": str(item.id),
            "created_at": item.created_at.isoformat() if item.created_at else "",
            "action": item.action or "",
            "entity_type": item.entity_type or "",
            "entity_id": str(item.entity_id) if item.entity_id else "",
            "actor_label": item.actor_label or "",
            "entity_label": item.entity_label or "",
            "user_id": str(item.user_id) if item.user_id else "",
            "api_key_id": str(item.api_key_id) if item.api_key_id else "",
            "ip_address": item.ip_address or "",
            "user_agent": item.user_agent or "",
            "diff": str(item.diff) if item.diff else "",
        })
    return output.getvalue()
