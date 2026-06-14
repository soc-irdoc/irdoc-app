# SharePoint Incident Folder Structure — Design Spec

**Date:** 2026-06-14
**Status:** Approved

---

## Problem

Reports are currently uploaded flat to the SharePoint document library root. If the configured library doesn't exist, IRDoc silently falls back to the site's default library. There is no per-incident organisation.

## Goal

- Every report is saved inside `{library}/{incident_ref}/{filename}` — one subfolder per incident.
- If the configured document library doesn't exist, IRDoc creates it automatically.
- Filename pattern is unchanged (`{incident_ref} - {template_name}.pdf`).

---

## Approach

**Option A — Path prefix in the filename** (chosen)

Microsoft Graph's path-based upload endpoint (`PUT /drives/{drive_id}/root:/{path}:/content`) auto-creates intermediate folders. Prepending `{incident_ref}/` to the filename string gives the desired folder hierarchy at zero extra API calls on subsequent uploads.

Library creation is the only new logic in the plugin.

---

## Changes

### 1. `backend/app/plugins/integrations/sharepoint.py`

#### `_resolve_drive_id` — create library if missing

Current: falls back to the site's default document library when the named one isn't found.

New behaviour:
1. List drives (`GET /sites/{site_id}/drives`).
2. If the named library is found → return its drive ID (unchanged).
3. If not found → create it via `POST /sites/{site_id}/lists` with body `{ "displayName": library_name, "list": { "template": "documentLibrary" } }`.
4. Re-fetch drives and return the new drive's ID.
5. If creation fails → raise (no silent fallback).

Required Graph permission: `Sites.ReadWrite.All` (already required).

#### `push_report` — prepend incident folder to upload path

Current upload URL:
```
PUT /drives/{drive_id}/root:/{filename}:/content
```

New upload URL:
```
PUT /drives/{drive_id}/root:/{incident_ref}/{filename}:/content
```

`incident_ref` is read from `config["_incident_ref"]` (a transient key injected by the Celery task — never stored or persisted).

If `_incident_ref` is absent (defensive), fall back to uploading at the root (existing behaviour).

---

### 2. `backend/app/workers/tasks.py`

Both callers of `push_report` already have `incident_ref` in scope:

- `push_report_to_sharepoint`: has `incident` object → `incident.incident_ref`
- `sync_to_sharepoint`: has `payload.incident.incident_ref`

Before each `push_report` call, inject into a shallow config copy:

```python
config_with_folder = {**config, "_incident_ref": incident.incident_ref}
sharepoint_url = await sp_plugin().push_report(file_bytes, filename, config_with_folder)
```

No other task logic changes.

---

### 3. `docs/sharepoint-sync-setup.md`

- **"Document library name" section**: replace "IRDoc falls back to the default document library if the named one isn't found" with "if the library doesn't exist, IRDoc creates it automatically."
- **New "Folder structure" section**: explain `{library}/{INC-YYYY-NNNN}/{filename}` layout; note folders are created on first sync per incident.
- **Troubleshooting**: update the "Files appear in the wrong library" entry; remove outdated fallback note.

---

## Data flow

```
Task (push_report_to_sharepoint | sync_to_sharepoint)
  │
  ├─ build filename from pattern  →  "INC-2026-0021 - Executive Summary.pdf"
  ├─ inject _incident_ref into config copy
  │
  └─ SharePointPlugin.push_report(bytes, filename, config)
       │
       ├─ _get_token()
       ├─ _resolve_site_id()
       ├─ _resolve_drive_id()   ← creates library if missing
       │
       └─ PUT root:/INC-2026-0021/INC-2026-0021 - Executive Summary.pdf:/content
            (Graph auto-creates folder on first upload)
```

---

## Error handling

| Scenario | Behaviour |
|---|---|
| Library not found | Create via Graph API; raise on failure |
| Library creation fails (permissions) | Exception propagates → Celery retries (max 3) |
| `_incident_ref` missing in config | Fall back to flat root upload (defensive) |
| Folder already exists | Graph handles silently (no conflict) |
| File already exists | Overwritten (existing behaviour, unchanged) |

---

## Permissions

No new permissions required. `Sites.ReadWrite.All` already covers list/drive creation.

---

## Out of scope

- Removing the `filename_pattern` field or simplifying filenames inside the incident folder.
- Sub-folders beyond one level (e.g. by year or severity).
- Migrating existing flat-uploaded files into the new folder structure.
