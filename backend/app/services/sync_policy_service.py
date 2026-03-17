"""
Sync policy service.

Handles CRUD for sync_policies. Actual SharePoint delivery is Phase 4.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import SyncPolicy
from app.schemas.report import SyncPolicyCreate, SyncPolicyUpdate


async def list_policies(db: AsyncSession, incident_id: str) -> list[SyncPolicy]:
    result = await db.execute(
        select(SyncPolicy)
        .where(SyncPolicy.incident_id == incident_id)
        .order_by(SyncPolicy.created_at.desc())
    )
    return list(result.scalars().all())


async def get_policy(db: AsyncSession, policy_id: str, incident_id: str) -> SyncPolicy:
    result = await db.execute(
        select(SyncPolicy).where(
            SyncPolicy.id == policy_id,
            SyncPolicy.incident_id == incident_id,
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Sync policy not found")
    return policy


async def create_policy(
    db: AsyncSession,
    incident_id: str,
    data: SyncPolicyCreate,
    created_by: str,
) -> SyncPolicy:
    from app.core.feature_flags import check_feature
    if not check_feature("sharepoint_sync"):
        raise HTTPException(status_code=402, detail="Sync policies require a premium license")

    policy = SyncPolicy(
        incident_id=incident_id,
        destination=data.destination,
        report_template_id=data.report_template_id,
        trigger_type=data.trigger_type,
        debounce_seconds=data.debounce_seconds,
        destination_config=data.destination_config,
        created_by=created_by,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


async def update_policy(
    db: AsyncSession,
    policy: SyncPolicy,
    data: SyncPolicyUpdate,
) -> SyncPolicy:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)
    await db.commit()
    await db.refresh(policy)
    return policy


async def delete_policy(db: AsyncSession, policy: SyncPolicy) -> None:
    await db.delete(policy)
    await db.commit()
