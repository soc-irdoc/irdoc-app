"""
Socket.io server for IRDoc real-time collaboration.

Architecture:
  - Single uvicorn worker (socket.io sessions are in-memory; multiple workers
    require sticky sessions or a shared session store - not worth the complexity
    for a self-hosted IR platform sized for 5-50 concurrent analysts)
  - A background task subscribes to irp:ws:* Redis pub/sub channels published
    by Celery workers and route handlers, then emits to the appropriate rooms
  - Presence tracking: Redis hash per incident keeps {sid: user_json} entries
    so each analyst can see who else is currently viewing the same incident
"""
import asyncio
import json
import logging
from urllib.parse import urlsplit

import socketio

from app.core.config import settings

logger = logging.getLogger(__name__)

_CONFIGURED_ORIGINS = frozenset(o.rstrip("/") for o in settings.get_cors_origins())
_reported_origins: set[str] = set()


def _host_name(netloc: str | None) -> str | None:
    """Host name of a Host header or origin netloc, lower-cased, without port."""
    if not netloc:
        return None
    try:
        return urlsplit(f"//{netloc}").hostname
    except ValueError:
        return None


def origin_allowed(origin: str | None, environ: dict) -> bool:
    """Socket.IO Origin check (#137).

    Accepts BASE_URL / CORS_ORIGINS, and any page served from the host the
    request was sent to (python-engineio's own default). A page on another
    site can't set its Origin to IRDoc's host, so this keeps cross-site pages
    out while an install reached under a name other than BASE_URL (a reverse
    proxy, a DNS alias) still gets real-time updates. Before, those users saw
    400s on polling and a 403 on the WebSocket and nothing in the UI updated.
    """
    if not origin:
        return True
    origin = origin.rstrip("/")
    if origin in _CONFIGURED_ORIGINS:
        return True
    try:
        origin_host = urlsplit(origin).hostname
    except ValueError:
        origin_host = None
    request_host = _host_name(environ.get("HTTP_HOST"))
    if origin_host and origin_host == request_host:
        return True
    if origin not in _reported_origins and len(_reported_origins) < 100:
        _reported_origins.add(origin)
        logger.warning(
            "Real-time updates refused for a page at %s (request Host: %s). Set BASE_URL "
            "to the address users open IRDoc at, or add it to CORS_ORIGINS. A reverse "
            "proxy in front of IRDoc must pass the original Host header "
            "(proxy_set_header Host $host).",
            origin, environ.get("HTTP_HOST") or "none",
        )
    return False


sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=origin_allowed,
    logger=False,
    engineio_logger=False,
)


# ── Auth ──────────────────────────────────────────────────────────────────────

@sio.event
async def connect(sid: str, environ: dict, auth: dict | None):
    from app.core.security import decode_token
    token = (auth or {}).get("token")
    if not token:
        raise ConnectionRefusedError("Authentication required")
    try:
        decode_token(token, expected_type="access")
    except Exception:
        raise ConnectionRefusedError("Invalid token")
    await sio.save_session(sid, {"incident_rooms": []})


@sio.event
async def disconnect(sid: str):
    """Clean up presence entries for every incident room this client was in."""
    try:
        session = await sio.get_session(sid)
        incident_rooms = session.get("incident_rooms", [])
    except Exception:
        incident_rooms = []

    for incident_id in incident_rooms:
        await _remove_presence(sid, incident_id)


# ── Room management ───────────────────────────────────────────────────────────

@sio.on("join:incident")
async def handle_join_incident(sid: str, data: dict):
    incident_id = (data or {}).get("incident_id")
    user = (data or {}).get("user")  # {id, full_name, avatar_initials}
    if not incident_id:
        return

    await sio.enter_room(sid, f"incident:{incident_id}")

    # Track in session so disconnect can clean up
    session = await sio.get_session(sid)
    rooms = session.get("incident_rooms", [])
    if incident_id not in rooms:
        rooms.append(incident_id)
        await sio.save_session(sid, {**session, "incident_rooms": rooms})

    # Presence
    if user:
        await _set_presence(sid, incident_id, user)

    users = await _get_presence(incident_id)
    await sio.emit("presence:update", {"incident_id": incident_id, "users": users},
                   room=f"incident:{incident_id}")


@sio.on("leave:incident")
async def handle_leave_incident(sid: str, data: dict):
    incident_id = (data or {}).get("incident_id")
    if not incident_id:
        return

    await sio.leave_room(sid, f"incident:{incident_id}")

    session = await sio.get_session(sid)
    rooms = session.get("incident_rooms", [])
    if incident_id in rooms:
        rooms.remove(incident_id)
        await sio.save_session(sid, {**session, "incident_rooms": rooms})

    await _remove_presence(sid, incident_id)


# ── Presence helpers ──────────────────────────────────────────────────────────

def _presence_key(incident_id: str) -> str:
    return f"irp:presence:{incident_id}"


async def _set_presence(sid: str, incident_id: str, user: dict) -> None:
    from app.core.debounce import get_redis
    redis = get_redis()
    await redis.hset(_presence_key(incident_id), sid, json.dumps(user))
    await redis.expire(_presence_key(incident_id), 3600)


async def _remove_presence(sid: str, incident_id: str) -> None:
    from app.core.debounce import get_redis
    redis = get_redis()
    await redis.hdel(_presence_key(incident_id), sid)
    users = await _get_presence(incident_id)
    await sio.emit("presence:update", {"incident_id": incident_id, "users": users},
                   room=f"incident:{incident_id}")


async def _get_presence(incident_id: str) -> list[dict]:
    from app.core.debounce import get_redis
    redis = get_redis()
    values = await redis.hvals(_presence_key(incident_id))
    seen_ids: set[str] = set()
    users: list[dict] = []
    for v in values:
        try:
            user = json.loads(v)
            uid = user.get("id")
            if uid and uid not in seen_ids:
                seen_ids.add(uid)
                users.append(user)
        except Exception:
            pass
    return users


# ── Emission helpers ──────────────────────────────────────────────────────────

async def publish_ws(incident_id: str, event: str, data: dict) -> None:
    """Publish a WebSocket event via Redis. Use from FastAPI route handlers.
    Connection errors are swallowed - WebSocket delivery is best-effort."""
    import redis.exceptions as _redis_exc

    from app.core.debounce import get_redis
    try:
        redis = get_redis()
        payload = json.dumps({"incident_id": incident_id, "event": event, "data": data})
        await redis.publish(f"irp:ws:{incident_id}", payload)
    except (_redis_exc.ConnectionError, _redis_exc.TimeoutError):
        pass


# ── Redis pub/sub bridge ──────────────────────────────────────────────────────

async def start_redis_subscriber() -> None:
    """Bridge Redis pub/sub (from Celery workers and route handlers) → Socket.io rooms."""
    import redis.asyncio as aioredis

    from app.core.config import settings

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.psubscribe("irp:ws:*")
    logger.info("WS bridge: subscribed to irp:ws:* Redis channels")
    try:
        async for message in pubsub.listen():
            if message["type"] != "pmessage":
                continue
            try:
                payload = json.loads(message["data"])
                incident_id = payload.get("incident_id")
                event = payload.get("event")
                evt_data = payload.get("data", {})
                if incident_id and event:
                    await sio.emit(event, evt_data, room=f"incident:{incident_id}")
            except Exception:
                logger.warning("WS bridge: failed to process message", exc_info=True)
    except asyncio.CancelledError:
        await pubsub.punsubscribe("irp:ws:*")
        await r.aclose()
