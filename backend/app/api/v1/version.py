from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.security import get_current_user
from app.services.version_check import get_latest_release_version

router = APIRouter(tags=["version"])


@router.get("/version")
async def get_version(current_user=Depends(get_current_user)):
    """Return the running IRDoc version and whether a newer release exists."""
    latest = await get_latest_release_version()
    return {
        "data": {
            "version": settings.VERSION,
            "latest_version": latest,
            "update_available": latest is not None and latest != settings.VERSION,
        },
        "error": None,
    }
