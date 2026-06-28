"""
AI configuration endpoints — get, upsert, test Ollama connection.
"""
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.services import ai_config_service

router = APIRouter(prefix="/admin/ai", tags=["ai"])
logger = logging.getLogger(__name__)


class AiConfigPayload(BaseModel):
    is_enabled: bool | None = None
    ollama_base_url: str | None = None
    model_name: str | None = None
    debounce_seconds: int | None = Field(default=None, ge=10, le=3600)
    max_timeline_events: int | None = Field(default=None, ge=1, le=200)


class AiTestPayload(BaseModel):
    ollama_base_url: str
    model_name: str


def _config_to_dict(cfg) -> dict:
    return {
        "is_enabled": cfg.is_enabled,
        "ollama_base_url": cfg.ollama_base_url,
        "model_name": cfg.model_name,
        "debounce_seconds": cfg.debounce_seconds,
        "max_timeline_events": cfg.max_timeline_events,
    }


_DEFAULTS = {
    "is_enabled": False,
    "ollama_base_url": "http://ollama:11434",
    "model_name": "llama3.2",
    "debounce_seconds": 60,
    "max_timeline_events": 20,
}


@router.get("")
async def get_ai_config(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    config = await ai_config_service.get_ai_config(db, str(current_user.org_id))
    data = _config_to_dict(config) if config else _DEFAULTS
    return {"data": data, "error": None}


@router.put("")
async def save_ai_config(
    payload: AiConfigPayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    from fastapi import HTTPException as _HTTPException
    from app.services.ai_service import validate_ollama_url
    if payload.ollama_base_url is not None:
        try:
            validate_ollama_url(payload.ollama_base_url)
        except ValueError as exc:
            raise _HTTPException(status_code=422, detail=str(exc))
    data = payload.model_dump(exclude_none=True)
    config = await ai_config_service.upsert_ai_config(db, str(current_user.org_id), data)
    return {"data": _config_to_dict(config), "error": None}


@router.post("/test")
async def test_ai_connection(
    payload: AiTestPayload,
    current_user=Depends(require_permission("users.manage")),
):
    """Test connectivity to Ollama and verify the configured model is available."""
    from fastapi import HTTPException as _HTTPException
    from app.services.ai_service import validate_ollama_url
    try:
        validate_ollama_url(payload.ollama_base_url)
    except ValueError as exc:
        raise _HTTPException(status_code=422, detail=str(exc))
    result = await ai_config_service.test_ollama_connection(
        payload.ollama_base_url, payload.model_name
    )
    return {"data": result, "error": None}
