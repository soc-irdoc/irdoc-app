"""SSO/OIDC config management - reading and writing org SSO settings."""
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

    # Encrypt client_secret before persisting - only when a new value is supplied
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


# ─── Role mapping (Refs #172) ────────────────────────────────────────────────

def _mapping_candidates(claims: dict) -> set[str]:
    """Every token value a role mapping may be keyed on: group object IDs
    (`groups`), app roles (`roles`) and the user's own object ID (`oid`)."""
    values: list = []
    for claim in ("groups", "roles"):
        raw = claims.get(claim) or []
        values.extend(raw if isinstance(raw, list) else [raw])
    if claims.get("oid"):
        values.append(claims["oid"])
    return {str(v).strip().lower() for v in values if v}


def resolve_sso_role(claims: dict, role_mappings: dict | None) -> str | None:
    """Role an SSO sign-in maps to, or None when no mapping matches.

    When several mappings match, the most privileged role wins. Mapping keys
    are compared case- and whitespace-insensitively (GUIDs are pasted by hand),
    and mappings to unknown roles are ignored.
    """
    from app.core.permissions import ROLE_HIERARCHY

    if not role_mappings:
        return None
    candidates = _mapping_candidates(claims)
    matched = [
        role
        for key, role in role_mappings.items()
        if str(key).strip().lower() in candidates and role in ROLE_HIERARCHY
    ]
    if not matched:
        return None
    return max(matched, key=ROLE_HIERARCHY.__getitem__)


async def provision_oidc_user(
    db: AsyncSession,
    *,
    org,
    email: str,
    full_name: str,
    mapped_role: str | None,
):
    """Create or update the user behind an SSO sign-in.

    A matched role mapping is applied on every sign-in, so Entra stays the source
    of truth for mapped users. Without a match, a new user gets "analyst" and an
    existing user keeps whatever role they have (e.g. one set by hand).
    """
    import logging
    import secrets

    from app.services import audit_service, auth_service

    logger = logging.getLogger(__name__)

    user = await auth_service.get_user_by_email(db, email)
    if user is None:
        user = await auth_service.register_user(
            db,
            email=email,
            full_name=full_name,
            password=secrets.token_urlsafe(32),
            org_id=str(org.id),
            role=mapped_role or "analyst",
        )
        user.auth_provider = "oidc"
        return user

    if full_name and user.full_name != full_name:
        user.full_name = full_name
        initials = "".join(p[0].upper() for p in full_name.split()[:2])
        user.avatar_initials = initials or full_name[:2].upper()
    user.auth_provider = "oidc"

    if not mapped_role or user.role == mapped_role:
        return user

    # Only sync roles onto accounts in the org this SSO config belongs to
    if str(user.org_id) != str(org.id):
        logger.warning("SSO role mapping skipped for %s: account belongs to another org", email)
        return user

    # Same invariant as the manual role endpoint: never demote the last admin
    if user.role == "admin" and mapped_role != "admin":
        from sqlalchemy import func

        from app.models.user import User

        admin_count = (await db.execute(
            select(func.count()).select_from(User).where(
                User.org_id == user.org_id,
                User.role == "admin",
                User.is_active == True,  # noqa: E712
            )
        )).scalar() or 0
        if admin_count <= 1:
            logger.warning(
                "SSO role mapping would demote %s, the last admin, to %s - keeping admin",
                email, mapped_role,
            )
            return user

    old_role = user.role
    user.role = mapped_role
    logger.info("SSO role mapping changed %s from %s to %s", email, old_role, mapped_role)
    await audit_service.log(
        db,
        org_id=str(user.org_id),
        user_id=str(user.id),
        actor_label="SSO",
        action="user.role_changed",
        entity_type="user",
        entity_id=str(user.id),
        entity_label=email,
        diff={"old_role": old_role, "new_role": mapped_role, "via": "sso"},
    )
    return user
