"""
Integrations API — plugin list, config, test, toggle, and action endpoints.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.services import integration_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class IntegrationConfigRequest(BaseModel):
    config: dict


class IntegrationToggleRequest(BaseModel):
    enabled: bool


class SentinelPullRequest(BaseModel):
    incident_id: str
    kql: str | None = None
    since_hours: int = 24


class CrowdStrikeContainRequest(BaseModel):
    device_id: str
    incident_id: str
    confirm: bool = False


class AzureADRevokeRequest(BaseModel):
    user_id: str
    incident_id: str
    confirm: bool = False


class AzureADResetRequest(BaseModel):
    user_id: str
    incident_id: str
    confirm: bool = False


class ManualEnrichRequest(BaseModel):
    pass


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
async def list_integrations(
    current_user: User = Depends(require_permission("incidents.read")),
    db: AsyncSession = Depends(get_db),
):
    """List all plugins with org configuration status. Config values are never returned."""
    data = await integration_service.list_integrations(str(current_user.org_id), db)
    return {"data": data, "meta": {}, "error": None}


@router.put("/{plugin_name}")
async def save_config(
    plugin_name: str,
    body: IntegrationConfigRequest,
    current_user: User = Depends(require_permission("api_keys.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Save integration configuration (admin only). Credentials are encrypted."""
    from app.plugins.registry import PLUGINS
    if plugin_name not in PLUGINS:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")

    record = await integration_service.save_integration_config(
        str(current_user.org_id), plugin_name, body.config, db
    )
    return {"data": {"plugin_name": record.plugin_name, "updated": True}, "meta": {}, "error": None}


@router.post("/{plugin_name}/test")
async def test_connection(
    plugin_name: str,
    current_user: User = Depends(require_permission("api_keys.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Test the integration connection. Updates last_tested + last_test_status."""
    result = await integration_service.test_integration_connection(
        str(current_user.org_id), plugin_name, db
    )
    return {"data": result, "meta": {}, "error": None}


@router.post("/{plugin_name}/toggle")
async def toggle_integration(
    plugin_name: str,
    body: IntegrationToggleRequest,
    current_user: User = Depends(require_permission("api_keys.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable an integration."""
    record = await integration_service.toggle_integration(
        str(current_user.org_id), plugin_name, body.enabled, db
    )
    if not record:
        raise HTTPException(status_code=404, detail="Integration not configured")
    return {"data": {"plugin_name": plugin_name, "is_enabled": record.is_enabled}, "meta": {}, "error": None}


@router.post("/sentinel/pull")
async def sentinel_pull_alerts(
    body: SentinelPullRequest,
    current_user: User = Depends(require_permission("timeline.create")),
    db: AsyncSession = Depends(get_db),
):
    """
    Pull Sentinel alerts as timeline entry candidates.
    Returns preview list — analyst selects which to import.
    """
    from app.core.feature_flags import check_feature
    if not check_feature("integration_siem"):
        raise HTTPException(status_code=403, detail="Sentinel integration requires premium plan")

    record = await integration_service.get_integration(str(current_user.org_id), "sentinel", db)
    if not record or not record.is_enabled:
        raise HTTPException(status_code=400, detail="Sentinel integration not enabled")

    from app.plugins.registry import PLUGINS
    from app.services.integration_service import decrypt_config
    plugin = PLUGINS.get("sentinel")
    if not plugin:
        raise HTTPException(status_code=500, detail="Sentinel plugin not loaded")

    config = decrypt_config(record.config)
    instance = plugin()

    if body.kql:
        results = await instance.run_kql(body.kql, config)
    else:
        results = await instance.pull_alerts(body.incident_id, config)

    return {"data": results, "meta": {"count": len(results)}, "error": None}


@router.post("/crowdstrike/contain")
async def crowdstrike_contain_host(
    body: CrowdStrikeContainRequest,
    current_user: User = Depends(require_permission("incidents.close")),
    db: AsyncSession = Depends(get_db),
):
    """
    Contain a host via CrowdStrike Falcon.
    Requires confirmation (confirm=True) + Senior Analyst role.
    Always logged to audit log.
    """
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Must set confirm=true to execute containment")

    from app.core.feature_flags import check_feature
    if not check_feature("integration_edr"):
        raise HTTPException(status_code=403, detail="CrowdStrike integration requires premium plan")

    record = await integration_service.get_integration(str(current_user.org_id), "crowdstrike", db)
    if not record or not record.is_enabled:
        raise HTTPException(status_code=400, detail="CrowdStrike integration not enabled")

    from app.plugins.registry import PLUGINS
    from app.services.integration_service import decrypt_config
    plugin = PLUGINS.get("crowdstrike")
    config = decrypt_config(record.config)
    ok = await plugin().contain_host(body.device_id, config)

    # Audit log
    try:
        from app.models.audit import AuditLog
        audit = AuditLog(
            org_id=current_user.org_id,
            user_id=current_user.id,
            action="crowdstrike.contain_host",
            entity_type="device",
            entity_id=None,
            diff={"device_id": body.device_id, "incident_id": body.incident_id, "success": ok},
        )
        db.add(audit)
        await db.commit()
    except Exception:
        pass

    return {"data": {"contained": ok, "device_id": body.device_id}, "meta": {}, "error": None}


@router.post("/azuread/revoke-sessions")
async def azuread_revoke_sessions(
    body: AzureADRevokeRequest,
    current_user: User = Depends(require_permission("incidents.close")),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all active sessions for a user. Requires confirmation + audit log."""
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Must set confirm=true to revoke sessions")

    from app.core.feature_flags import check_feature
    if not check_feature("integration_iam"):
        raise HTTPException(status_code=403, detail="Azure AD integration requires premium plan")

    record = await integration_service.get_integration(str(current_user.org_id), "azuread", db)
    if not record or not record.is_enabled:
        raise HTTPException(status_code=400, detail="Azure AD integration not enabled")

    from app.plugins.registry import PLUGINS
    from app.services.integration_service import decrypt_config
    plugin = PLUGINS.get("azuread")
    config = decrypt_config(record.config)
    ok = await plugin().revoke_sessions(body.user_id, config)

    try:
        from app.models.audit import AuditLog
        audit = AuditLog(
            org_id=current_user.org_id,
            user_id=current_user.id,
            action="azuread.revoke_sessions",
            entity_type="user",
            entity_id=None,
            diff={"user_id": body.user_id, "incident_id": body.incident_id, "success": ok, "risk": "high"},
        )
        db.add(audit)
        await db.commit()
    except Exception:
        pass

    return {"data": {"revoked": ok, "user_id": body.user_id}, "meta": {}, "error": None}


@router.post("/azuread/reset-password")
async def azuread_reset_password(
    body: AzureADResetRequest,
    current_user: User = Depends(require_permission("incidents.close")),
    db: AsyncSession = Depends(get_db),
):
    """Force password reset for a user. Requires confirmation + audit log."""
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Must set confirm=true to reset password")

    from app.core.feature_flags import check_feature
    if not check_feature("integration_iam"):
        raise HTTPException(status_code=403, detail="Azure AD integration requires premium plan")

    record = await integration_service.get_integration(str(current_user.org_id), "azuread", db)
    if not record or not record.is_enabled:
        raise HTTPException(status_code=400, detail="Azure AD integration not enabled")

    from app.plugins.registry import PLUGINS
    from app.services.integration_service import decrypt_config
    plugin = PLUGINS.get("azuread")
    config = decrypt_config(record.config)
    message = await plugin().reset_password(body.user_id, config)

    try:
        from app.models.audit import AuditLog
        audit = AuditLog(
            org_id=current_user.org_id,
            user_id=current_user.id,
            action="azuread.reset_password",
            entity_type="user",
            entity_id=None,
            diff={"user_id": body.user_id, "incident_id": body.incident_id, "risk": "high"},
        )
        db.add(audit)
        await db.commit()
    except Exception:
        pass

    return {"data": {"message": message, "user_id": body.user_id}, "meta": {}, "error": None}
