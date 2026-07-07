# Settings About — Version Display & Update Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the running IRDoc version in Settings → About, linked to the GitHub releases page, with a "new version available" indicator when a newer release exists.

**Architecture:** Backend exposes `settings.VERSION` (sourced from the `VERSION` env var, already written to `docker/.env` by the installer) and an authenticated `/api/v1/version` endpoint that also reports the latest GitHub release, using an in-memory 1-hour cache around the same unauthenticated GitHub Releases API call the installer already makes. Frontend fetches this via a `useVersion` hook and renders it in the existing About card.

**Tech Stack:** FastAPI, httpx, pytest + pytest-asyncio (backend); React, @tanstack/react-query, axios (frontend).

## Global Constraints

- Repo is `soc-irdoc/irdoc-app` (currently private) — the GitHub Releases API call will 404 until it's public or has a release; this must fail silently (return `None`), never raise or block the endpoint.
- Version comparison is exact string equality (`latest != current`), no semver ordering — matches `installer/wizard.py`'s existing logic.
- `settings.VERSION` defaults to `"dev"` when no `VERSION` env var is set (local/non-Docker runs).
- No new frontend test infrastructure — this project has no frontend test framework configured (no `test` script, no `*.test.tsx` files anywhere). Verify frontend changes via `npm run type-check`, `npm run lint`, `npm run build`, and manual browser check, consistent with existing project practice.
- Backend changes get pytest coverage, following existing patterns in `backend/tests/`.

---

### Task 1: Backend — `settings.VERSION` + fix hardcoded app version

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/main.py:42`
- Test: `backend/tests/unit/test_config.py` (new)

**Interfaces:**
- Produces: `settings.VERSION: str` (module-level singleton `app.core.config.settings`), consumed by Task 3's endpoint and by `app.main.application.version`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_config.py`:

```python
"""Unit tests for app.core.config.Settings."""
from app.core.config import Settings
from app.main import application, settings


def test_version_defaults_to_dev(monkeypatch):
    monkeypatch.delenv("VERSION", raising=False)
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    s = Settings(_env_file=None)
    assert s.VERSION == "dev"


def test_version_reads_env_override(monkeypatch):
    monkeypatch.setenv("VERSION", "0.1.0-alpha")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    s = Settings(_env_file=None)
    assert s.VERSION == "0.1.0-alpha"


def test_app_version_matches_settings():
    assert application.version == settings.VERSION
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_config.py -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'VERSION'` (first two tests), third test fails too since `application.version` is still `"1.0.0"`.

- [ ] **Step 3: Add the `VERSION` field to `Settings`**

In `backend/app/core/config.py`, add to the `# App` section (after `ALLOW_REGISTRATION: bool = True`):

```python
    # App
    APP_NAME: str = "IRDoc"
    BASE_URL: AnyHttpUrl = "http://localhost:3000"  # type: ignore[assignment]
    ALLOW_REGISTRATION: bool = True
    VERSION: str = "dev"
```

- [ ] **Step 4: Fix the hardcoded app version**

In `backend/app/main.py`, change line 42:

```python
    version="1.0.0",
```

to:

```python
    version=settings.VERSION,
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_config.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/config.py backend/app/main.py backend/tests/unit/test_config.py
git commit -m "fix(backend): source app version from settings instead of hardcoding 1.0.0"
```

---

### Task 2: Backend — cached GitHub release check

**Files:**
- Create: `backend/app/services/version_check.py`
- Test: `backend/tests/unit/test_version_check.py` (new)

**Interfaces:**
- Produces: `async def get_latest_release_version() -> str | None` in `app.services.version_check`, consumed by Task 3's endpoint.
- Produces: module-level `_cache: dict` (keys `"value"`, `"checked_at"`) for test cache-reset purposes.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_version_check.py`:

```python
"""Unit tests for the cached GitHub release version check."""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services import version_check


def _mock_response(data: dict) -> MagicMock:
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = data
    return r


def _make_client(get_return=None, get_side_effect=None) -> AsyncMock:
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    if get_side_effect is not None:
        client.get = AsyncMock(side_effect=get_side_effect)
    else:
        client.get = AsyncMock(return_value=get_return)
    return client


@pytest.fixture(autouse=True)
def reset_cache():
    version_check._cache["value"] = None
    version_check._cache["checked_at"] = 0.0
    yield
    version_check._cache["value"] = None
    version_check._cache["checked_at"] = 0.0


@pytest.mark.asyncio
async def test_returns_latest_version_on_success():
    client = _make_client(get_return=_mock_response({"tag_name": "v0.2.0"}))

    with patch("app.services.version_check.httpx.AsyncClient", return_value=client):
        latest = await version_check.get_latest_release_version()

    assert latest == "0.2.0"


@pytest.mark.asyncio
async def test_returns_none_when_request_fails():
    client = _make_client(get_side_effect=httpx.ConnectError("boom"))

    with patch("app.services.version_check.httpx.AsyncClient", return_value=client):
        latest = await version_check.get_latest_release_version()

    assert latest is None


@pytest.mark.asyncio
async def test_returns_none_on_404():
    resp = MagicMock()
    resp.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock()))
    client = _make_client(get_return=resp)

    with patch("app.services.version_check.httpx.AsyncClient", return_value=client):
        latest = await version_check.get_latest_release_version()

    assert latest is None


@pytest.mark.asyncio
async def test_caches_result_within_ttl():
    client = _make_client(get_return=_mock_response({"tag_name": "v0.2.0"}))

    with patch("app.services.version_check.httpx.AsyncClient", return_value=client) as mock_ctor:
        first = await version_check.get_latest_release_version()
        second = await version_check.get_latest_release_version()

    assert first == second == "0.2.0"
    mock_ctor.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/unit/test_version_check.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.version_check'`

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/version_check.py`:

```python
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

_cache: dict = {"value": None, "checked_at": 0.0}


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/test_version_check.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/version_check.py backend/tests/unit/test_version_check.py
git commit -m "feat(backend): add cached GitHub release version check service"
```

---

### Task 3: Backend — `GET /api/v1/version` endpoint

**Files:**
- Create: `backend/app/api/v1/version.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/integration/test_version_endpoint.py` (new)

**Interfaces:**
- Consumes: `settings.VERSION` (Task 1), `get_latest_release_version()` (Task 2), `get_current_user` (`app.core.security`).
- Produces: `GET /api/v1/version` → `{"data": {"version": str, "latest_version": str | None, "update_available": bool}, "error": null}`, consumed by Task 6's frontend hook.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/integration/test_version_endpoint.py`:

```python
"""Integration tests for GET /api/v1/version."""
from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_version_returns_current_version(client: AsyncClient, auth_headers):
    with patch("app.api.v1.version.get_latest_release_version", return_value=None):
        resp = await client.get("/api/v1/version", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["version"] == "dev"
    assert data["latest_version"] is None
    assert data["update_available"] is False


@pytest.mark.asyncio
async def test_get_version_flags_update_available(client: AsyncClient, auth_headers):
    with patch("app.api.v1.version.get_latest_release_version", return_value="99.0.0"):
        resp = await client.get("/api/v1/version", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["latest_version"] == "99.0.0"
    assert data["update_available"] is True


@pytest.mark.asyncio
async def test_get_version_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/version")
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/integration/test_version_endpoint.py -v`
Expected: FAIL — `404 Not Found` (route doesn't exist yet)

- [ ] **Step 3: Write the router**

Create `backend/app/api/v1/version.py`:

```python
from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.security import get_current_user
from app.services.version_check import get_latest_release_version

router = APIRouter(tags=["version"])


@router.get("/version")
async def get_version(current_user=Depends(get_current_user)):
    """Return the running IRDoc version and whether a newer release exists."""
    latest = await get_latest_release_version()
    return {
        "data": {
            "version": settings.VERSION,
            "latest_version": latest,
            "update_available": latest is not None and latest != settings.VERSION,
        },
        "error": None,
    }
```

- [ ] **Step 4: Register the router**

In `backend/app/main.py`, add `version` to the router import tuple (after `ai_config,` on line 182):

```python
    smtp,
    ai_config,
    version,
)
```

Add the include call after line 223 (`application.include_router(ai_config.router, prefix=API_PREFIX)`):

```python
application.include_router(ai_config.router, prefix=API_PREFIX)
application.include_router(version.router, prefix=API_PREFIX)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && pytest tests/integration/test_version_endpoint.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Run the full backend test suite to check for regressions**

Run: `cd backend && pytest -v`
Expected: All tests pass (no new failures beyond pre-existing skips).

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/version.py backend/app/main.py backend/tests/integration/test_version_endpoint.py
git commit -m "feat(backend): add GET /api/v1/version endpoint"
```

---

### Task 4: Docker — pass `VERSION` into the running backend container

**Files:**
- Modify: `docker/docker-compose.prod.yml`

**Interfaces:**
- Consumes: `VERSION` value in `docker/.env` (already written by `installer/wizard.py`'s `assemble_env`).
- Produces: `VERSION` env var visible inside the `backend`, `worker`, and `beat` containers (all three use the `x-backend-env` anchor), read by `settings.VERSION` (Task 1).

- [ ] **Step 1: Add `VERSION` to the backend env anchor**

In `docker/docker-compose.prod.yml`, add to `x-backend-env` (after `MSSP_MODE: ${MSSP_MODE:-false}`):

```yaml
x-backend-env: &backend-env
  DATABASE_URL: ${DATABASE_URL}
  REDIS_URL: ${REDIS_URL}
  SECRET_KEY: ${SECRET_KEY}
  STORAGE_BACKEND: ${STORAGE_BACKEND:-local}
  STORAGE_PATH: /app/storage
  BASE_URL: ${BASE_URL}
  LICENSE_KEY: ${LICENSE_KEY:-}
  AI_BACKEND: ${AI_BACKEND:-}
  AI_MODEL: ${AI_MODEL:-claude-sonnet-4-6}
  ALLOW_REGISTRATION: ${ALLOW_REGISTRATION:-false}
  WEBHOOK_RATE_LIMIT: ${WEBHOOK_RATE_LIMIT:-20}
  WEBHOOK_MAX_PAYLOAD_BYTES: ${WEBHOOK_MAX_PAYLOAD_BYTES:-65536}
  ACCESS_TOKEN_EXPIRE_MINUTES: ${ACCESS_TOKEN_EXPIRE_MINUTES:-15}
  REFRESH_TOKEN_EXPIRE_DAYS: ${REFRESH_TOKEN_EXPIRE_DAYS:-30}
  MSSP_MODE: ${MSSP_MODE:-false}
  VERSION: ${VERSION:-latest}
```

- [ ] **Step 2: Verify the interpolation resolves**

Run: `cd docker && VERSION=0.1.0-alpha DB_PASSWORD=x REDIS_PASSWORD=x SECRET_KEY=x BASE_URL=http://localhost DATABASE_URL=postgresql://x REDIS_URL=redis://x docker compose -f docker-compose.prod.yml config --services`
Expected: prints the service list (`db`, `redis`, `backend`, `ollama`, `worker`, `beat`, `frontend`) with no YAML errors, confirming the anchor still parses. If Docker isn't installed locally, skip this step and instead visually confirm the YAML indentation matches the surrounding keys (2 spaces, same level as `MSSP_MODE`).

- [ ] **Step 3: Commit**

```bash
git add docker/docker-compose.prod.yml
git commit -m "fix(docker): pass VERSION through to the backend container env"
```

---

### Task 5: Frontend — API client + `useVersion` hook

**Files:**
- Modify: `frontend/src/lib/apiClient.ts`
- Create: `frontend/src/hooks/useVersion.ts`

**Interfaces:**
- Consumes: `GET /api/v1/version` (Task 3).
- Produces: `useVersion(): { version: string | undefined; latestVersion: string | null; updateAvailable: boolean }`, consumed by Task 6.

- [ ] **Step 1: Add `versionApi` to the API client**

In `frontend/src/lib/apiClient.ts`, insert after the `mfaApi` object closes (after line 184 `}`, before `export default apiClient`):

```typescript
export const versionApi = {
  get: () =>
    apiClient.get<{
      data: { version: string; latest_version: string | null; update_available: boolean }
    }>('/version'),
}

export default apiClient
```

(This replaces the existing `export default apiClient` line — don't duplicate it.)

- [ ] **Step 2: Create the hook**

Create `frontend/src/hooks/useVersion.ts`:

```typescript
import { useQuery } from '@tanstack/react-query'
import apiClient from '@/lib/apiClient'
import { useAuthStore } from '@/stores/authStore'

interface VersionInfo {
  version: string
  latest_version: string | null
  update_available: boolean
}

export function useVersion() {
  const user = useAuthStore((s) => s.user)

  const query = useQuery({
    queryKey: ['version'],
    queryFn: async () => {
      const res = await apiClient.get<{ data: VersionInfo }>('/version')
      return res.data.data
    },
    enabled: !!user,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  return {
    version: query.data?.version,
    latestVersion: query.data?.latest_version ?? null,
    updateAvailable: query.data?.update_available ?? false,
  }
}
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && npm run type-check`
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/apiClient.ts frontend/src/hooks/useVersion.ts
git commit -m "feat(frontend): add versionApi client and useVersion hook"
```

---

### Task 6: Frontend — render version in Settings → About

**Files:**
- Modify: `frontend/src/components/settings/SettingsPage.tsx`

**Interfaces:**
- Consumes: `useVersion()` (Task 5).

- [ ] **Step 1: Import the hook**

In `frontend/src/components/settings/SettingsPage.tsx`, add to the imports (after line 11, `import { MFASetupWizard } from '@/components/auth/MFASetupWizard'`):

```typescript
import { useVersion } from '@/hooks/useVersion'
```

- [ ] **Step 2: Call the hook in the component**

After line 86 (`const changePassword = useChangePassword()`), add:

```typescript
  const { version, latestVersion, updateAvailable } = useVersion()
```

- [ ] **Step 3: Render the version in the About section**

Replace the About section (lines 293-305):

```tsx
      {/* About */}
      <SettingsSection icon="information_color.svg" title="About IRDoc">
        <div style={{ padding: '16px 20px', fontSize: 13, color: 'var(--text-muted)' }}>
          <p>
            <strong style={{ color: 'var(--text-primary)' }}>IRDoc</strong> — Open-Core Incident
            Response Documentation Platform
          </p>
          <p style={{ marginTop: 8 }}>
            Licensed under{' '}
            <span style={{ color: 'var(--accent)' }}>AGPL-3.0</span>.
          </p>
        </div>
      </SettingsSection>
```

with:

```tsx
      {/* About */}
      <SettingsSection icon="information_color.svg" title="About IRDoc">
        <div style={{ padding: '16px 20px', fontSize: 13, color: 'var(--text-muted)' }}>
          <p>
            <strong style={{ color: 'var(--text-primary)' }}>IRDoc</strong> — Open-Core Incident
            Response Documentation Platform
          </p>
          <p style={{ marginTop: 8 }}>
            Licensed under{' '}
            <span style={{ color: 'var(--accent)' }}>AGPL-3.0</span>.
          </p>
          {version && (
            <p style={{ marginTop: 8 }}>
              <a
                href="https://github.com/soc-irdoc/irdoc-app/releases"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'var(--accent)', textDecoration: 'none' }}
              >
                v{version}
              </a>
              {updateAvailable && (
                <a
                  href="https://github.com/soc-irdoc/irdoc-app/releases"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ display: 'block', marginTop: 4, color: 'var(--yellow)', textDecoration: 'none' }}
                >
                  New version available: v{latestVersion}
                </a>
              )}
            </p>
          )}
        </div>
      </SettingsSection>
```

- [ ] **Step 4: Type-check, lint, build**

Run: `cd frontend && npm run type-check && npm run lint && npm run build`
Expected: All three succeed with no errors.

- [ ] **Step 5: Manual verification in browser**

Run: `cd backend && VERSION=0.1.0-alpha uvicorn app.main:app --reload` (or run via the dev docker-compose stack) and `cd frontend && npm run dev`. Log in, go to Settings, scroll to "About IRDoc", and confirm:
- `v0.1.0-alpha` renders as a clickable link opening `https://github.com/soc-irdoc/irdoc-app/releases` in a new tab.
- No "new version available" line appears (since the real repo is private and the check returns `None` — this is expected today).
- No console errors in the browser devtools.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/settings/SettingsPage.tsx
git commit -m "feat(frontend): show current version and update indicator in Settings About"
```

---

## Post-Plan Note

The "new version available" line will not appear in practice until `soc-irdoc/irdoc-app` either becomes public or the GitHub API call is otherwise authenticated — this is a known, accepted limitation carried over from the installer's existing (also currently non-functional) update check, not a bug in this implementation.
