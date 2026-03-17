"""
Audit log endpoints — paginated read + CSV export.
Enterprise feature: requires check_feature("audit_log").
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.feature_flags import check_feature
from app.core.permissions import require_permission
from app.schemas.admin import AuditLogOut
from app.services import audit_service

router = APIRouter(prefix="/audit-log", tags=["audit"])


def _require_audit_feature():
    if not check_feature("audit_log"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Audit log requires an enterprise license",
        )


@router.get("")
async def get_audit_log(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    user_id: str | None = Query(None),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    incident_id: str | None = Query(None),
    from_dt: datetime | None = Query(None),
    to_dt: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("audit_log.read")),
):
    """Return paginated audit log for the org. Enterprise only."""
    _require_audit_feature()

    items, total = await audit_service.get_audit_log(
        db,
        org_id=str(current_user.org_id),
        page=page,
        per_page=per_page,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        incident_id=incident_id,
        from_dt=from_dt,
        to_dt=to_dt,
    )

    return {
        "data": [AuditLogOut.model_validate(item) for item in items],
        "meta": {"page": page, "per_page": per_page, "total": total},
        "error": None,
    }


@router.get("/export")
async def export_audit_log(
    user_id: str | None = Query(None),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    incident_id: str | None = Query(None),
    from_dt: datetime | None = Query(None),
    to_dt: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("audit_log.read")),
):
    """Export audit log as CSV. Enterprise only."""
    _require_audit_feature()

    csv_data = await audit_service.export_csv(
        db,
        org_id=str(current_user.org_id),
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        incident_id=incident_id,
        from_dt=from_dt,
        to_dt=to_dt,
    )

    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=audit_log.csv",
        },
    )
