"""
SMTP configuration service — get/upsert per-org config with encrypted password.
"""
import uuid
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.smtp_config import SmtpConfig
from app.services.integration_service import _fernet

logger = logging.getLogger(__name__)


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except Exception:
        return value  # legacy / already plain


async def get_smtp_config(db: AsyncSession, org_id: str) -> SmtpConfig | None:
    result = await db.execute(
        select(SmtpConfig).where(SmtpConfig.org_id == uuid.UUID(org_id))
    )
    return result.scalar_one_or_none()


async def upsert_smtp_config(db: AsyncSession, org_id: str, data: dict) -> SmtpConfig:
    """
    Create or update the SMTP config for an org.
    If `password` key is absent or None in `data`, the existing encrypted value is kept.
    """
    config = await get_smtp_config(db, org_id)

    new_password = data.pop("password", None)

    if config is None:
        config = SmtpConfig(org_id=uuid.UUID(org_id))
        db.add(config)

    for key, value in data.items():
        if hasattr(config, key):
            setattr(config, key, value)

    if new_password:
        config.password_encrypted = _encrypt(new_password)

    await db.commit()
    await db.refresh(config)
    return config


def get_decrypted_password(config: SmtpConfig) -> str:
    if not config.password_encrypted:
        return ""
    return _decrypt(config.password_encrypted)
