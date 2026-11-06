"""SFTP / SMB backup destination settings (#151).

Kept apart from Admin > Storage so backups can live somewhere fully separate
from the evidence they protect. Secrets are stored encrypted and never
returned, only whether they are set.
"""
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.backup import BackupRemoteConfig
from app.services import audit_service, backup_destinations
from app.services.integration_service import decrypt_config, encrypt_config

router = APIRouter(prefix="/admin/backup/remote", tags=["backup"])

RemoteKind = Literal["sftp", "smb"]
Host = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255, pattern=r"^[^\s/\\]+$")]


class SFTPConfigIn(BaseModel):
    host: Host
    port: int = Field(22, ge=1, le=65535)
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    remote_dir: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1024)] = "."
    auth: Literal["password", "key"] = "password"
    # Empty / omitted = keep the stored value.
    password: str | None = None
    private_key: str | None = Field(None, max_length=20000)
    passphrase: str | None = None
    # OpenSSH public key line the admin confirmed after a test (pins it).
    host_key: str | None = Field(None, max_length=20000)


class SMBConfigIn(BaseModel):
    server: Host
    port: int = Field(445, ge=1, le=65535)
    share: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    path: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1024)] = ""
    username: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] = ""
    password: str | None = None
    domain: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None
    # SMB 3 encryption; turning it off is an explicit, warned-about choice.
    require_encryption: bool = True


_MODELS = {"sftp": SFTPConfigIn, "smb": SMBConfigIn}
# Changing any of these on SFTP drops the pinned host key: it belongs to the old server.
_SFTP_IDENTITY = ("host", "port")


def _parse(kind: str, body: dict) -> BaseModel:
    try:
        return _MODELS[kind].model_validate(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


def _merge(kind: str, data: BaseModel, stored: dict) -> dict:
    """New settings, keeping stored secrets the request left empty."""
    merged = data.model_dump(exclude={"host_key"})
    for key in backup_destinations.SECRET_FIELDS[kind]:
        if not merged.get(key):
            merged[key] = stored.get(key)
    return merged


def _out(kind: str, row: BackupRemoteConfig | None) -> dict:
    if row is None:
        return {"kind": kind, "configured": False}
    cfg = decrypt_config(row.config or {})
    secrets = backup_destinations.SECRET_FIELDS[kind]
    out = {k: v for k, v in cfg.items() if k not in secrets}
    out.update({f"{k}_set": bool(cfg.get(k)) for k in secrets})
    out.update({
        "kind": kind,
        "configured": True,
        "host_key_fingerprint": row.host_key_fingerprint,
        "host_key_pinned": bool(row.host_key),
        "last_tested": row.last_tested.isoformat() if row.last_tested else None,
        "test_status": row.test_status,
        "test_error": row.test_error,
    })
    return out


def _fingerprint(host_key: str) -> str:
    import base64
    import hashlib
    try:
        blob = base64.b64decode(host_key.split()[1])
    except (IndexError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="host_key must be an OpenSSH public key line") from exc
    return "SHA256:" + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")


@router.get("/{kind}")
async def get_remote_config(
    kind: RemoteKind,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    row = await backup_destinations.get_remote_config(db, kind)
    return {"data": _out(kind, row), "error": None}


@router.put("/{kind}")
async def put_remote_config(
    kind: RemoteKind,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    data = _parse(kind, body)
    row = await backup_destinations.get_remote_config(db, kind)
    stored = decrypt_config(row.config) if row else {}
    merged = _merge(kind, data, stored)

    if row is None:
        row = BackupRemoteConfig(kind=kind, config={})
        db.add(row)

    action = "backup.remote_config_updated"
    if kind == "sftp":
        moved = any(stored.get(k) != merged.get(k) for k in _SFTP_IDENTITY)
        new_key = getattr(data, "host_key", None)
        if new_key:
            row.host_key = new_key.strip()
            row.host_key_fingerprint = _fingerprint(row.host_key)
            action = "backup.sftp_host_key_pinned"
        elif moved:
            row.host_key = None
            row.host_key_fingerprint = None

    row.config = encrypt_config(merged)
    row.test_status = row.test_error = None
    await db.flush()
    await audit_service.log(
        db,
        org_id=str(current_user.org_id),
        action=action,
        entity_type="backup_destination",
        entity_id=str(row.id),
        actor_label=current_user.email,
        entity_label=kind.upper(),
        diff={"host_key_fingerprint": row.host_key_fingerprint} if kind == "sftp" else None,
        user_id=str(current_user.id),
        request=request,
        risk_level="high",
    )
    await db.commit()
    await db.refresh(row)
    return {"data": _out(kind, row), "error": None}


@router.post("/{kind}/test")
async def test_remote_config(
    kind: RemoteKind,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    """Test the settings in the request (unsaved), using stored secrets where left empty.

    SFTP without a pinned key for this host returns the server's key and
    fingerprint for the admin to confirm; nothing is trusted automatically.
    """
    data = _parse(kind, body)
    row = await backup_destinations.get_remote_config(db, kind)
    stored = decrypt_config(row.config) if row else {}
    merged = _merge(kind, data, stored)

    host_key = None
    if kind == "sftp":
        same_server = row is not None and all(stored.get(k) == merged.get(k) for k in _SFTP_IDENTITY)
        host_key = getattr(data, "host_key", None) or (row.host_key if same_server else None)

    try:
        dest = backup_destinations.build_destination(kind, merged, host_key)
        result = await dest.test()
    except backup_destinations.RemoteBackupError as exc:
        result = backup_destinations.TestResult(ok=False, error=str(exc))

    if row is not None and not result.needs_host_key_confirmation:
        row.last_tested = datetime.now(UTC)
        row.test_status = "ok" if result.ok else "failed"
        row.test_error = result.error
        await db.commit()

    return {
        "data": {
            "ok": result.ok,
            "error": result.error,
            "needs_host_key_confirmation": result.needs_host_key_confirmation,
            "host_key": result.host_key,
            "host_key_fingerprint": result.host_key_fingerprint,
        },
        "error": None,
    }
