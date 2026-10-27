"""Session timeouts and revocation (#123).

Before 0.1.8 every refresh issued a new 30-day cookie, so a session that kept
refreshing never ended. Now the refresh cookie lasts the idle timeout, every
refresh keeps the original sign-in time, and sessions end after the absolute
lifetime or when the user's token_version changes.
"""
import re
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from jose import jwt

from app.core.config import settings
from app.core.security import ALGORITHM, create_refresh_token

LOGIN = {"email": "admin@test.com", "password": "TestPass123!"}


def _max_age(response) -> int:
    cookie = next(c for c in response.headers.get_list("set-cookie") if c.startswith("refresh_token="))
    return int(re.search(r"Max-Age=(\d+)", cookie).group(1))


def _claims(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


async def _login(client: AsyncClient):
    response = await client.post("/api/v1/auth/login", json=LOGIN)
    assert response.status_code == 200
    return response


async def _refresh_with(client: AsyncClient, token: str):
    client.cookies.clear()
    client.cookies.set("refresh_token", token)
    return await client.post("/api/v1/auth/refresh")


def _token(user, *, auth_time: datetime, expires_in=timedelta(minutes=30), tv=0, **extra) -> str:
    return create_refresh_token(
        str(user.id),
        str(user.org_id),
        expires_at=datetime.now(UTC) + expires_in,
        auth_time=auth_time,
        token_version=tv,
        **extra,
    )


@pytest.mark.asyncio
async def test_login_cookie_lasts_the_idle_timeout(client: AsyncClient, admin_user):
    response = await _login(client)

    assert _max_age(response) == settings.SESSION_IDLE_TIMEOUT_MINUTES * 60
    session = response.json()["meta"]["session"]
    assert session["idle_minutes"] == settings.SESSION_IDLE_TIMEOUT_MINUTES
    claims = _claims(response.cookies["refresh_token"])
    assert claims["exp"] - claims["auth_time"] == settings.SESSION_IDLE_TIMEOUT_MINUTES * 60


@pytest.mark.asyncio
async def test_refresh_keeps_the_original_sign_in_time(client: AsyncClient, admin_user):
    user, _ = admin_user
    signed_in = datetime.now(UTC) - timedelta(hours=2)

    response = await _refresh_with(client, _token(user, auth_time=signed_in))

    assert response.status_code == 200
    assert _claims(response.cookies["refresh_token"])["auth_time"] == int(signed_in.timestamp())
    expires_at = datetime.fromisoformat(response.json()["meta"]["session"]["expires_at"])
    assert expires_at == datetime.fromtimestamp(int(signed_in.timestamp()), UTC) + timedelta(
        hours=settings.SESSION_MAX_HOURS
    )


@pytest.mark.asyncio
async def test_refresh_fails_after_the_absolute_lifetime(client: AsyncClient, admin_user):
    user, _ = admin_user
    signed_in = datetime.now(UTC) - timedelta(hours=settings.SESSION_MAX_HOURS, minutes=1)

    response = await _refresh_with(client, _token(user, auth_time=signed_in))

    assert response.status_code == 401
    assert response.json()["detail"] == "Session expired"


@pytest.mark.asyncio
async def test_cookie_never_outlives_the_absolute_lifetime(client: AsyncClient, admin_user):
    user, _ = admin_user
    # 10 minutes left of the session: less than the idle timeout.
    signed_in = datetime.now(UTC) - timedelta(hours=settings.SESSION_MAX_HOURS) + timedelta(minutes=10)

    response = await _refresh_with(client, _token(user, auth_time=signed_in))

    assert response.status_code == 200
    assert _max_age(response) <= 10 * 60


@pytest.mark.asyncio
async def test_token_from_before_0_1_8_is_rejected(client: AsyncClient, admin_user):
    user, _ = admin_user
    legacy = jwt.encode(
        {
            "sub": str(user.id),
            "org": str(user.org_id),
            "exp": datetime.now(UTC) + timedelta(days=30),
            "type": "refresh",
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )

    response = await _refresh_with(client, legacy)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_expired_idle_cookie_is_rejected(client: AsyncClient, admin_user):
    user, _ = admin_user
    token = _token(user, auth_time=datetime.now(UTC) - timedelta(hours=1), expires_in=timedelta(seconds=-1))

    response = await _refresh_with(client, token)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sign_out_everywhere_ends_other_sessions(client: AsyncClient, admin_user):
    login = await _login(client)
    other_session = login.cookies["refresh_token"]
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    response = await client.post("/api/v1/auth/logout-all", headers=headers)
    assert response.status_code == 200

    response = await _refresh_with(client, other_session)
    assert response.status_code == 401
    assert response.json()["detail"] == "Session revoked"


@pytest.mark.asyncio
async def test_password_change_ends_other_sessions_but_not_this_one(client: AsyncClient, admin_user):
    login = await _login(client)
    other_session = login.cookies["refresh_token"]
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "TestPass123!", "new_password": "NewPass456!"},
        headers=headers,
    )
    assert response.status_code == 200
    this_session = response.cookies["refresh_token"]

    assert (await _refresh_with(client, other_session)).status_code == 401
    assert (await _refresh_with(client, this_session)).status_code == 200


@pytest.mark.asyncio
async def test_org_session_timeouts_override_the_defaults(client: AsyncClient, auth_headers):
    response = await client.put(
        "/api/v1/admin/org",
        json={"session_idle_minutes": 15, "session_max_hours": 2},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["settings"]["session_idle_minutes"] == 15

    login = await _login(client)
    assert _max_age(login) == 15 * 60
    assert login.json()["meta"]["session"]["idle_minutes"] == 15
    claims = _claims(login.cookies["refresh_token"])

    # 0 goes back to the server default.
    response = await client.put(
        "/api/v1/admin/org",
        json={"session_idle_minutes": 0, "session_max_hours": 0},
        headers=auth_headers,
    )
    assert "session_idle_minutes" not in response.json()["data"]["settings"]
    assert claims["exp"] - claims["auth_time"] == 15 * 60


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"session_idle_minutes": 3},
    {"session_idle_minutes": 1441},
    {"session_max_hours": 721},
    {"session_max_hours": -1},
])
async def test_org_session_timeouts_are_bounded(client: AsyncClient, auth_headers, payload):
    response = await client.put("/api/v1/admin/org", json=payload, headers=auth_headers)
    assert response.status_code == 422
