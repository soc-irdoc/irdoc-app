"""
Admin endpoints — org settings, cloud storage config, SSO config.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.feature_flags import check_feature
from app.core.permissions import require_permission
from app.models.organization import Organization
from app.models.storage import StorageConfig
from app.schemas.admin import (
    OrgSettingsUpdate,
    SSOConfigOut,
    SSOConfigUpdate,
    StorageConfigCreate,
    StorageConfigOut,
)
from app.services import audit_service, sso_service
from app.services.integration_service import decrypt_config, encrypt_config
from app.services.storage.resolver import (
    get_storage_backend,
    get_storage_backend_from_config,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Org settings ──────────────────────────────────────────────────────────────

@router.get("/org")
async def get_org(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    """Get org settings."""
    result = await db.execute(
        select(Organization).where(
            Organization.id == uuid.UUID(str(current_user.org_id))
        )
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")

    return {
        "data": {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "plan": org.plan,
            "settings": org.settings or {},
        },
        "error": None,
    }


@router.patch("/org")
@router.put("/org")
async def update_org(
    data: OrgSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    """Update org settings."""
    result = await db.execute(
        select(Organization).where(
            Organization.id == uuid.UUID(str(current_user.org_id))
        )
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")

    changes: dict = {}
    if data.name is not None:
        changes["name"] = data.name
        org.name = data.name

    settings_patch: dict = dict(org.settings or {})
    if data.allow_registration is not None:
        settings_patch["allow_registration"] = data.allow_registration
        changes["allow_registration"] = data.allow_registration
    if data.invite_only is not None:
        settings_patch["invite_only"] = data.invite_only
        changes["invite_only"] = data.invite_only
    if data.mfa_required is not None:
        settings_patch["mfa_required"] = data.mfa_required
        changes["mfa_required"] = data.mfa_required
    if data.logo_url is not None:
        settings_patch["logo_url"] = data.logo_url
        changes["logo_url"] = data.logo_url
    if data.accent_color is not None:
        settings_patch["accent_color"] = data.accent_color
        changes["accent_color"] = data.accent_color

    if settings_patch:
        org.settings = settings_patch

    await db.flush()
    await db.commit()

    if changes:
        await audit_service.log(
            db,
            org_id=str(current_user.org_id),
            user_id=str(current_user.id),
            action="org.settings_updated",
            entity_type="organization",
            entity_id=str(org.id),
            diff=changes,
        )
        await db.commit()

    return {
        "data": {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "plan": org.plan,
            "settings": org.settings or {},
        },
        "error": None,
    }


# ── Storage config ────────────────────────────────────────────────────────────

@router.get("/storage")
async def get_storage_config(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("storage.manage")),
):
    """Get the current storage config (config values redacted)."""
    result = await db.execute(
        select(StorageConfig).where(
            StorageConfig.org_id == uuid.UUID(str(current_user.org_id))
        )
    )
    config_row = result.scalar_one_or_none()
    if not config_row:
        return {"data": None, "error": None}

    return {
        "data": StorageConfigOut.model_validate(config_row),
        "error": None,
    }


@router.put("/storage")
async def update_storage_config(
    data: StorageConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("storage.manage")),
):
    """Save (but do not activate) a storage config. Config is Fernet-encrypted."""
    if not check_feature("cloud_storage"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Cloud storage requires a pro or enterprise license",
        )

    encrypted_cfg = encrypt_config({k: str(v) if not isinstance(v, str) else v
                                     for k, v in data.config.items()})

    result = await db.execute(
        select(StorageConfig).where(
            StorageConfig.org_id == uuid.UUID(str(current_user.org_id))
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.backend = data.backend
        existing.config = encrypted_cfg
        await db.flush()
        row = existing
    else:
        row = StorageConfig(
            org_id=uuid.UUID(str(current_user.org_id)),
            backend=data.backend,
            config=encrypted_cfg,
            is_active=False,
        )
        db.add(row)
        await db.flush()

    await db.commit()

    await audit_service.log(
        db,
        org_id=str(current_user.org_id),
        user_id=str(current_user.id),
        action="storage.config_updated",
        entity_type="storage_config",
        entity_id=str(row.id),
        diff={"backend": data.backend},
    )
    await db.commit()

    return {"data": StorageConfigOut.model_validate(row), "error": None}


@router.post("/storage/test")
async def test_storage_config(
    data: StorageConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("storage.manage")),
):
    """Test connectivity with the provided (unsaved) storage config."""
    if not check_feature("cloud_storage"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Cloud storage requires a pro or enterprise license",
        )

    # Build a temporary config row-like object for the resolver
    class _TempConfig:
        def __init__(self, backend: str, cfg: dict):
            self.backend = backend
            self.config = cfg

    try:
        backend_instance = get_storage_backend_from_config(
            _TempConfig(data.backend, data.config)
        )
        ok = await backend_instance.test_connection()
        return {"data": {"ok": ok, "error": None if ok else "Connection test failed"}, "error": None}
    except Exception as exc:
        return {"data": {"ok": False, "error": str(exc)[:200]}, "error": None}


@router.post("/storage/switch")
async def switch_storage_backend(
    data: StorageConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("storage.manage")),
):
    """Save, activate, and clear resolver cache for the new storage backend."""
    if not check_feature("cloud_storage"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Cloud storage requires a pro or enterprise license",
        )

    encrypted_cfg = encrypt_config({k: str(v) if not isinstance(v, str) else v
                                     for k, v in data.config.items()})

    result = await db.execute(
        select(StorageConfig).where(
            StorageConfig.org_id == uuid.UUID(str(current_user.org_id))
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.backend = data.backend
        existing.config = encrypted_cfg
        existing.is_active = True
        await db.flush()
        row = existing
    else:
        row = StorageConfig(
            org_id=uuid.UUID(str(current_user.org_id)),
            backend=data.backend,
            config=encrypted_cfg,
            is_active=True,
        )
        db.add(row)
        await db.flush()

    await db.commit()

    # Clear the resolver cache so next request picks up the new backend
    get_storage_backend.cache_clear()

    await audit_service.log(
        db,
        org_id=str(current_user.org_id),
        user_id=str(current_user.id),
        action="storage.backend_switched",
        entity_type="storage_config",
        entity_id=str(row.id),
        diff={"backend": data.backend},
        risk_level="high",
    )
    await db.commit()

    return {"data": {"ok": True, "backend": data.backend}, "error": None}


# ── SSO config ────────────────────────────────────────────────────────────────

@router.get("/sso")
async def get_sso(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    """Get SSO config (certificate redacted). Enterprise only."""
    if not check_feature("sso_saml"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="SSO/SAML requires an enterprise license",
        )

    cfg = await sso_service.get_sso_config(db, str(current_user.org_id))
    if not cfg:
        return {"data": None, "error": None}

    return {"data": SSOConfigOut.model_validate(cfg), "error": None}


@router.put("/sso")
async def update_sso(
    data: SSOConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    """Create or update SSO config. Enterprise only."""
    if not check_feature("sso_saml"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="SSO/SAML requires an enterprise license",
        )

    patch = data.model_dump(exclude_none=True)
    cfg = await sso_service.upsert_sso_config(db, str(current_user.org_id), patch)
    await db.commit()

    await audit_service.log(
        db,
        org_id=str(current_user.org_id),
        user_id=str(current_user.id),
        action="sso.config_updated",
        entity_type="sso_config",
        entity_id=str(cfg.id),
        diff={k: v for k, v in patch.items() if k != "certificate"},
    )
    await db.commit()

    return {"data": SSOConfigOut.model_validate(cfg), "error": None}
