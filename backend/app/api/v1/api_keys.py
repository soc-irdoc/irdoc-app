from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.schemas.api_key import APIKeyCreate, APIKeyCreated, APIKeyOut
from app.services import api_key_service
from app.services import audit_service

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("")
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("api_keys.manage")),
):
    keys = await api_key_service.list_keys(db, str(current_user.org_id))
    return {"data": [APIKeyOut.model_validate(k) for k in keys], "error": None}


@router.post("", status_code=201)
async def create_api_key(
    request: Request,
    data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("api_keys.manage")),
):
    key, raw_key = await api_key_service.create_key(
        db,
        org_id=str(current_user.org_id),
        created_by=str(current_user.id),
        name=data.name,
        scopes=data.scopes,
        expires_at=data.expires_at,
    )
    await audit_service.log(
        db,
        org_id=str(current_user.org_id),
        action="api_key.created",
        entity_type="api_key",
        entity_id=str(key.id),
        actor_label=current_user.email,
        entity_label=key.name,
        diff={"name": key.name, "scopes": key.scopes},
        user_id=str(current_user.id),
        request=request,
    )
    out = APIKeyCreated(**APIKeyOut.model_validate(key).model_dump(), raw_key=raw_key)
    return {"data": out, "error": None}


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    request: Request,
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("api_keys.manage")),
):
    key = await api_key_service.get_key(db, str(current_user.org_id), key_id)
    await audit_service.log(
        db,
        org_id=str(current_user.org_id),
        action="api_key.revoked",
        entity_type="api_key",
        entity_id=str(key.id),
        actor_label=current_user.email,
        entity_label=key.name,
        risk_level="high",
        user_id=str(current_user.id),
        request=request,
    )
    await api_key_service.revoke_key(db, key)
