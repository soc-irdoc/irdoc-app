# IRDoc API Developer Guide

This guide is for developers and security engineers who want to build automations
on top of IRDoc — creating incidents from SIEM alerts, enriching them programmatically,
or exporting data to external systems.

**Base URL:** `https://your-irdoc-instance/api/v1`

**Interactive API Explorer:** Once IRDoc is running, visit `/api/docs` for the live
Swagger UI where you can test every endpoint in the browser.

---

## Authentication

IRDoc supports two authentication methods. Which one to use depends on what you
are trying to do.

### Method 1 — API Key (for webhook integrations)

API keys give external tools a simple way to **push incidents into IRDoc** without
needing a user account. They authenticate a single endpoint: `POST /external/incidents`.

**Create a key:**
1. Log in as Admin → Settings → API Keys → Create Key
2. Give it a name (e.g. "SIEM Integration") and select the scope `incidents:create`
3. Copy the raw key — it is shown **once only** and looks like:
   ```
   irp_key_a3f92b1c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1
   ```

**Use the key in requests:**
```
Authorization: ApiKey irp_key_a3f92b1c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1
```

**Available scopes:**

| Scope | Purpose |
|-------|---------|
| `incidents:create` | Create incidents via `POST /external/incidents` |
| `incidents:read` | (Reserved for future endpoints) |
| `incidents:write` | (Reserved for future endpoints) |
| `timeline:read` | (Reserved for future endpoints) |
| `iocs:read` | (Reserved for future endpoints) |
| `reports:read` | (Reserved for future endpoints) |

---

### Method 2 — JWT Bearer Token (for full API access)

All other endpoints (read/update incidents, timeline, IOCs, tasks, reports, etc.)
require a JWT from a user login. This is the right approach for scripts that need
to read or enrich data.

**Step 1 — Log in and get a token:**
```bash
curl -s -X POST https://your-irdoc-instance/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "analyst@example.com", "password": "your-password"}' \
  | python3 -m json.tool
```

Response:
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5...",
    "user": { "id": "...", "role": "analyst", "email": "analyst@example.com" }
  },
  "meta": {},
  "error": null
}
```

> **Note on MFA:** If your organisation enforces multi-factor authentication, the login response will contain `mfa_challenge_token` instead of `access_token`. In that case, complete the TOTP verification step via `POST /auth/mfa/verify` before making API calls. Scripts targeting MFA-enabled orgs should handle this case or use a dedicated service account with MFA disabled.

**Step 2 — Use the token in subsequent requests:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5...
```

Access tokens expire in **15 minutes**. For long-running scripts, call the login
endpoint again to get a fresh token, or implement refresh token logic.

> **Role required:** The user whose credentials you use determines what the token
> can do. Role hierarchy: `viewer → analyst → senior_analyst → admin`. Each endpoint
> documents its minimum required role below.

---

## Response Envelope

All endpoints wrap responses in a consistent envelope:

```json
{
  "data": { ... },
  "meta": { "page": 1, "per_page": 50, "total": 123 },
  "error": null
}
```

- `data` — the requested resource(s). Array for list endpoints, object for single.
- `meta` — pagination info on list endpoints (`page`, `per_page`, `total`).
- `error` — always `null` on success; not used (errors use HTTP status codes).

**DELETE endpoints** return `204 No Content` with an empty body.

---

## Error Responses

```json
{ "detail": "Insufficient permissions: incidents.delete requires role senior_analyst" }
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request or business rule violation |
| 401 | Missing or invalid authentication |
| 403 | Insufficient role, wrong token type, or missing scope |
| 404 | Resource not found (or not in your org) |
| 413 | Payload too large (webhook endpoint) |
| 422 | Request body failed validation — `detail` lists the fields |
| 429 | Rate limited — slow down and retry |

---

## Endpoint Reference

### Incidents

#### List Incidents
`GET /incidents`
**Auth:** JWT, minimum role: `viewer`

| Query param | Type | Default | Description |
|-------------|------|---------|-------------|
| `status` | string | — | Filter: `open`, `contained`, `monitoring`, `closed` |
| `severity` | string | — | Filter: `sev1`, `sev2`, `sev3`, `sev4` |
| `search` | string | — | Full-text search on title |
| `page` | int | 1 | Page number |
| `per_page` | int | 50 | Results per page (max 200) |

```bash
curl -s "https://your-irdoc-instance/api/v1/incidents?status=open&per_page=10" \
  -H "Authorization: Bearer $TOKEN"
```

Response (truncated):
```json
{
  "data": [
    {
      "id": "018e1a2b-3c4d-5e6f-7890-abcdef012345",
      "incident_ref": "INC-2026-0042",
      "title": "Phishing campaign targeting finance",
      "severity": "sev2",
      "status": "open",
      "opened_at": "2026-06-13T08:30:00Z",
      "assigned_user": { "id": "...", "full_name": "Alice Smith", "email": "alice@example.com" },
      "attack_vector": [],
      "affected_users": 0,
      "external_refs": []
    }
  ],
  "meta": { "page": 1, "per_page": 10, "total": 3 },
  "error": null
}
```

---

#### Create Incident
`POST /incidents` → `201 Created`
**Auth:** JWT, minimum role: `analyst`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Incident title |
| `severity` | string | No | `sev1`–`sev4`, default `sev2` |
| `template_id` | UUID | No | Pre-populate tasks from a template |
| `assigned_to` | UUID | No | User ID to assign immediately |

```bash
curl -s -X POST https://your-irdoc-instance/api/v1/incidents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Suspected ransomware — endpoint-012",
    "severity": "sev1"
  }'
```

Response: full `Incident` object (same shape as the list item above).

---

#### Get Incident
`GET /incidents/{incident_id}`
**Auth:** JWT, minimum role: `viewer`

```bash
curl -s "https://your-irdoc-instance/api/v1/incidents/018e1a2b-3c4d-5e6f-7890-abcdef012345" \
  -H "Authorization: Bearer $TOKEN"
```

---

#### Update Incident
`PUT /incidents/{incident_id}`
**Auth:** JWT, minimum role: `analyst`

All fields are optional — send only what you want to change.

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Rename the incident |
| `severity` | string | `sev1`–`sev4` |
| `status` | string | `open`, `contained`, `monitoring`, `closed` |
| `executive_summary` | string | Rich-text summary (HTML) |
| `notes` | string | Rich-text notes (HTML) |
| `lessons_learned` | string | Rich-text lessons (HTML) |
| `actions_todo` | string | Rich-text actions (HTML) |
| `attack_vector` | string[] | e.g. `["phishing", "credential_stuffing"]` |
| `affected_users` | int | Count of affected users |
| `assigned_to` | UUID | Reassign; `null` to unassign |
| `metadata` | object | Custom key/value fields |

```bash
curl -s -X PUT \
  "https://your-irdoc-instance/api/v1/incidents/018e1a2b-3c4d-5e6f-7890-abcdef012345" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "contained", "affected_users": 14}'
```

---

#### Delete Incident
`DELETE /incidents/{incident_id}` → `204 No Content`
**Auth:** JWT, minimum role: `senior_analyst`

Permanently deletes the incident and all its timeline entries, IOCs, tasks, and
attachments. This is irreversible.

```bash
curl -s -X DELETE \
  "https://your-irdoc-instance/api/v1/incidents/018e1a2b-3c4d-5e6f-7890-abcdef012345" \
  -H "Authorization: Bearer $TOKEN"
```

Returns `204` with no body on success.

---

#### Get Incident Stats
`GET /incidents/{incident_id}/stats`
**Auth:** JWT, minimum role: `viewer`

```bash
curl -s "https://your-irdoc-instance/api/v1/incidents/018e1a2b-3c4d-5e6f-7890-abcdef012345/stats" \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "timeline_count": 12,
  "ioc_count": 5,
  "task_total": 8,
  "task_done": 3,
  "attachment_count": 2,
  "duration_hours": 14.5
}
```

---

#### List External References
`GET /incidents/{incident_id}/external-refs`
**Auth:** JWT, minimum role: `viewer`

Returns references to linked tickets (ServiceDesk Plus, Jira, etc.).

---

#### Add External Reference
`POST /incidents/{incident_id}/external-refs` → `201 Created`
**Auth:** JWT, minimum role: `analyst`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `external_source` | string | Yes | e.g. `"servicedesk_plus"`, `"jira"` |
| `external_ref` | string | Yes | Ticket ID, e.g. `"SDP-2026-4421"` |
| `external_url` | string | No | Deep-link URL to the original ticket |

```bash
curl -s -X POST \
  "https://your-irdoc-instance/api/v1/incidents/018e1a2b-3c4d-5e6f-7890-abcdef012345/external-refs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "external_source": "jira",
    "external_ref": "SEC-1234",
    "external_url": "https://jira.example.com/browse/SEC-1234"
  }'
```

---

### Timeline

#### List Timeline Entries
`GET /incidents/{incident_id}/timeline`
**Auth:** JWT, minimum role: `viewer`

| Query param | Type | Description |
|-------------|------|-------------|
| `entry_type` | string | Filter by type (see below) |
| `page` | int | Page number |
| `per_page` | int | Default 100, max 500 |

```bash
curl -s "https://your-irdoc-instance/api/v1/incidents/018e1a2b-3c4d-5e6f-7890-abcdef012345/timeline" \
  -H "Authorization: Bearer $TOKEN"
```

---

#### Create Timeline Entry
`POST /incidents/{incident_id}/timeline` → `201 Created`
**Auth:** JWT, minimum role: `analyst`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entry_type` | string | Yes | `detection`, `analysis`, `containment`, `evidence`, `comms`, `note` |
| `occurred_at` | datetime | Yes | ISO 8601 timestamp of when the event occurred |
| `description` | string | Yes | Rich text or plain text describing what happened |
| `source` | string | No | Default `"manual"`. Use `"siem"`, `"edr"`, etc. for automated entries |
| `is_pinned` | bool | No | Pin to top of timeline, default `false` |
| `metadata` | object | No | Custom key/value pairs |

```bash
curl -s -X POST \
  "https://your-irdoc-instance/api/v1/incidents/018e1a2b-3c4d-5e6f-7890-abcdef012345/timeline" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entry_type": "detection",
    "occurred_at": "2026-06-13T08:15:00Z",
    "description": "CrowdStrike alert: process injection detected on endpoint-012",
    "source": "crowdstrike",
    "metadata": {"alert_id": "CSA-2026-88231", "host": "endpoint-012"}
  }'
```

After creating a timeline entry, IRDoc automatically queues an IOC auto-detection
scan on the description text and may suggest indicators.

---

#### Update Timeline Entry
`PUT /incidents/{incident_id}/timeline/{entry_id}`
**Auth:** JWT, minimum role: `analyst`

Same fields as create, all optional.

---

#### Delete Timeline Entry
`DELETE /incidents/{incident_id}/timeline/{entry_id}` → `204 No Content`
**Auth:** JWT, minimum role: `senior_analyst`

---

#### Pin / Unpin Timeline Entry
`POST /incidents/{incident_id}/timeline/{entry_id}/pin?pinned=true`
**Auth:** JWT, minimum role: `senior_analyst`

Pass `?pinned=false` to unpin.

---

#### Export Timeline to CSV
`GET /incidents/{incident_id}/timeline/export/csv`
**Auth:** JWT, minimum role: `viewer`

Returns a CSV file download (`Content-Disposition: attachment`).

```bash
curl -s \
  "https://your-irdoc-instance/api/v1/incidents/018e1a2b-3c4d-5e6f-7890-abcdef012345/timeline/export/csv" \
  -H "Authorization: Bearer $TOKEN" \
  --output timeline.csv
```

---

### IOCs (Indicators of Compromise)

#### List IOCs
`GET /incidents/{incident_id}/iocs`
**Auth:** JWT, minimum role: `viewer`

```bash
curl -s \
  "https://your-irdoc-instance/api/v1/incidents/018e1a2b-3c4d-5e6f-7890-abcdef012345/iocs" \
  -H "Authorization: Bearer $TOKEN"
```

Response includes `enrichment` object populated automatically by VirusTotal
(if configured).

---

#### Create IOC
`POST /incidents/{incident_id}/iocs` → `201 Created`
**Auth:** JWT, minimum role: `analyst`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ioc_type` | string | Yes | `email`, `domain`, `ip`, `url`, `hash`, `file`, `username` |
| `value` | string | Yes | The indicator value, e.g. `"185.220.101.45"` |
| `description` | string | No | Context for this indicator |
| `confidence` | int | No | 0–100, default 50 |
| `status` | string | No | `active`, `blocked`, `remediated`, `fp` — default `active` |
| `tlp_level` | string | No | `red`, `amber`, `green`, `white` — default `red` |
| `tags` | string[] | No | e.g. `["c2", "tor-exit-node"]` |

```bash
curl -s -X POST \
  "https://your-irdoc-instance/api/v1/incidents/018e1a2b-3c4d-5e6f-7890-abcdef012345/iocs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ioc_type": "ip",
    "value": "185.220.101.45",
    "description": "C2 server observed in Wireshark capture",
    "confidence": 90,
    "tlp_level": "amber",
    "tags": ["c2", "ransomware"]
  }'
```

---

#### Bulk Import IOCs
`POST /incidents/{incident_id}/iocs/bulk` → `201 Created`
**Auth:** JWT, minimum role: `analyst`

Paste raw text containing indicators — the server auto-detects IP addresses,
domains, URLs, and hashes.

```bash
curl -s -X POST \
  "https://your-irdoc-instance/api/v1/incidents/018e1a2b-3c4d-5e6f-7890-abcdef012345/iocs/bulk" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "C2 IPs observed:\n185.220.101.45\n194.165.16.76\nDomain: evil-corp.ru\nHash: 44d88612fea8a8f36de82e1278abb02f"
  }'
```

Returns an array of created IOC objects.

---

#### Update IOC
`PUT /incidents/{incident_id}/iocs/{ioc_id}`
**Auth:** JWT, minimum role: `analyst`

Update `description`, `confidence`, `status`, `tlp_level`, or `tags`.

---

#### Delete IOC
`DELETE /incidents/{incident_id}/iocs/{ioc_id}` → `204 No Content`
**Auth:** JWT, minimum role: `senior_analyst`

---

### Tasks

#### List Tasks
`GET /incidents/{incident_id}/tasks`
**Auth:** JWT, minimum role: `viewer`

---

#### Create Task
`POST /incidents/{incident_id}/tasks` → `201 Created`
**Auth:** JWT, minimum role: `analyst`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Task description |
| `description` | string | No | Extended notes |
| `phase` | string | No | e.g. `"containment"`, `"eradication"` |
| `priority` | string | No | `critical`, `high`, `medium`, `low` — default `medium` |
| `assigned_to` | UUID | No | User ID |
| `sort_order` | int | No | Display order, default 0 |

```bash
curl -s -X POST \
  "https://your-irdoc-instance/api/v1/incidents/018e1a2b-3c4d-5e6f-7890-abcdef012345/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Isolate endpoint-012 from network",
    "phase": "containment",
    "priority": "critical"
  }'
```

---

#### Update Task
`PUT /incidents/{incident_id}/tasks/{task_id}`
**Auth:** JWT, minimum role: `analyst`

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Rename the task |
| `status` | string | `pending`, `in_progress`, `done`, `skipped` |
| `priority` | string | `critical`, `high`, `medium`, `low` |
| `assigned_to` | UUID | Reassign; `null` to unassign |

```bash
curl -s -X PUT \
  "https://your-irdoc-instance/api/v1/incidents/018e1a2b-3c4d-5e6f-7890-abcdef012345/tasks/TASK_UUID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

#### Delete Task
`DELETE /incidents/{incident_id}/tasks/{task_id}` → `204 No Content`
**Auth:** JWT, minimum role: `senior_analyst`

---

### Assets

Assets are devices, accounts, or services involved in the incident.

#### List Assets
`GET /incidents/{incident_id}/assets`
**Auth:** JWT, minimum role: `viewer`

---

#### Create Asset
`POST /incidents/{incident_id}/assets` → `201 Created`
**Auth:** JWT, minimum role: `analyst`

See the Swagger UI at `/api/docs` for the full `AssetCreate` schema.

---

#### Update Asset
`PUT /incidents/{incident_id}/assets/{asset_id}`
**Auth:** JWT, minimum role: `analyst`

---

#### Delete Asset
`DELETE /incidents/{incident_id}/assets/{asset_id}` → `204 No Content`
**Auth:** JWT, minimum role: `senior_analyst`

---

### Reports

Reports are generated asynchronously. The workflow is: enqueue → poll for ready → download.

#### Enqueue Report Generation
`POST /incidents/{incident_id}/reports` → `202 Accepted`
**Auth:** JWT, minimum role: `viewer`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `report_template_id` | UUID | No | Custom report template; omit for default |
| `pdf_template_id` | UUID | No | PDF layout template |
| `classification` | string | No | Default `"confidential"` |
| `include_ai` | bool | No | Include AI-generated summary |

```bash
curl -s -X POST \
  "https://your-irdoc-instance/api/v1/incidents/018e1a2b-3c4d-5e6f-7890-abcdef012345/reports" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"classification": "confidential"}'
```

Response includes a report `id` and `status: "pending"`.

---

#### Check Report Status
`GET /reports/{report_id}`
**Auth:** JWT, minimum role: `viewer`

```bash
curl -s "https://your-irdoc-instance/api/v1/reports/REPORT_UUID" \
  -H "Authorization: Bearer $TOKEN"
```

The `status` field progresses: `pending` → `processing` → `ready` (or `failed`).
Poll every few seconds until `status == "ready"`.

---

#### Download Report
`GET /reports/{report_id}/download`
**Auth:** JWT, minimum role: `viewer`

Returns the PDF as a binary stream.

```bash
curl -s "https://your-irdoc-instance/api/v1/reports/REPORT_UUID/download" \
  -H "Authorization: Bearer $TOKEN" \
  --output incident-report.pdf
```

---

#### List Reports for an Incident
`GET /incidents/{incident_id}/reports`
**Auth:** JWT, minimum role: `viewer`

---

#### Delete Report
`DELETE /reports/{report_id}` → `204 No Content`
**Auth:** JWT, minimum role: `viewer`

---

### API Keys *(Admin only)*

#### List API Keys
`GET /api-keys`
**Auth:** JWT, minimum role: `admin`

Returns all active API keys for your organisation. The raw key is never returned
after creation.

---

#### Create API Key
`POST /api-keys` → `201 Created`
**Auth:** JWT, minimum role: `admin`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Human-readable label, e.g. `"SIEM Integration"` |
| `scopes` | string[] | No | List of scopes to grant (see Scopes table above) |
| `expires_at` | datetime | No | Optional expiry; omit for no expiry |

```bash
curl -s -X POST https://your-irdoc-instance/api/v1/api-keys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SIEM Integration",
    "scopes": ["incidents:create"],
    "expires_at": "2027-01-01T00:00:00Z"
  }'
```

Response includes `raw_key` — **copy it now, it will not be shown again**.

---

#### Revoke API Key
`DELETE /api-keys/{key_id}` → `204 No Content`
**Auth:** JWT, minimum role: `admin`

Soft-deletes the key (sets `is_active = false`). The key immediately stops working.

---

### Users *(Admin only)*

#### List Users
`GET /users`
**Auth:** JWT, minimum role: `viewer`

Returns all active users in your organisation.

---

#### Update User Role
`PUT /users/{user_id}/role`
**Auth:** JWT, minimum role: `admin`

```bash
curl -s -X PUT "https://your-irdoc-instance/api/v1/users/USER_UUID/role" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "senior_analyst"}'
```

Valid roles: `viewer`, `analyst`, `senior_analyst`, `admin`. Cannot demote
the last admin in the organisation.

---

#### Deactivate User
`PUT /users/{user_id}/deactivate`
**Auth:** JWT, minimum role: `admin`

Soft-deletes the account. Cannot deactivate yourself or the last admin.

---

#### Invite User
`POST /users/invite` → `201 Created`
**Auth:** JWT, minimum role: `admin`

Sends an invitation email. The recipient sets their own password via the invite link.

```bash
curl -s -X POST https://your-irdoc-instance/api/v1/users/invite \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "newanalyst@example.com", "role": "analyst"}'
```

---

## Webhook / External Incident Endpoint

This is the primary API key–authenticated endpoint. Use it to push incidents from
any tool that can make an HTTP POST — SIEM platforms, EDR consoles, ticketing
systems, scripts.

#### Create Incident via Webhook
`POST /external/incidents` → `201 Created`
**Auth:** API key with `incidents:create` scope

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Incident title |
| `severity` | string | No | `sev1`–`sev4`, default `sev2` |
| `template` | string | No | Template slug to pre-populate tasks, default `"blank"` |
| `external_ref` | string | No | Ticket/alert ID from the source system |
| `external_source` | string | No | Source label, e.g. `"crowdstrike"`, `"splunk"` |
| `external_url` | string | No | Deep-link to the original alert/ticket |
| `description` | string | No | Pre-populates the first timeline entry |
| `reported_by` | string | No | Email of the original reporter |

```bash
curl -s -X POST https://your-irdoc-instance/api/v1/external/incidents \
  -H "Authorization: ApiKey irp_key_a3f92b1c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Brute-force login attempts — admin panel",
    "severity": "sev2",
    "external_ref": "SPLUNK-20260613-4821",
    "external_source": "splunk",
    "external_url": "https://splunk.example.com/alerts/4821",
    "description": "440 failed login attempts in 5 minutes from 185.220.101.45",
    "reported_by": "splunk-alert@example.com"
  }'
```

Response:
```json
{
  "incident_id": "018e1a2b-3c4d-5e6f-7890-abcdef012345",
  "incident_ref": "INC-2026-0043",
  "external_ref": "SPLUNK-20260613-4821",
  "workspace_url": "https://your-irdoc-instance/incidents/018e1a2b-3c4d-5e6f-7890-abcdef012345"
}
```

The `workspace_url` is a direct link to the new incident in IRDoc.

---

## End-to-End Automation Examples

### Example A — Create an incident from a SIEM alert (full enrichment)

This script logs in, creates an incident, adds a timeline entry, and attaches IOCs.

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE="https://your-irdoc-instance/api/v1"
EMAIL="automation@example.com"
PASSWORD="your-password"

# 1. Authenticate
TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

# 2. Create incident
INCIDENT_ID=$(curl -s -X POST "$BASE/incidents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Lateral movement detected — srv-dc01","severity":"sev1"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")

echo "Created incident: $INCIDENT_ID"

# 3. Add initial detection timeline entry
curl -s -X POST "$BASE/incidents/$INCIDENT_ID/timeline" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entry_type": "detection",
    "occurred_at": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'",
    "description": "CrowdStrike: Pass-the-Hash detected on srv-dc01",
    "source": "crowdstrike",
    "metadata": {"alert_id": "CSA-2026-99312"}
  }' > /dev/null

# 4. Add attacker IOC
curl -s -X POST "$BASE/incidents/$INCIDENT_ID/iocs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ioc_type": "ip",
    "value": "185.220.101.45",
    "confidence": 85,
    "tlp_level": "amber",
    "tags": ["lateral-movement", "credential-theft"]
  }' > /dev/null

echo "Incident ready: https://your-irdoc-instance/incidents/$INCIDENT_ID"
```

---

### Example B — Nightly open-incident report export

Generates PDF reports for all open incidents and saves them locally.

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE="https://your-irdoc-instance/api/v1"
TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"reports@example.com","password":"your-password"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

# Get all open incidents
INCIDENT_IDS=$(curl -s "$BASE/incidents?status=open&per_page=200" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; [print(i['id']) for i in json.load(sys.stdin)['data']]")

for ID in $INCIDENT_IDS; do
  # Enqueue report generation
  REPORT_ID=$(curl -s -X POST "$BASE/incidents/$ID/reports" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"classification":"confidential"}' \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")

  # Poll until ready (max 60s)
  for i in $(seq 1 12); do
    STATUS=$(curl -s "$BASE/reports/$REPORT_ID" \
      -H "Authorization: Bearer $TOKEN" \
      | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
    [ "$STATUS" = "ready" ] && break
    sleep 5
  done

  # Download
  curl -s "$BASE/reports/$REPORT_ID/download" \
    -H "Authorization: Bearer $TOKEN" \
    --output "report_${ID:0:8}.pdf"

  echo "Downloaded report for incident $ID"
done
```

---

### Example C — Auto-close resolved incidents from a ticketing system

When a ticket is resolved in your ITSM, call this to close the linked IRDoc incident.

```bash
#!/usr/bin/env bash
set -euo pipefail

TICKET_REF="${1:-}"
BASE="https://your-irdoc-instance/api/v1"

TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"automation@example.com","password":"your-password"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

# Find the incident by searching
INCIDENT_ID=$(curl -s "$BASE/incidents?search=$TICKET_REF" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(d[0]['id'] if d else '')")

if [ -z "$INCIDENT_ID" ]; then
  echo "No incident found for $TICKET_REF"
  exit 0
fi

# Update status to closed
curl -s -X PUT "$BASE/incidents/$INCIDENT_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"closed"}' > /dev/null

# Log the closure in the timeline
curl -s -X POST "$BASE/incidents/$INCIDENT_ID/timeline" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"entry_type\": \"note\",
    \"occurred_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"description\": \"Closed automatically: linked ticket $TICKET_REF resolved in ITSM.\",
    \"source\": \"automation\"
  }" > /dev/null

echo "Incident $INCIDENT_ID closed."
```
