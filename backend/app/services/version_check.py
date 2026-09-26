"""Checks GitHub Releases for a newer IRDoc version, with an in-memory cache.

Mirrors the same unauthenticated call installer/wizard.py already makes on
startup, so both surfaces behave identically: if the repo is private,
offline, or has no releases yet, this silently returns None rather than
raising.
"""
import time

import httpx
from packaging.version import InvalidVersion, Version

# /releases/latest skips pre-releases, and every IRDoc release so far is one,
# so list releases and pick the highest version ourselves.
GITHUB_RELEASES_URL = "https://api.github.com/repos/soc-irdoc/irdoc-app/releases"
_CACHE_TTL_SECONDS = 3600

_cache: dict = {"value": None, "checked_at": float('-inf')}


def _parse(version: str | None) -> Version | None:
    if not version:
        return None
    try:
        return Version(version.lstrip("v"))
    except InvalidVersion:
        return None


def pick_latest(releases: list[dict]) -> str | None:
    """Return the highest non-draft release version (pre-releases included), without the 'v'."""
    best: tuple[Version, str] | None = None
    for release in releases:
        if release.get("draft"):
            continue
        tag = (release.get("tag_name") or "").lstrip("v")
        parsed = _parse(tag)
        if parsed is not None and (best is None or parsed > best[0]):
            best = (parsed, tag)
    return best[1] if best else None


def is_newer(latest: str | None, current: str | None) -> bool:
    """True only when both versions parse and latest > current (a 'dev' build never nags)."""
    latest_v, current_v = _parse(latest), _parse(current)
    return latest_v is not None and current_v is not None and latest_v > current_v


async def get_latest_release_version() -> str | None:
    now = time.monotonic()
    if now - _cache["checked_at"] < _CACHE_TTL_SECONDS:
        return _cache["value"]

    latest: str | None = None
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(
                GITHUB_RELEASES_URL,
                params={"per_page": 20},
                headers={"Accept": "application/vnd.github+json"},
            )
            resp.raise_for_status()
            latest = pick_latest(resp.json())
    except Exception:
        latest = None

    _cache["value"] = latest
    _cache["checked_at"] = now
    return latest
