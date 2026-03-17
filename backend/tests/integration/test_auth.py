"""Integration tests for auth endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_setup_creates_admin(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/setup",
        json={"email": "admin@test.com", "full_name": "Admin", "password": "TestPass123!", "org_name": "Test Org"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data["data"]
    assert data["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "TestPass123!"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user(client: AsyncClient, auth_headers):
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "TestPass123!", "new_password": "NewPass456!"},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_setup_blocked_after_first_user(client: AsyncClient, admin_user):
    response = await client.post(
        "/api/v1/auth/setup",
        json={"email": "second@test.com", "full_name": "Second", "password": "TestPass123!"},
    )
    assert response.status_code == 409
