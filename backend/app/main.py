"""
IRDoc FastAPI application entry point.
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.limiter import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify DB connectivity
    from app.core.database import engine
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: None)  # ping

    # Start Redis → Socket.io bridge
    from app.sio import start_redis_subscriber
    _ws_task = asyncio.create_task(start_redis_subscriber())

    yield

    # Shutdown
    _ws_task.cancel()
    try:
        await _ws_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()


application = FastAPI(
    title="IRDoc API",
    description="Incident Response Documentation Platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Rate limiting
application.state.limiter = limiter
application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
application.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Security Headers Middleware ────────────────────────────────────────────────
@application.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ─── Global exception handler (never leak internals) ───────────────────────────
@application.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging
    logging.getLogger("irp").exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"data": None, "error": "Internal server error"},
    )


# ─── Health ─────────────────────────────────────────────────────────────────────
@application.get("/api/health", tags=["health"])
async def health():
    from app.core.database import engine
    from app.core.debounce import get_redis
    from app.services.storage.resolver import get_storage_backend

    db_ok = False
    redis_ok = False
    storage_ok = False

    try:
        async with engine.begin() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    try:
        redis = get_redis()
        await redis.ping()
        redis_ok = True
    except Exception:
        pass

    try:
        backend = get_storage_backend()
        storage_ok = await backend.test_connection()
    except Exception:
        pass

    all_ok = db_ok and redis_ok and storage_ok
    return JSONResponse(
        status_code=status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "ok" if all_ok else "degraded",
            "db": db_ok,
            "redis": redis_ok,
            "storage": storage_ok,
        },
    )


# ─── Routers ────────────────────────────────────────────────────────────────────
from app.api.v1 import (  # noqa: E402
    auth,
    api_keys,
    incidents,
    timeline,
    attachments,
    iocs,
    tasks,
    templates,
    external,
    features,
    reports,
    report_templates,
    sync_policies,
    ai,
    integrations,
    graph,
    assets,
    users,
    audit,
    admin,
    saml,
    pdf_templates,
    mfa,
    dashboard,
    backup,
    smtp,
    ai_config,
)
# Load all integration plugins on startup
import app.plugins  # noqa: F401, E402

API_PREFIX = "/api/v1"

application.include_router(auth.router, prefix=API_PREFIX)
application.include_router(api_keys.router, prefix=API_PREFIX)
application.include_router(incidents.router, prefix=API_PREFIX)
application.include_router(timeline.router, prefix=API_PREFIX)
application.include_router(attachments.router, prefix=API_PREFIX)
application.include_router(iocs.router, prefix=API_PREFIX)
application.include_router(tasks.router, prefix=API_PREFIX)
application.include_router(templates.router, prefix=API_PREFIX)
application.include_router(external.router, prefix=API_PREFIX)
application.include_router(features.router, prefix=API_PREFIX)
# Phase 3
application.include_router(reports.router, prefix=API_PREFIX)
application.include_router(report_templates.router, prefix=API_PREFIX)
application.include_router(sync_policies.router, prefix=API_PREFIX)
application.include_router(ai.router, prefix=API_PREFIX)
# Phase 4
application.include_router(integrations.router, prefix=API_PREFIX)
application.include_router(graph.router, prefix=API_PREFIX)
application.include_router(assets.router, prefix=API_PREFIX)
# Phase 5
application.include_router(users.router, prefix=API_PREFIX)
application.include_router(audit.router, prefix=API_PREFIX)
application.include_router(admin.router, prefix=API_PREFIX)
application.include_router(saml.router, prefix=API_PREFIX)
# Post-launch additions
application.include_router(pdf_templates.router, prefix=API_PREFIX)
# MFA
application.include_router(mfa.router, prefix=API_PREFIX)
# Dashboard
application.include_router(dashboard.router, prefix=API_PREFIX)
# Backup
application.include_router(backup.router, prefix=API_PREFIX)
application.include_router(smtp.router, prefix=API_PREFIX)
application.include_router(ai_config.router, prefix=API_PREFIX)

# ── Combined ASGI app (Socket.io + FastAPI) ─────────────────────────────────
import socketio as _sio_lib  # noqa: E402
from app.sio import sio  # noqa: E402

app = _sio_lib.ASGIApp(sio, other_asgi_app=application)
