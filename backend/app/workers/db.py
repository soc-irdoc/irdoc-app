"""Separate SQLAlchemy engine for Celery workers.

Workers use this instead of the shared FastAPI engine to avoid pool contention
when engine.dispose() is called on task completion.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

_worker_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=2,
    max_overflow=3,
    pool_pre_ping=True,
)

WorkerSessionLocal = async_sessionmaker(
    bind=_worker_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def dispose_worker_engine() -> None:
    await _worker_engine.dispose()
