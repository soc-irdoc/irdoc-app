"""
Backup management endpoints - config, listing, manual trigger, download.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.services import backup_crypto, backup_destinations
from app.services.backup_service import (
    count_backups_needing_rekey,
    get_local_backup_path,
    get_or_create_config,
    list_records,
    update_config,
)

router = APIRouter(prefix="/admin/backup", tags=["backup"])

VALID_SCHEDULES = {"6h", "daily", "weekly", "monthly"}
VALID_DESTINATIONS = set(backup_destinations.DESTINATIONS)  # local, cloud, sftp, smb (#151)


class BackupConfigUpdate(BaseModel):
    enabled: bool | None = None
    schedule: str | None = None
    retention_days: int | None = None
    destination: str | None = None


def _config_to_dict(cfg) -> dict:
    return {
        "id": str(cfg.id),
        "enabled": cfg.enabled,
        "schedule": cfg.schedule,
        "retention_days": cfg.retention_days,
        "destination": cfg.destination,
        "last_backup_at": cfg.last_backup_at.isoformat() if cfg.last_backup_at else None,
        "last_backup_status": cfg.last_backup_status,
        "last_backup_error": cfg.last_backup_error,
        "last_backup_size_bytes": cfg.last_backup_size_bytes,
        # Backup encryption key (#149)
        "key_fingerprint": backup_crypto.active_fingerprint(),
        "key_source": backup_crypto.active_key_source(),
        "legacy_backup_count": count_backups_needing_rekey(),
    }


def _record_to_dict(rec) -> dict:
    return {
        "id": str(rec.id),
        "filename": rec.filename,
        "size_bytes": rec.size_bytes,
        "destination": rec.destination,
        "status": rec.status,
        "error": rec.error,
        "key_fingerprint": rec.key_fingerprint,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }


@router.get("/config")
async def get_backup_config(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    cfg = await get_or_create_config(db)
    return {"data": _config_to_dict(cfg), "error": None}


@router.put("/config")
async def set_backup_config(
    data: BackupConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    if data.schedule is not None and data.schedule not in VALID_SCHEDULES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"schedule must be one of {sorted(VALID_SCHEDULES)}",
        )
    if data.destination is not None and data.destination not in VALID_DESTINATIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"destination must be one of {sorted(VALID_DESTINATIONS)}",
        )
    if data.destination in backup_destinations.REMOTE_KINDS:
        row = await backup_destinations.get_remote_config(db, data.destination)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Configure the {data.destination.upper()} destination before selecting it",
            )
        if data.destination == "sftp" and not row.host_key:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Pin the SFTP server's host key (Test connection) before selecting SFTP",
            )

    patch = data.model_dump(exclude_none=True)
    cfg = await update_config(db, **patch)
    return {"data": _config_to_dict(cfg), "error": None}


@router.get("/backups")
async def list_backups(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    records = await list_records(db)
    return {"data": [_record_to_dict(r) for r in records], "error": None}


@router.post("/run")
async def run_backup(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    from app.workers.backup_tasks import trigger_manual_backup
    config = await get_or_create_config(db)
    config.last_backup_status = "running"
    await db.commit()
    trigger_manual_backup.delay()
    return {"data": {"queued": True}, "error": None}


@router.get("/download/{filename}")
async def download_backup(
    filename: str,
    current_user=Depends(require_permission("users.manage")),
):
    try:
        path = get_local_backup_path(filename)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup file not found")
    return FileResponse(path, media_type="application/octet-stream", filename=filename)
