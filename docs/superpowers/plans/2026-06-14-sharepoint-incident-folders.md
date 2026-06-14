# SharePoint Incident Folder Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upload every SharePoint report into a per-incident subfolder (`{library}/{incident_ref}/{filename}`), and automatically create the document library if it doesn't exist.

**Architecture:** Microsoft Graph's path-based upload (`root:/{path}:/content`) creates intermediate folders automatically, so prepending `{incident_ref}/` to the upload path is all that's needed. Library creation uses `POST /sites/{site_id}/lists` with `template: documentLibrary`. Tasks inject `_incident_ref` into the config dict before calling `push_report` — a transient key, never stored.

**Tech Stack:** Python, httpx, Microsoft Graph API, pytest, unittest.mock

---

## File Map

| File | Change |
|---|---|
| `backend/app/plugins/integrations/sharepoint.py` | `_resolve_drive_id` creates library if missing; `push_report` uses `{incident_ref}/{filename}` path |
| `backend/app/workers/tasks.py` | Both `push_report_to_sharepoint` and `sync_to_sharepoint` inject `_incident_ref` into config copy |
| `backend/tests/unit/test_sharepoint_plugin.py` | New — unit tests for the plugin changes |
| `docs/sharepoint-sync-setup.md` | Update library-name section, add folder-structure section, fix troubleshooting entry |

---

## Task 1: `_resolve_drive_id` — create library if missing (TDD)

**Files:**
- Create: `backend/tests/unit/test_sharepoint_plugin.py`
- Modify: `backend/app/plugins/integrations/sharepoint.py`

### Step 1: Write failing tests

Create `backend/tests/unit/test_sharepoint_plugin.py`:

```python
"""Unit tests for SharePointPlugin."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.plugins.integrations.sharepoint import SharePointPlugin


def _mock_json_response(data: dict) -> MagicMock:
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = data
    return r


def _make_client(get_side_effects: list, post_return=None, put_return=None) -> AsyncMock:
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get = AsyncMock(side_effect=get_side_effects)
    if post_return is not None:
        client.post = AsyncMock(return_value=post_return)
    if put_return is not None:
        client.put = AsyncMock(return_value=put_return)
    return client


@pytest.mark.asyncio
async def test_resolve_drive_id_returns_existing():
    """Returns drive ID when library is already present — no POST called."""
    plugin = SharePointPlugin()
    drives_resp = _mock_json_response({"value": [{"id": "drv-1", "name": "IR Reports"}]})
    client = _make_client(get_side_effects=[drives_resp])

    with patch("app.plugins.integrations.sharepoint.httpx.AsyncClient", return_value=client):
        drive_id = await plugin._resolve_drive_id("site-1", "IR Reports", "tok")

    assert drive_id == "drv-1"
    client.post.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_drive_id_creates_library_when_missing():
    """Creates the document library via Graph when it is not found, then returns the new drive ID."""
    plugin = SharePointPlugin()
    empty_drives = _mock_json_response({"value": []})
    create_resp = _mock_json_response({})
    new_drives = _mock_json_response({"value": [{"id": "drv-new", "name": "IR Reports"}]})
    client = _make_client(
        get_side_effects=[empty_drives, new_drives],
        post_return=create_resp,
    )

    with patch("app.plugins.integrations.sharepoint.httpx.AsyncClient", return_value=client):
        drive_id = await plugin._resolve_drive_id("site-1", "IR Reports", "tok")

    assert drive_id == "drv-new"
    client.post.assert_called_once()
    call_kwargs = client.post.call_args[1]
    assert call_kwargs["json"]["displayName"] == "IR Reports"
    assert call_kwargs["json"]["list"]["template"] == "documentLibrary"


@pytest.mark.asyncio
async def test_resolve_drive_id_raises_if_creation_fails():
    """Raises ValueError when library creation succeeds but drive still not found."""
    plugin = SharePointPlugin()
    empty_drives = _mock_json_response({"value": []})
    create_resp = _mock_json_response({})
    still_empty = _mock_json_response({"value": []})
    client = _make_client(
        get_side_effects=[empty_drives, still_empty],
        post_return=create_resp,
    )

    with patch("app.plugins.integrations.sharepoint.httpx.AsyncClient", return_value=client):
        with pytest.raises(ValueError, match="could not be created or found"):
            await plugin._resolve_drive_id("site-1", "IR Reports", "tok")
```

- [ ] **Step 2: Run to confirm all three tests FAIL**

```
cd backend && pytest tests/unit/test_sharepoint_plugin.py -v
```

Expected: `FAILED` on all three — the plugin has no library-creation logic yet.

### Step 3: Implement library creation in `_resolve_drive_id`

Replace the entire `_resolve_drive_id` method in `backend/app/plugins/integrations/sharepoint.py`:

```python
async def _resolve_drive_id(self, site_id: str, library_name: str, token: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{_GRAPH_BASE}/sites/{site_id}/drives",
            headers=headers,
        )
        r.raise_for_status()
        drives = r.json().get("value", [])
        for drive in drives:
            if drive.get("name", "").lower() == library_name.lower():
                return drive["id"]

        # Library not found — create it
        r = await client.post(
            f"{_GRAPH_BASE}/sites/{site_id}/lists",
            json={"displayName": library_name, "list": {"template": "documentLibrary"}},
            headers={**headers, "Content-Type": "application/json"},
        )
        r.raise_for_status()

        # Re-fetch drives to get the newly created library's drive ID
        r = await client.get(
            f"{_GRAPH_BASE}/sites/{site_id}/drives",
            headers=headers,
        )
        r.raise_for_status()
        drives = r.json().get("value", [])
        for drive in drives:
            if drive.get("name", "").lower() == library_name.lower():
                return drive["id"]

        raise ValueError(f"Document library '{library_name}' could not be created or found")
```

- [ ] **Step 4: Run tests — all three must PASS**

```
cd backend && pytest tests/unit/test_sharepoint_plugin.py -v
```

Expected: `PASSED` for all three.

- [ ] **Step 5: Commit**

```
git add backend/tests/unit/test_sharepoint_plugin.py backend/app/plugins/integrations/sharepoint.py
git commit -m "feat(sharepoint): create document library via Graph if not found"
```

---

## Task 2: `push_report` — incident folder path (TDD)

**Files:**
- Modify: `backend/tests/unit/test_sharepoint_plugin.py`
- Modify: `backend/app/plugins/integrations/sharepoint.py`

### Step 1: Add failing tests to `test_sharepoint_plugin.py`

Append these tests to `backend/tests/unit/test_sharepoint_plugin.py`:

```python
@pytest.mark.asyncio
async def test_push_report_uploads_into_incident_folder():
    """Upload URL includes {incident_ref}/{filename} when _incident_ref is in config."""
    plugin = SharePointPlugin()

    token_resp = _mock_json_response({"access_token": "tok"})
    site_resp = _mock_json_response({"id": "site-1"})
    drives_resp = _mock_json_response({"value": [{"id": "drv-1", "name": "IR Reports"}]})
    upload_resp = _mock_json_response({"webUrl": "https://sp.example/INC-2026-0021/report.pdf"})

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.post = AsyncMock(return_value=token_resp)
    client.get = AsyncMock(side_effect=[site_resp, drives_resp])
    client.put = AsyncMock(return_value=upload_resp)

    config = {
        "tenant_id": "t1", "client_id": "c1", "client_secret": "s1",
        "site_url": "https://company.sharepoint.com/sites/SOC",
        "library": "IR Reports",
        "_incident_ref": "INC-2026-0021",
    }

    with patch("app.plugins.integrations.sharepoint.httpx.AsyncClient", return_value=client):
        url = await plugin.push_report(b"pdf", "INC-2026-0021 - Executive Summary.pdf", config)

    assert url == "https://sp.example/INC-2026-0021/report.pdf"
    put_url = client.put.call_args[0][0]
    assert "INC-2026-0021/INC-2026-0021 - Executive Summary.pdf" in put_url


@pytest.mark.asyncio
async def test_push_report_falls_back_to_root_without_incident_ref():
    """Upload URL does NOT include a folder prefix when _incident_ref is absent."""
    plugin = SharePointPlugin()

    token_resp = _mock_json_response({"access_token": "tok"})
    site_resp = _mock_json_response({"id": "site-1"})
    drives_resp = _mock_json_response({"value": [{"id": "drv-1", "name": "IR Reports"}]})
    upload_resp = _mock_json_response({"webUrl": "https://sp.example/report.pdf"})

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.post = AsyncMock(return_value=token_resp)
    client.get = AsyncMock(side_effect=[site_resp, drives_resp])
    client.put = AsyncMock(return_value=upload_resp)

    config = {
        "tenant_id": "t1", "client_id": "c1", "client_secret": "s1",
        "site_url": "https://company.sharepoint.com/sites/SOC",
        "library": "IR Reports",
    }

    with patch("app.plugins.integrations.sharepoint.httpx.AsyncClient", return_value=client):
        await plugin.push_report(b"pdf", "report.pdf", config)

    put_url = client.put.call_args[0][0]
    assert put_url.endswith("/root:/report.pdf:/content")
```

- [ ] **Step 2: Run to confirm both new tests FAIL**

```
cd backend && pytest tests/unit/test_sharepoint_plugin.py::test_push_report_uploads_into_incident_folder tests/unit/test_sharepoint_plugin.py::test_push_report_falls_back_to_root_without_incident_ref -v
```

Expected: `FAILED` — current `push_report` doesn't use `_incident_ref`.

### Step 3: Implement incident folder path in `push_report`

Replace the `push_report` method in `backend/app/plugins/integrations/sharepoint.py`:

```python
async def push_report(self, report_bytes: bytes, filename: str, config: dict) -> str:
    """Upload bytes to SharePoint into an incident subfolder. Returns webUrl."""
    token = await self._get_token(config)
    site_id = await self._resolve_site_id(config["site_url"], token)
    drive_id = await self._resolve_drive_id(site_id, config.get("library", "IR Reports"), token)

    incident_ref = config.get("_incident_ref", "")
    upload_path = f"{incident_ref}/{filename}" if incident_ref else filename

    upload_url = f"{_GRAPH_BASE}/drives/{drive_id}/root:/{upload_path}:/content"
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.put(
            upload_url,
            content=report_bytes,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/octet-stream",
            },
        )
        r.raise_for_status()
        return r.json().get("webUrl", "")
```

- [ ] **Step 4: Run the full test file — all five tests must PASS**

```
cd backend && pytest tests/unit/test_sharepoint_plugin.py -v
```

Expected: all 5 tests `PASSED`.

- [ ] **Step 5: Commit**

```
git add backend/tests/unit/test_sharepoint_plugin.py backend/app/plugins/integrations/sharepoint.py
git commit -m "feat(sharepoint): upload reports into incident subfolder via path prefix"
```

---

## Task 3: Inject `_incident_ref` in both task callers

**Files:**
- Modify: `backend/app/workers/tasks.py`

### Step 1: Update `push_report_to_sharepoint`

In `backend/app/workers/tasks.py`, find the block inside `push_report_to_sharepoint` that calls `sp_plugin().push_report`. It currently reads:

```python
            sp_plugin = PLUGINS.get("sharepoint")
            if not sp_plugin:
                raise RuntimeError("SharePoint plugin not loaded")

            sharepoint_url = await sp_plugin().push_report(file_bytes, filename, config)
```

Replace with:

```python
            sp_plugin = PLUGINS.get("sharepoint")
            if not sp_plugin:
                raise RuntimeError("SharePoint plugin not loaded")

            incident_ref = incident.incident_ref if incident else ""
            sharepoint_url = await sp_plugin().push_report(
                file_bytes, filename, {**config, "_incident_ref": incident_ref}
            )
```

### Step 2: Update `sync_to_sharepoint`

In `backend/app/workers/tasks.py`, find the block inside `sync_to_sharepoint` that calls `sp_plugin().push_report`. It currently reads:

```python
            config = decrypt_config(dict(policy.destination_config))
            sp_plugin = PLUGINS.get("sharepoint")
            if not sp_plugin:
                raise RuntimeError("SharePoint plugin not loaded")

            sharepoint_url = await sp_plugin().push_report(report_bytes, filename, config)
```

Replace with:

```python
            config = decrypt_config(dict(policy.destination_config))
            sp_plugin = PLUGINS.get("sharepoint")
            if not sp_plugin:
                raise RuntimeError("SharePoint plugin not loaded")

            sharepoint_url = await sp_plugin().push_report(
                report_bytes, filename, {**config, "_incident_ref": payload.incident.incident_ref}
            )
```

- [ ] **Step 3: Run the full test suite to ensure no regressions**

```
cd backend && pytest tests/unit/ -v
```

Expected: all unit tests `PASSED`.

- [ ] **Step 4: Commit**

```
git add backend/app/workers/tasks.py
git commit -m "feat(sharepoint): pass incident_ref to push_report for folder routing"
```

---

## Task 4: Update `docs/sharepoint-sync-setup.md`

**Files:**
- Modify: `docs/sharepoint-sync-setup.md`

### Step 1: Update the "Document library name" subsection

Find this block (around line 132):

```markdown
### Document library name

The **Document Library** field must exactly match the library's name as shown in SharePoint (case-insensitive). The default is `IR Reports`. If the library doesn't exist, IRDoc falls back to the site's default document library.

To create a dedicated library:
1. Browse to your SharePoint site
2. Click **+ New → Document library**
3. Name it `IR Reports` (or whatever you put in the IRDoc field)
```

Replace with:

```markdown
### Document library name

The **Document Library** field must exactly match the library's name as shown in SharePoint (case-insensitive). The default is `IR Reports`. If the library doesn't exist, IRDoc creates it automatically using the Microsoft Graph API — no manual setup required.

### Folder structure

Inside the document library, IRDoc organises reports into per-incident subfolders. The folder is named after the incident reference and is created automatically on the first sync:

```
IR Reports/
├── INC-2026-0021/
│   ├── INC-2026-0021 - Executive Summary.pdf
│   └── INC-2026-0021 - Technical Report.pdf
└── INC-2026-0022/
    └── INC-2026-0022 - Management Brief.pdf
```

The filename inside each folder follows the configured **Filename Pattern** unchanged.
```

### Step 2: Update the troubleshooting entry "Files appear in the wrong library"

Find (around line 188):

```markdown
**Files appear in the wrong library**
The Document Library name is case-insensitive but must match exactly. Check the library name in SharePoint. IRDoc falls back to the default document library if the named one isn't found.
```

Replace with:

```markdown
**Files appear in the wrong library**
The Document Library name is case-insensitive but must match exactly. If the named library is not found, IRDoc creates it automatically — so if creation is failing, verify that `Sites.ReadWrite.All` admin consent is granted in the Azure portal (required for library creation as well as uploads).
```

- [ ] **Step 3: Commit**

```
git add docs/sharepoint-sync-setup.md
git commit -m "docs(sharepoint): document library auto-creation and incident folder structure"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered in |
|---|---|
| SharePoint Site URL field (already exists) | No change needed — field exists in `config_schema` |
| Document Library field (already exists) | No change needed |
| Create library if it doesn't exist | Task 1 |
| Per-incident subfolder `{incident_ref}/` | Task 2 |
| Reports uploaded inside the incident folder | Tasks 2 + 3 |
| Filename pattern unchanged | Task 2 (`filename` arg unchanged, only path prefix added) |
| Docs updated | Task 4 |

**Placeholder scan:** None found.

**Type/name consistency:**
- `_incident_ref` key used consistently in Task 2 (plugin reads it) and Task 3 (tasks write it).
- `_resolve_drive_id` signature unchanged — compatible across all tasks.
- `push_report` signature unchanged — `config` dict carries the new transient key.
