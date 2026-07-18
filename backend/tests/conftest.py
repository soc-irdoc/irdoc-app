"""
Test configuration and fixtures.
Uses an in-memory SQLite for unit tests and a real PostgreSQL for integration tests.
Integration tests require: TEST_DATABASE_URL env var pointing to a test DB.
"""
import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ─── SQLite dialect shims (only active when using SQLite) ─────────────────────
# PostgreSQL-specific column types (JSONB, UUID, ARRAY, INET) are not understood
# by SQLite's DDL compiler. Patch the type compiler so that:
#   JSONB  → JSON     (functionally equivalent for tests)
#   UUID   → VARCHAR(36)
#   ARRAY  → JSON     (stores list as JSON blob)
#   INET   → TEXT     (stores IP as text)
# This must happen before any model or app import so that create_all succeeds.
_TEST_DB_URL_RAW = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
if "sqlite" in _TEST_DB_URL_RAW:
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # noqa: E402

    if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):
        SQLiteTypeCompiler.visit_JSONB = SQLiteTypeCompiler.visit_JSON  # type: ignore[attr-defined]

    if not hasattr(SQLiteTypeCompiler, "visit_UUID"):
        SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: "VARCHAR(36)"  # type: ignore[attr-defined]

    if not hasattr(SQLiteTypeCompiler, "visit_ARRAY"):
        SQLiteTypeCompiler.visit_ARRAY = SQLiteTypeCompiler.visit_JSON  # type: ignore[attr-defined]

    if not hasattr(SQLiteTypeCompiler, "visit_INET"):
        SQLiteTypeCompiler.visit_INET = lambda self, type_, **kw: "TEXT"  # type: ignore[attr-defined]

    # SQLite only auto-increments INTEGER PRIMARY KEY, not BIGINT.
    # Map BigInteger → INTEGER so audit_log.id auto-increments correctly.
    if not hasattr(SQLiteTypeCompiler, "_visit_BIGINT_patched"):
        SQLiteTypeCompiler.visit_BIGINT = lambda self, type_, **kw: "INTEGER"  # type: ignore[attr-defined]
        SQLiteTypeCompiler._visit_BIGINT_patched = True  # type: ignore[attr-defined]

    # Patch the PostgreSQL UUID type's bind-parameter processor so that it stores
    # UUID values as plain strings (VARCHAR-compatible) rather than calling .hex.
    # Without this, WHERE clauses comparing UUID columns break under SQLite even
    # though the DDL compiler already maps UUID → VARCHAR(36).
    import uuid as _uuid_mod
    from sqlalchemy.dialects.postgresql import UUID as _PG_UUID  # noqa: E402

    def _sqlite_uuid_bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            if isinstance(value, _uuid_mod.UUID):
                return str(value)
            return str(value)  # already a string — pass through
        return process

    _PG_UUID.bind_processor = _sqlite_uuid_bind_processor  # type: ignore[method-assign]

    # Patch the core SQLAlchemy ARRAY type so SQLite can store/retrieve lists as
    # JSON text. SQLite cannot bind Python list values natively.
    import json as _json
    from sqlalchemy.sql.sqltypes import ARRAY as _SA_ARRAY  # noqa: E402

    _orig_array_bind_processor = _SA_ARRAY.bind_processor

    def _sqlite_array_bind_processor(self, dialect):
        _inner = _orig_array_bind_processor(self, dialect)

        def process(value):
            if value is None:
                return None
            processed = _inner(value) if _inner else value
            return _json.dumps(processed)

        return process

    def _sqlite_array_result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return None
            if isinstance(value, list):
                return value
            return _json.loads(value)
        return process

    _SA_ARRAY.bind_processor = _sqlite_array_bind_processor  # type: ignore[method-assign]
    _SA_ARRAY.result_processor = _sqlite_array_result_processor  # type: ignore[method-assign]

from app.core.database import Base, get_db
from app.core.limiter import limiter
from app.core.security import hash_password
# `app` is the Socket.io ASGIApp wrapper; `application` is the FastAPI instance.
# dependency_overrides lives on the FastAPI instance.
from app.main import app, application

# ─── In-memory SQLite engine for unit tests ────────────────────────────────────
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False, autoflush=False)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    # slowapi's Limiter keeps its counters in a module-level singleton
    # (app.core.limiter.limiter), so without a reset requests from earlier
    # tests count towards later tests' limits (e.g. the 10/minute login
    # limit gets exceeded partway through the suite).
    limiter.reset()
    yield


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    """HTTP client wired to test DB."""
    async def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    from app.models.organization import Organization
    from app.models.user import User

    org = Organization(name="Test Org", slug="test")
    db_session.add(org)
    await db_session.flush()

    user = User(
        org_id=org.id,
        email="admin@test.com",
        full_name="Test Admin",
        role="admin",
        password_hash=hash_password("TestPass123!"),
        avatar_initials="TA",
    )
    db_session.add(user)
    await db_session.flush()
    return user, org


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, admin_user):
    """Returns Bearer auth headers for the admin user."""
    user, org = admin_user

    # Perform login
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "TestPass123!"},
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
