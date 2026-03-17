from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.schemas.api_key import APIKeyCreate, APIKeyCreated, APIKeyOut
from app.services import api_key_service

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=list[APIKeyOut])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("api_keys.manage")),
):
    keys = await api_key_service.list_keys(db, str(current_user.org_id))
    return [APIKeyOut.model_validate(k) for k in keys]


@router.post("", response_model=APIKeyCreated, status_code=201)
async def create_api_key(
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
    out = APIKeyCreated.model_validate(key)
    out.raw_key = raw_key
    return out


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("api_keys.manage")),
):
    await api_key_service.revoke_key(db, str(current_user.org_id), key_id)
