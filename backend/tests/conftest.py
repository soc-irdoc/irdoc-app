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

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app

# ─── In-memory SQLite engine for unit tests ────────────────────────────────────
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
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

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


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
