# Settings About — Version Display & Update Check — Design Spec

**Date:** 2026-07-07
**Status:** Approved

## Context

The Settings page's "About IRDoc" section (`frontend/src/components/settings/SettingsPage.tsx`) currently shows only the product name and license (AGPL-3.0), with no version information.

Two related pieces of drift exist in the codebase:
- `backend/app/main.py` hardcodes `version="1.0.0"` in the FastAPI app metadata, out of sync with the root `VERSION` file (currently `0.1.0-alpha`).
- The install/upgrade wizard (`installer/wizard.py`) already contains an update check that hits `https://api.github.com/repos/soc-irdoc/irdoc-app/releases/latest` unauthenticated on startup — but the repo (`soc-irdoc/irdoc-app`) is currently private, so that call 404s and the check silently does nothing today. It's expected to start working once the repo is made public / a release is tagged.

This feature adds a version display to the About section, linked to the GitHub repo's releases page, and a "new version available" indicator using the same GitHub Releases API approach as the installer — proxied through the backend so the check happens once per cache window regardless of how many users have Settings open, and so it degrades silently exactly like the installer's check does today.

## Layout

**Location:** Settings → About IRDoc section (existing `SettingsSection` card), below the existing license line.

- Current version renders as a link: `v0.1.0-alpha`, opening `https://github.com/soc-irdoc/irdoc-app/releases` in a new tab.
- If a newer version is available, a secondary line appears below it: "New version available: v{latest_version}", also linking to the releases page.
- While the version query is loading, or if it fails, the version line simply doesn't render (no spinner, no error state) — consistent with the installer's existing silent-fail behavior for the update check.

## Data Flow

```
Settings page mount → GET /api/v1/version (auth required)
  → settings.VERSION (from env, instant)
  → get_cached_latest_release() → in-memory cache (1hr TTL)
      hit  → return cached value
      miss → GET https://api.github.com/repos/soc-irdoc/irdoc-app/releases/latest (httpx, 3s timeout)
             success → parse tag_name, cache it
             failure (private repo / offline / rate-limited / no releases) → cache `None`
  → { version, latest_version, update_available }
```

`update_available = latest_version is not None and latest_version != version` (exact string comparison, same as the installer — no semver ordering logic).

## Backend Changes

| File | Change |
|---|---|
| `backend/app/core/config.py` | Add `VERSION: str = "dev"` to `Settings` (read from `VERSION` env var). |
| `backend/app/main.py` | Change `version="1.0.0"` → `version=settings.VERSION` in the `FastAPI(...)` constructor. |
| `backend/app/services/version_check.py` (new) | `get_latest_release_version()` — in-memory 1hr-cached GitHub Releases API call, returns `str \| None`. |
| `backend/app/api/v1/version.py` (new) | `GET /api/v1/version`, requires `get_current_user` (same pattern as `features.py`). Returns `{"data": {"version": str, "latest_version": str \| None, "update_available": bool}, "error": null}`. |

Router registered in `main.py`'s router list, same as the other `api/v1` modules.

## Docker / Installer Wiring

| File | Change |
|---|---|
| `docker/docker-compose.prod.yml` | Add `VERSION: ${VERSION:-latest}` to the `x-backend-env` anchor, so the `VERSION` value already written to `docker/.env` by the installer (currently only used to select the image tag) also reaches the running backend container. |
| `docker/docker-compose.yml` (dev) | No change — backend already uses `env_file: .env`, so `VERSION` passes through automatically if present. |
| `installer/wizard.py` | No change — already writes `VERSION=` into `docker/.env`. |

## Frontend Changes

| File | Change |
|---|---|
| `frontend/src/lib/apiClient.ts` | Add `versionApi.get()` — `GET /version`. |
| `frontend/src/hooks/useVersion.ts` (new) | `useQuery(['version'], ...)`, `enabled: !!user`, mirrors `useFeatureFlags.ts`. |
| `frontend/src/components/settings/SettingsPage.tsx` | About section renders the version link (and update-available line, if any) using `useVersion()`. |

## Key Files

| | |
|---|---|
| Config | `backend/app/core/config.py` |
| App metadata | `backend/app/main.py` |
| Version check service | `backend/app/services/version_check.py` |
| API router | `backend/app/api/v1/version.py` |
| Compose (prod) | `docker/docker-compose.prod.yml` |
| Frontend API client | `frontend/src/lib/apiClient.ts` |
| Frontend hook | `frontend/src/hooks/useVersion.ts` |
| Frontend component | `frontend/src/components/settings/SettingsPage.tsx` |
