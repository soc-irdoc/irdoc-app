"""
Integration service — CRUD for org_integrations, credential encryption/decryption.
All integration credentials are Fernet-encrypted at rest and NEVER returned via API.
"""
import json
import logging
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.integration import OrgIntegration
from app.plugins.registry import PLUGINS, list_plugins

logger = logging.getLogger(__name__)


def _fernet() -> Fernet:
    # Derive a 32-byte Fernet key from SECRET_KEY (pad/truncate to 32 bytes, then base64url)
    import base64
    raw = settings.SECRET_KEY.encode()[:32].ljust(32, b"\x00")
    return Fernet(base64.urlsafe_b64encode(raw))


def encrypt_config(config: dict) -> dict:
    """Encrypt all password-type fields in config. Other fields stored plaintext."""
    f = _fernet()
    encrypted = {}
    for k, v in config.items():
        if v and isinstance(v, str):
            # Encrypt every non-empty string value to avoid leakage
            encrypted[k] = f.encrypt(v.encode()).decode()
        else:
            encrypted[k] = v
    return encrypted


def decrypt_config(encrypted: dict) -> dict:
    """Decrypt all values back to plaintext."""
    f = _fernet()
    result = {}
    for k, v in encrypted.items():
        if v and isinstance(v, str):
            try:
                result[k] = f.decrypt(v.encode()).decode()
            except Exception:
                result[k] = v  # Already plain (legacy / migration)
        else:
            result[k] = v
    return result


async def list_integrations(org_id: str, db: AsyncSession) -> list[dict]:
    """
    Return all plugins with their per-org configuration status.
    Config values are never included in the response.
    """
    all_plugins = list_plugins()

    # Load all existing org integration records
    result = await db.execute(
        select(OrgIntegration).where(OrgIntegration.org_id == org_id)
    )
    org_configs = {row.plugin_name: row for row in result.scalars().all()}

    output = []
    for plugin_meta in all_plugins:
        name = plugin_meta["name"]
        record = org_configs.get(name)

        # Return non-password config fields so the UI can pre-populate them.
        # Password fields are never included.
        safe_config: dict = {}
        if record and record.config:
            full_config = decrypt_config(record.config)
            schema = plugin_meta.get("config_schema", {})
            for field_key, field_def in schema.items():
                if field_def.get("type") != "password" and field_key in full_config:
                    safe_config[field_key] = full_config[field_key]

        output.append({
            **plugin_meta,
            "is_enabled": record.is_enabled if record else False,
            "is_configured": bool(record and record.config),
            "last_tested": record.last_tested.isoformat() if record and record.last_tested else None,
            "last_test_status": record.last_test_status if record else None,
            "last_error": record.last_error if record else None,
            "config_values": safe_config,
        })
    return output


async def get_integration(org_id: str, plugin_name: str, db: AsyncSession) -> OrgIntegration | None:
    result = await db.execute(
        select(OrgIntegration).where(
            OrgIntegration.org_id == org_id,
            OrgIntegration.plugin_name == plugin_name,
        )
    )
    return result.scalar_one_or_none()


async def save_integration_config(
    org_id: str, plugin_name: str, config: dict, db: AsyncSession
) -> OrgIntegration:
    """Save (upsert) integration config. Encrypts all values before storing."""
    encrypted = encrypt_config(config)
    existing = await get_integration(org_id, plugin_name, db)
    if existing:
        existing.config = encrypted
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        return existing

    record = OrgIntegration(
        org_id=org_id,
        plugin_name=plugin_name,
        config=encrypted,
        is_enabled=False,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def toggle_integration(
    org_id: str, plugin_name: str, enabled: bool, db: AsyncSession
) -> OrgIntegration | None:
    record = await get_integration(org_id, plugin_name, db)
    if not record:
        return None
    record.is_enabled = enabled
    record.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return record


async def test_integration_connection(
    org_id: str, plugin_name: str, db: AsyncSession
) -> dict:
    """Test the connection for a plugin. Updates last_tested + last_test_status."""
    record = await get_integration(org_id, plugin_name, db)
    if not record:
        return {"ok": False, "error": "Integration not configured"}

    plugin_cls = PLUGINS.get(plugin_name)
    if not plugin_cls:
        return {"ok": False, "error": "Plugin not found"}

    config = decrypt_config(record.config)
    try:
        plugin = plugin_cls()
        ok = await plugin.test_connection(config)
        status = "ok" if ok else "fail"
        error = None if ok else "Connection test returned False"
    except Exception as exc:
        ok = False
        status = "fail"
        error = str(exc)[:200]

    record.last_tested = datetime.now(timezone.utc)
    record.last_test_status = status
    record.last_error = error
    record.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"ok": ok, "error": error}


async def get_enabled_plugins_for_org(org_id: str, category: str, db: AsyncSession) -> list[tuple]:
    """
    Return [(plugin_instance, config_dict)] for all enabled plugins in a category.
    Used by enrichment + notification services.
    """
    result = await db.execute(
        select(OrgIntegration).where(
            OrgIntegration.org_id == org_id,
            OrgIntegration.is_enabled == True,  # noqa: E712
        )
    )
    records = result.scalars().all()

    output = []
    for record in records:
        plugin_cls = PLUGINS.get(record.plugin_name)
        if not plugin_cls:
            continue
        if getattr(plugin_cls, "category", "") != category:
            continue
        config = decrypt_config(record.config)
        output.append((plugin_cls(), config))
    return output
