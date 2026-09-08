"""
AI configuration service — get/upsert per-org Ollama config, test connectivity.
"""
import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_config import AiConfig

logger = logging.getLogger(__name__)


async def get_ai_config(db: AsyncSession, org_id: str) -> AiConfig | None:
    result = await db.execute(
        select(AiConfig).where(AiConfig.org_id == uuid.UUID(org_id))
    )
    return result.scalar_one_or_none()


async def upsert_ai_config(db: AsyncSession, org_id: str, data: dict) -> AiConfig:
    config = await get_ai_config(db, org_id)

    if config is None:
        config = AiConfig(org_id=uuid.UUID(org_id))
        db.add(config)

    for key, value in data.items():
        if hasattr(config, key):
            setattr(config, key, value)

    await db.commit()
    await db.refresh(config)
    return config


async def test_ollama_connection(base_url: str, model_name: str) -> dict:
    """
    Verifies Ollama is reachable and the specified model is available.
    Returns {"success": bool, "error": str | None, "available_models": list[str]}.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{base_url.rstrip('/')}/api/tags")
            response.raise_for_status()
    except httpx.ConnectError:
        return {"success": False, "error": f"Cannot reach Ollama at {base_url}. Is it running?"}
    except httpx.TimeoutException:
        return {"success": False, "error": f"Connection to {base_url} timed out."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    data = response.json()
    available = [m.get("name", "") for m in data.get("models", [])]

    # Ollama model names may include tags like "llama3.2:latest"
    model_found = any(
        m == model_name or m.startswith(f"{model_name}:")
        for m in available
    )

    if not model_found:
        pull_cmd = f"docker compose --profile ai exec ollama ollama pull {model_name}"
        return {
            "success": False,
            "error": (
                f"Model '{model_name}' not found on this Ollama instance. "
                f"Pull it with: {pull_cmd}"
            ),
            "available_models": available,
        }

    return {"success": True, "error": None, "available_models": available}
