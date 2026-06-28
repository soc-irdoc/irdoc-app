"""
AI endpoints — Phase 3.

POST /incidents/{id}/ai/summary         → generate executive summary (premium)
POST /incidents/{id}/ai/recommendations → generate recommendations (premium)
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.database import get_db
from app.core.feature_flags import check_feature
from app.core.permissions import require_permission

router = APIRouter(tags=["ai"])


@router.post("/incidents/{incident_id}/ai/summary", status_code=202)
async def generate_summary(
    incident_id: str,
    db=Depends(get_db),
    current_user=Depends(require_permission("reports.generate")),
):
    if not check_feature("ai_summaries"):
        raise HTTPException(status_code=402, detail="AI summaries require a premium license")

    from app.services import incident_service
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))

    from app.workers.tasks import generate_ai_summary
    task = generate_ai_summary.delay(incident_id)
    return {
        "data": {"task_id": task.id, "message": "AI summary generation queued"},
        "error": None,
    }


@router.post("/incidents/{incident_id}/ai/recommendations", status_code=202)
async def generate_recommendations(
    incident_id: str,
    db=Depends(get_db),
    current_user=Depends(require_permission("reports.generate")),
):
    if not check_feature("ai_summaries"):
        raise HTTPException(status_code=402, detail="AI summaries require a premium license")

    from app.services import incident_service
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))

    from app.workers.tasks import generate_ai_recommendations
    task = generate_ai_recommendations.delay(incident_id)
    return {
        "data": {"task_id": task.id, "message": "AI recommendations generation queued"},
        "error": None,
    }
