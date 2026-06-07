"""
SMTP configuration endpoints — get, upsert, test.
"""
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.services import smtp_config_service
from app.services.email_service import send_email_with_config

router = APIRouter(prefix="/admin/smtp", tags=["smtp"])
logger = logging.getLogger(__name__)


class SmtpConfigPayload(BaseModel):
    is_enabled: bool | None = None
    host: str | None = None
    port: int | None = None
    use_tls: bool | None = None
    username: str | None = None
    password: str | None = None  # None = keep existing
    from_name: str | None = None
    from_address: str | None = None
    subject_template: str | None = None
    logo_url: str | None = None
    accent_color: str | None = None
    footer_text: str | None = None


class SmtpTestPayload(BaseModel):
    host: str
    port: int = 587
    use_tls: bool = True
    username: str | None = None
    password: str | None = None
    from_name: str | None = None
    from_address: str | None = None


def _config_to_dict(cfg) -> dict:
    return {
        "is_enabled": cfg.is_enabled,
        "host": cfg.host,
        "port": cfg.port,
        "use_tls": cfg.use_tls,
        "username": cfg.username,
        "password": "••••••" if cfg.password_encrypted else "",
        "from_name": cfg.from_name,
        "from_address": cfg.from_address,
        "subject_template": cfg.subject_template,
        "logo_url": cfg.logo_url,
        "accent_color": cfg.accent_color,
        "footer_text": cfg.footer_text,
    }


@router.get("")
async def get_smtp_config(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("org.manage")),
):
    config = await smtp_config_service.get_smtp_config(db, str(current_user.org_id))
    data = _config_to_dict(config) if config else None
    return {"data": data, "error": None}


@router.put("")
async def save_smtp_config(
    payload: SmtpConfigPayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("org.manage")),
):
    data = payload.model_dump(exclude_none=True)
    config = await smtp_config_service.upsert_smtp_config(db, str(current_user.org_id), data)
    return {"data": _config_to_dict(config), "error": None}


@router.post("/test")
async def test_smtp(
    payload: SmtpTestPayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("org.manage")),
):
    """Send a test email to the calling admin's address using the provided (unsaved) settings."""
    from_addr = f"{payload.from_name} <{payload.from_address}>" if payload.from_name and payload.from_address else (payload.from_address or "noreply@localhost")
    subject = "IRDoc SMTP Test"
    html_body = (
        "<p>This is a test email from IRDoc. If you received it, your SMTP configuration is working.</p>"
    )
    try:
        await send_email_with_config(
            to=current_user.email,
            subject=subject,
            html_body=html_body,
            host=payload.host,
            port=payload.port,
            use_tls=payload.use_tls,
            username=payload.username or None,
            password=payload.password or None,
            from_addr=from_addr,
        )
        return {"data": {"ok": True, "error": None}, "error": None}
    except Exception as exc:
        logger.warning("SMTP test failed: %s", exc)
        return {"data": {"ok": False, "error": str(exc)}, "error": None}
