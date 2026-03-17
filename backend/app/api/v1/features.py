from fastapi import APIRouter, Depends

from app.core.feature_flags import get_all_flags
from app.core.security import get_current_user

router = APIRouter(tags=["features"])


@router.get("/features")
async def get_features(current_user=Depends(get_current_user)):
    """Return the feature flag map for the current org/license."""
    return {"data": get_all_flags(), "error": None}
