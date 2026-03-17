"""
Task service: CRUD + template instantiation + progress calculation.
"""
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


async def list_tasks(db: AsyncSession, incident_id: str) -> list[Task]:
    result = await db.execute(
        select(Task).where(Task.incident_id == incident_id).order_by(Task.sort_order, Task.created_at)
    )
    return list(result.scalars().all())


async def get_task(db: AsyncSession, task_id: str, incident_id: str) -> Task:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.incident_id == incident_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def create_task(
    db: AsyncSession, incident_id: str, data: TaskCreate, created_by: str | None = None
) -> Task:
    task = Task(
        incident_id=incident_id,
        title=data.title,
        description=data.description,
        phase=data.phase,
        priority=data.priority,
        assigned_to=data.assigned_to,
        sort_order=data.sort_order,
    )
    db.add(task)
    await db.flush()
    return task


async def update_task(
    db: AsyncSession, task: Task, data: TaskUpdate, updated_by: str | None = None
) -> Task:
    update_data = data.model_dump(exclude_none=True)

    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == "done" and task.status != "done":
            task.completed_at = datetime.now(UTC)
            task.completed_by = updated_by
        elif new_status != "done" and task.status == "done":
            task.completed_at = None
            task.completed_by = None

    for key, value in update_data.items():
        setattr(task, key, value)

    await db.flush()
    return task


async def delete_task(db: AsyncSession, task: Task) -> None:
    await db.delete(task)
    await db.flush()


def compute_progress(tasks: list[Task]) -> dict:
    total = len(tasks)
    if total == 0:
        return {"total": 0, "done": 0, "percent": 0}
    done = sum(1 for t in tasks if t.status == "done")
    return {"total": total, "done": done, "percent": round(done / total * 100)}
