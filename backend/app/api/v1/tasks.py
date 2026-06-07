from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.services import incident_service, task_service

router = APIRouter(tags=["tasks"])


@router.get("/incidents/{incident_id}/tasks")
async def list_tasks(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("tasks.read")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    tasks = await task_service.list_tasks(db, incident_id)
    return {"data": [TaskOut.model_validate(t) for t in tasks], "error": None}


@router.post("/incidents/{incident_id}/tasks", status_code=201)
async def create_task(
    incident_id: str,
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("tasks.create")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    task = await task_service.create_task(db, incident_id, data, str(current_user.id))
    from app.services.report_service import maybe_trigger_ai_report
    await maybe_trigger_ai_report(db, incident_id, str(current_user.org_id))
    return {"data": TaskOut.model_validate(task), "error": None}


@router.put("/incidents/{incident_id}/tasks/{task_id}")
async def update_task(
    incident_id: str,
    task_id: str,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("tasks.update")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    task = await task_service.get_task(db, task_id, incident_id)
    updated = await task_service.update_task(db, task, data, str(current_user.id))
    from app.services.report_service import maybe_trigger_ai_report
    await maybe_trigger_ai_report(db, incident_id, str(current_user.org_id))
    return {"data": TaskOut.model_validate(updated), "error": None}


@router.delete("/incidents/{incident_id}/tasks/{task_id}", status_code=204)
async def delete_task(
    incident_id: str,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("tasks.delete")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    task = await task_service.get_task(db, task_id, incident_id)
    await task_service.delete_task(db, task)
