"""Socket.IO Origin check (#137): pages served from the host the request went
to are accepted even when that isn't BASE_URL; other sites are refused."""
import logging

import httpx
import pytest
import socketio

from app import sio as sio_module
from app.core.config import settings
from app.sio import origin_allowed

BASE = str(settings.BASE_URL).rstrip("/")


def env(host: str | None) -> dict:
    return {"HTTP_HOST": host} if host else {}


@pytest.fixture(autouse=True)
def _fresh_reports():
    sio_module._reported_origins.clear()
    yield


def test_base_url_is_accepted_from_any_host():
    assert origin_allowed(BASE, env("10.0.0.5:8080"))
    assert origin_allowed(BASE + "/", env(None))


def test_no_origin_is_left_to_the_auth_check():
    assert origin_allowed(None, env("irdoc.example.com"))


@pytest.mark.parametrize("origin,host", [
    # Reached through a reverse proxy under another name, HTTPS at the proxy
    ("https://irdoc.corp.example", "irdoc.corp.example"),
    ("https://irdoc.corp.example", "irdoc.corp.example:443"),
    ("http://irdoc.corp.example:8080", "IRDOC.corp.example:8080"),
    ("http://[::1]:8080", "[::1]:8080"),
])
def test_same_host_page_is_accepted(origin, host):
    assert origin_allowed(origin, env(host))


@pytest.mark.parametrize("origin,host", [
    ("https://evil.example", "irdoc.corp.example"),
    ("https://irdoc.corp.example.evil.example", "irdoc.corp.example"),
    ("https://irdoc.corp.example", None),
    ("null", "irdoc.corp.example"),
    ("https://irdoc.corp.example", "[bad"),
])
def test_other_sites_are_refused(origin, host):
    assert not origin_allowed(origin, env(host))


def test_a_refusal_is_logged_once_with_what_to_fix(caplog):
    with caplog.at_level(logging.WARNING, logger="app.sio"):
        for _ in range(3):
            origin_allowed("https://irdoc.corp.example", env("10.0.0.5:8080"))
    records = [r for r in caplog.records if r.name == "app.sio"]
    assert len(records) == 1
    assert records[0].args == ("https://irdoc.corp.example", "10.0.0.5:8080")
    msg = records[0].getMessage()
    assert "BASE_URL" in msg and "proxy_set_header Host $host" in msg


async def _poll(origin: str, host: str) -> httpx.Response:
    app = socketio.ASGIApp(sio_module.sio)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=f"http://{host}") as c:
        return await c.get("/socket.io/?EIO=4&transport=polling", headers={"Origin": origin})


@pytest.mark.asyncio
async def test_engineio_handshake_uses_the_check():
    ok = await _poll("https://irdoc.corp.example", "irdoc.corp.example")
    assert ok.status_code == 200
    assert ok.headers.get("access-control-allow-origin") == "https://irdoc.corp.example"

    refused = await _poll("https://evil.example", "irdoc.corp.example")
    assert refused.status_code == 400
    assert "not an accepted origin" in refused.text
