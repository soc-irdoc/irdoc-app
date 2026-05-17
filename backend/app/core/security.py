"""
JWT auth + API key auth + password hashing.

Access token:  15-min JWT, stored in Zustand (memory only)
Refresh token: 30-day JWT, stored in HttpOnly SameSite=Strict cookie
API keys:      irp_key_{random_32_hex} — argon2id hashed in DB, never stored plain
"""
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Cookie, Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)

ALGORITHM = "HS256"
API_KEY_PREFIX = "irp_key_"

bearer_scheme = HTTPBearer(auto_error=False)


# ─── Password ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def needs_rehash(hashed: str) -> bool:
    return ph.check_needs_rehash(hashed)


# ─── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(subject: str, org_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": subject, "org": org_id, "exp": expire, "type": "access"},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_refresh_token(subject: str, org_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": subject, "org": org_id, "exp": expire, "type": "refresh"},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_mfa_challenge_token(user_id: str, org_id: str) -> str:
    """Short-lived token for users who need to complete TOTP verification."""
    expire = datetime.now(UTC) + timedelta(minutes=5)
    return jwt.encode(
        {"sub": str(user_id), "org": str(org_id), "exp": expire, "type": "mfa_challenge"},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_mfa_setup_token(user_id: str, org_id: str) -> str:
    """Short-lived token for users who need to enroll MFA (org policy requires it)."""
    expire = datetime.now(UTC) + timedelta(minutes=10)
    return jwt.encode(
        {"sub": str(user_id), "org": str(org_id), "exp": expire, "type": "mfa_setup"},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_token(token: str, expected_type: str = "access") -> dict:
    """Raises HTTPException on invalid / expired token or wrong token type."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    return payload


# ─── API Keys ──────────────────────────────────────────────────────────────────

def generate_api_key() -> tuple[str, str, str]:
    """Return (raw_key, key_prefix, key_hash). Store hash only."""
    raw_key = f"{API_KEY_PREFIX}{secrets.token_hex(32)}"
    key_prefix = raw_key[:16]  # "irp_key_a3f92b..." — shown in UI
    key_hash = ph.hash(raw_key)
    return raw_key, key_prefix, key_hash


def verify_api_key_hash(raw_key: str, key_hash: str) -> bool:
    try:
        return ph.verify(key_hash, raw_key)
    except VerifyMismatchError:
        return False


# ─── Signed File Tokens (local storage) ────────────────────────────────────────

def sign_file_token(path: str, expires_in: int = 3600) -> str:
    expire = int((datetime.now(UTC) + timedelta(seconds=expires_in)).timestamp())
    payload = f"{path}:{expire}"
    sig = hmac.new(settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    import base64
    token_data = f"{payload}:{sig}"
    return base64.urlsafe_b64encode(token_data.encode()).decode()


def verify_file_token(token: str) -> str | None:
    """Returns path if valid/not-expired, else None."""
    import base64
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        path, expire_str, sig = decoded.rsplit(":", 2)
        payload = f"{path}:{expire_str}"
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        if int(expire_str) < datetime.now(UTC).timestamp():
            return None
        return path
    except Exception:
        return None


# ─── FastAPI Dependencies ───────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User  # avoid circular import

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))  # noqa: E712
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_user_from_cookie(
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User  # avoid circular import

    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")
    payload = decode_token(refresh_token, expected_type="refresh")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))  # noqa: E712
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_api_key_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Validate Authorization: ApiKey irp_key_xxx header."""
    from app.models.api_key import APIKey  # avoid circular import

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("ApiKey "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required (Authorization: ApiKey irp_key_...)",
        )
    raw_key = auth_header[len("ApiKey "):]
    if not raw_key.startswith(API_KEY_PREFIX):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key format")

    prefix = raw_key[:16]
    from datetime import datetime as dt
    result = await db.execute(
        select(APIKey).where(
            APIKey.key_prefix == prefix,
            APIKey.is_active == True,  # noqa: E712
        )
    )
    candidates = result.scalars().all()
    for candidate in candidates:
        if candidate.expires_at and candidate.expires_at < dt.now(UTC):
            continue
        if verify_api_key_hash(raw_key, candidate.key_hash):
            candidate.last_used_at = dt.now(UTC)
            await db.flush()
            return candidate

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API key")


def require_scope(scope: str):
    """Dependency factory: requires a specific scope on the API key."""
    async def _check(api_key=Depends(get_api_key_auth)):
        if scope not in (api_key.scopes or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key missing required scope: {scope}",
            )
        return api_key
    return _check
