"""Real client IP behind IRDoc's nginx (#160).

The backend is only reachable through the frontend container's nginx (compose
`expose`s port 8000, it doesn't publish it), so request.client is always the
nginx container's Docker address. Audit logs recorded 172.x addresses, and the
rate limiter, keyed on that address, counted every user as one client.

Every nginx config IRDoc has shipped (image default, installer, examples) sets
`proxy_set_header X-Real-IP $remote_addr;`. nginx overwrites the header, so a
client can't forge it, and behind a load balancer `real_ip` (set_real_ip_from)
makes $remote_addr the real client. This middleware puts that address into the
ASGI scope, so request.client is right everywhere.

X-Forwarded-For is deliberately not used: older local configs append to the
client's own X-Forwarded-For, so its leftmost entries are attacker-controlled.

Set TRUST_X_REAL_IP=false if port 8000 is ever reachable without nginx.
"""
import ipaddress


class RealIPMiddleware:
    def __init__(self, app, trust: bool = True):
        self.app = app
        self.trust = trust

    async def __call__(self, scope, receive, send):
        if self.trust and scope["type"] in ("http", "websocket"):
            for name, value in scope.get("headers", ()):
                if name == b"x-real-ip":
                    ip = _parse_ip(value)
                    if ip is not None:
                        port = scope["client"][1] if scope.get("client") else 0
                        scope = dict(scope, client=(ip, port))
                    break
        await self.app(scope, receive, send)


def _parse_ip(raw: bytes) -> str | None:
    try:
        return str(ipaddress.ip_address(raw.decode("ascii").strip()))
    except (UnicodeDecodeError, ValueError):
        return None
