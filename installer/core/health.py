import asyncio
import httpx


async def wait_for_health(base_url: str, timeout: int = 120, interval: int = 3) -> bool:
    """Poll GET <base_url>/api/health until 200 or timeout. Returns True on success."""
    deadline = asyncio.get_event_loop().time() + timeout
    async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                resp = await client.get(f"{base_url}/api/health")
                if resp.status_code == 200:
                    return True
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            if interval > 0:
                await asyncio.sleep(interval)
    return False
