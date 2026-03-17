"""
Redis debounce lock for SharePoint sync (and any future debounced operations).

Pattern:
  - On any incident write, call trigger_debounced_sync(incident_id, policy_id).
  - This sets a Redis key with TTL = debounce_seconds.
  - If the key already exists, the TTL is reset (debounce extended).
  - Celery beat checks for expired locks every 10s and fires the sync task.

Redis must have `notify-keyspace-events Ex` enabled (set in docker-compose).
"""
import redis.asyncio as aioredis

from app.core.config import settings

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


SYNC_PENDING_KEY = "sync_pending:{incident_id}:{policy_id}"


async def trigger_debounced_sync(
    incident_id: str,
    policy_id: str,
    debounce_seconds: int = 60,
) -> None:
    """Set/reset TTL on the sync-pending key. Worker fires when key expires."""
    redis = get_redis()
    key = SYNC_PENDING_KEY.format(incident_id=incident_id, policy_id=policy_id)
    await redis.set(key, policy_id, ex=debounce_seconds)


async def cancel_debounced_sync(incident_id: str, policy_id: str) -> None:
    """Cancel a pending sync (e.g., when policy is deleted)."""
    redis = get_redis()
    key = SYNC_PENDING_KEY.format(incident_id=incident_id, policy_id=policy_id)
    await redis.delete(key)


async def get_pending_syncs() -> list[tuple[str, str]]:
    """Scan for all pending sync keys. Used by beat task."""
    redis = get_redis()
    keys = await redis.keys("sync_pending:*")
    result = []
    for key in keys:
        parts = key.split(":")
        if len(parts) == 3:
            result.append((parts[1], parts[2]))
    return result
