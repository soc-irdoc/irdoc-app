"""SSO/OIDC config management — reading and writing org SSO settings."""
import base64
import uuid as _uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sso_config import SSOConfig


def _fernet():
    """
    Derive a Fernet key from SECRET_KEY using HKDF-SHA256 with a domain-specific
    info label. HKDF ensures the derived key is uniformly distributed regardless
    of the input key's format, and the label isolates it from other derived keys.
    """
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    from app.core.config import settings

    key_material = settings.SECRET_KEY.encode()
    derived = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"irdoc-sso-client-secret-v1",
    ).derive(key_material)
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_client_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_client_secret(encrypted: str) -> str:
    return _fernet().decrypt(encrypted.encode()).decode()


async def get_sso_config(db: AsyncSession, org_id: str) -> SSOConfig | None:
    result = await db.execute(
        select(SSOConfig).where(SSOConfig.org_id == _uuid.UUID(str(org_id)))
    )
    return result.scalar_one_or_none()


async def upsert_sso_config(db: AsyncSession, org_id: str, data: dict) -> SSOConfig:
    from datetime import datetime, timezone

    # Encrypt client_secret before persisting — only when a new value is supplied
    if data.get("client_secret"):
        data = dict(data)
        data["client_secret"] = encrypt_client_secret(data["client_secret"])

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
