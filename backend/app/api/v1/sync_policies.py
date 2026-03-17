"""
Sync policy endpoints — Phase 3.

GET    /incidents/{id}/sync-policies            → list
POST   /incidents/{id}/sync-policies            → create (premium)
PUT    /incidents/{id}/sync-policies/{pid}      → update
DELETE /incidents/{id}/sync-policies/{pid}      → delete
POST   /incidents/{id}/sync-policies/{pid}/trigger → manual trigger (stub until Phase 4)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.schemas.report import SyncPolicyCreate, SyncPolicyOut, SyncPolicyUpdate
from app.services import sync_policy_service

router = APIRouter(tags=["sync-policies"])


@router.get("/incidents/{incident_id}/sync-policies")
async def list_policies(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports.read")),
):
    policies = await sync_policy_service.list_policies(db, incident_id)
    return {
        "data": [SyncPolicyOut.model_validate(p) for p in policies],
        "meta": {"total": len(policies)},
        "error": None,
    }


@router.post("/incidents/{incident_id}/sync-policies", status_code=201)
async def create_policy(
    incident_id: str,
    data: SyncPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports.generate")),
):
    policy = await sync_policy_service.create_policy(
        db, incident_id, data, str(current_user.id)
    )
    return {"data": SyncPolicyOut.model_validate(policy), "error": None}


@router.put("/incidents/{incident_id}/sync-policies/{policy_id}")
async def update_policy(
    incident_id: str,
    policy_id: str,
    data: SyncPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports.generate")),
):
    policy = await sync_policy_service.get_policy(db, policy_id, incident_id)
    updated = await sync_policy_service.update_policy(db, policy, data)
    return {"data": SyncPolicyOut.model_validate(updated), "error": None}


@router.delete("/incidents/{incident_id}/sync-policies/{policy_id}", status_code=204)
async def delete_policy(
    incident_id: str,
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports.generate")),
):
    policy = await sync_policy_service.get_policy(db, policy_id, incident_id)
    await sync_policy_service.delete_policy(db, policy)


@router.post("/incidents/{incident_id}/sync-policies/{policy_id}/trigger", status_code=202)
async def trigger_policy(
    incident_id: str,
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports.generate")),
):
    """Manual sync trigger. Returns 202 Accepted. Actual delivery implemented in Phase 4."""
    policy = await sync_policy_service.get_policy(db, policy_id, incident_id)
    # Phase 4: sync_to_sharepoint.delay(incident_id, policy_id)
    return {
        "data": {"message": "Sync queued", "policy_id": str(policy.id)},
        "error": None,
    }
