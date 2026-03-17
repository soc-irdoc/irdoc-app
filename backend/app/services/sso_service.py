"""SSO/SAML config management — reading and writing org SSO settings."""
import uuid as _uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sso_config import SSOConfig


async def get_sso_config(db: AsyncSession, org_id: str) -> SSOConfig | None:
    """Return the SSO config for an org, or None if not configured."""
    result = await db.execute(
        select(SSOConfig).where(SSOConfig.org_id == _uuid.UUID(str(org_id)))
    )
    return result.scalar_one_or_none()


async def upsert_sso_config(
    db: AsyncSession, org_id: str, data: dict
) -> SSOConfig:
    """Create or update the SSO config for an org."""
    from datetime import datetime, timezone

    existing = await get_sso_config(db, org_id)
    if existing:
        for key, value in data.items():
            if value is not None and hasattr(existing, key):
                setattr(existing, key, value)
        existing.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return existing

    config = SSOConfig(
        org_id=_uuid.UUID(str(org_id)),
        **{k: v for k, v in data.items() if hasattr(SSOConfig, k) and v is not None},
    )
    db.add(config)
    await db.flush()
    return config


async def get_saml_settings(sso_config: SSOConfig, base_url: str) -> dict:
    """Return a python3-saml settings dict built from the stored SSOConfig."""
    base = base_url.rstrip("/")
    return {
        "strict": True,
        "debug": False,
        "sp": {
            "entityId": f"{base}/auth/saml/metadata",
            "assertionConsumerService": {
                "url": f"{base}/auth/saml/acs",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
        },
        "idp": {
            "entityId": sso_config.entity_id or "",
            "singleSignOnService": {
                "url": sso_config.sso_url or "",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "x509cert": sso_config.certificate or "",
        },
    }
