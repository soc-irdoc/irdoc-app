"""Checks GitHub Releases for a newer IRDoc version, with an in-memory cache.

Mirrors the same unauthenticated call installer/wizard.py already makes on
startup, so both surfaces behave identically: if the repo is private,
offline, or has no releases yet, this silently returns None rather than
raising.
"""
import time

import httpx

GITHUB_RELEASES_URL = "https://api.github.com/repos/soc-irdoc/irdoc-app/releases/latest"
_CACHE_TTL_SECONDS = 3600

_cache: dict = {"value": None, "checked_at": float('-inf')}


async def get_latest_release_version() -> str | None:
    now = time.monotonic()
    if now - _cache["checked_at"] < _CACHE_TTL_SECONDS:
        return _cache["value"]

    latest: str | None = None
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(
                GITHUB_RELEASES_URL,
                headers={"Accept": "application/vnd.github+json"},
            )
            resp.raise_for_status()
            tag = resp.json().get("tag_name", "")
            latest = tag.lstrip("v") or None
    except Exception:
        latest = None

    _cache["value"] = latest
    _cache["checked_at"] = now
    return latest
