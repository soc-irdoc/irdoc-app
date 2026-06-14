"""
API key lifecycle: creation (argon2id hash), listing, revocation.
Keys are shown exactly once at creation. Stored as hash only.
"""
import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_api_key
from app.models.api_key import APIKey

VALID_SCOPES = {
    "incidents:create",
    "incidents:read",
    "incidents:write",
    "timeline:read",
    "iocs:read",
    "reports:read",
}


async def create_key(
    db: AsyncSession,
    org_id: str,
    created_by: str,
    name: str,
    scopes: list[str],
    expires_at: datetime | None = None,
) -> tuple[APIKey, str]:
    invalid = set(scopes) - VALID_SCOPES
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scopes: {invalid}. Valid: {VALID_SCOPES}",
        )

    raw_key, key_prefix, key_hash = generate_api_key()
    api_key = APIKey(
        org_id=org_id,
        created_by=created_by,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=scopes,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.flush()
    return api_key, raw_key


async def list_keys(db: AsyncSession, org_id: str) -> list[APIKey]:
    result = await db.execute(
        select(APIKey).where(APIKey.org_id == org_id, APIKey.is_active == True)  # noqa: E712
    )
    return list(result.scalars().all())


async def get_key(db: AsyncSession, org_id: str, key_id: str) -> APIKey:
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.org_id == org_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return key


async def revoke_key(db: AsyncSession, org_id: str, key_id: str) -> None:
    key = await get_key(db, org_id, key_id)
    key.is_active = False
    await db.flush()
