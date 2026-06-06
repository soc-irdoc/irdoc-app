"""
Celery tasks for automated and manual backups.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run an async coroutine from a sync Celery task.

    asyncio.run() creates a fresh event loop, runs the coroutine, and waits for
    all pending callbacks before closing the loop.  The engine pool is disposed
    *inside* the coroutine (while the loop is still active) so asyncpg can
    properly close connections — calling dispose() outside the loop left stale
    connections attached to the old loop, causing the next task to fail with
    "Future attached to a different loop".
    """
    async def _with_pool_cleanup():
        try:
            return await coro
        finally:
            from app.core.database import engine
            await engine.dispose()

    return asyncio.run(_with_pool_cleanup())


def _parse_interval(schedule: str) -> timedelta:
    if schedule == "6h":
        return timedelta(hours=6)
    if schedule == "weekly":
        return timedelta(weeks=1)
    if schedule == "monthly":
        return timedelta(days=30)
    return timedelta(days=1)


@celery_app.task(bind=True)
def check_and_run_backup(self):
    """Scheduled hourly. Runs a backup if the configured interval has elapsed."""
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.services.backup_service import get_or_create_config, run_backup

        async with AsyncSessionLocal() as db:
            config = await get_or_create_config(db)

            if not config.enabled:
                logger.debug("check_and_run_backup: backups disabled, skipping")
                return

            interval = _parse_interval(config.schedule)
            now = datetime.now(timezone.utc)

            if config.last_backup_at is None or (now - config.last_backup_at) >= interval:
                logger.info(
                    "check_and_run_backup: running backup (schedule=%s, last=%s)",
                    config.schedule,
                    config.last_backup_at,
                )
                record = await run_backup(db)
                logger.info(
                    "check_and_run_backup: backup complete — %s (%d bytes)",
                    record.filename,
                    record.size_bytes,
                )
            else:
                logger.debug(
                    "check_and_run_backup: next backup not due yet (last=%s, interval=%s)",
                    config.last_backup_at,
                    interval,
                )

    try:
        run_async(_run())
    except Exception:
        logger.exception("check_and_run_backup: unexpected error")


@celery_app.task(bind=True)
def trigger_manual_backup(self):
    """Called by the API's POST /run endpoint. Runs a backup immediately."""
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.services.backup_service import run_backup

        async with AsyncSessionLocal() as db:
            record = await run_backup(db)
            return {"filename": record.filename, "size_bytes": record.size_bytes}

    return run_async(_run())
