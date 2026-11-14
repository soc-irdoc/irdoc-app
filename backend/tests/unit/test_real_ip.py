"""Client IP behind IRDoc's nginx: taken from X-Real-IP, which nginx always
overwrites, so audit logs and rate limits see the real client instead of the
frontend container (Refs #160)."""
import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from app.core.real_ip import RealIPMiddleware


async def whoami(request):
    return PlainTextResponse(request.client.host if request.client else "none")


def _client(trust: bool = True) -> AsyncClient:
    inner = Starlette(routes=[Route("/", whoami)])
    transport = ASGITransport(app=RealIPMiddleware(inner, trust=trust), client=("172.18.0.2", 50000))
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_uses_x_real_ip():
    async with _client() as c:
        assert (await c.get("/", headers={"X-Real-IP": "203.0.113.7"})).text == "203.0.113.7"


@pytest.mark.asyncio
async def test_ipv6_x_real_ip():
    async with _client() as c:
        assert (await c.get("/", headers={"X-Real-IP": "2001:db8::1"})).text == "2001:db8::1"


@pytest.mark.asyncio
async def test_keeps_peer_without_header():
    async with _client() as c:
        assert (await c.get("/")).text == "172.18.0.2"


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["not-an-ip", "203.0.113.7, 10.0.0.1", "", "<script>"])
async def test_ignores_malformed_header(value):
    async with _client() as c:
        assert (await c.get("/", headers={"X-Real-IP": value})).text == "172.18.0.2"


@pytest.mark.asyncio
async def test_x_forwarded_for_is_never_used():
    # Older nginx configs append the client's own X-Forwarded-For; it must not win.
    async with _client() as c:
        r = await c.get("/", headers={"X-Forwarded-For": "6.6.6.6", "X-Real-IP": "203.0.113.7"})
        assert r.text == "203.0.113.7"


@pytest.mark.asyncio
async def test_can_be_switched_off():
    async with _client(trust=False) as c:
        assert (await c.get("/", headers={"X-Real-IP": "203.0.113.7"})).text == "172.18.0.2"
