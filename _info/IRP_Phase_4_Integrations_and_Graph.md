# IRP Phase 4 — Integrations, IOC Enrichment, SharePoint Auto-Sync & Investigation Graph

> **Status:** Planning  
> **Depends on:** Phase 3 complete (report generation, sync policy table and UI in place)  
> **Estimated effort:** 5–6 weeks  
> **Goal:** The platform connects to real security tools. IOCs are auto-enriched. SharePoint auto-sync is fully operational — management always has a live document. The investigation graph gives analysts a visual view of the attack. The inbound webhook integrations (SDP, ManageEngine) are documented for external teams.

---

## 1. Objectives

By end of Phase 4:
- IOCs auto-enriched via VirusTotal and AbuseIPDB on creation
- SharePoint auto-sync fully operational with debounced Celery worker
- Bi-directional integration with at least 3 security tools (Sentinel, CrowdStrike, Azure AD/Entra)
- Slack / Teams webhook notifications working
- Investigation graph renders entity relationships in the frontend
- Integration plugin system fully operational (new integrations = new plugin file only)
- Inbound webhook integration guide published for SDP, ManageEngine, and Jira
- All integrations toggleable and configurable from the admin UI

---

## 2. Integration Plugin Architecture

Each integration is a Python class conforming to a Protocol, registered via a decorator. New integrations never touch core code.

```python
# app/plugins/base.py
class IntegrationPlugin(Protocol):
    name: str
    display_name: str
    category: str        # siem | edr | iam | email | ticketing | comms | ti | storage_sync
    is_premium: bool
    config_schema: dict  # JSON schema — frontend renders this as a form automatically

    async def test_connection(self, config: dict) -> bool: ...
    async def pull_alerts(self, incident_id: str, config: dict) -> list[dict]: ...
    async def enrich_ioc(self, ioc: IOC, config: dict) -> dict: ...
    async def push_report(self, report: Report, config: dict) -> str: ...
    async def send_notification(self, event: str, payload: dict, config: dict) -> bool: ...

# app/plugins/registry.py
PLUGINS: dict[str, type] = {}

def register_plugin(cls):
    PLUGINS[cls.name] = cls
    return cls
```

Integration configuration is stored per-organization in `org_integrations` with credentials Fernet-encrypted:

```sql
CREATE TABLE org_integrations (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID REFERENCES organizations(id),
    plugin_name  TEXT NOT NULL,
    is_enabled   BOOLEAN DEFAULT false,
    config       JSONB NOT NULL DEFAULT '{}',   -- encrypted at rest
    last_tested  TIMESTAMPTZ,
    last_error   TEXT,
    created_at   TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, plugin_name)
);
```

---

## 3. SharePoint Auto-Sync (Full Implementation)

The sync policy table, UI, and API endpoints were built in Phase 3. This phase delivers the actual delivery worker.

### 3.1 How the Debounce Works

```
Any write to an incident (timeline entry, task toggle, IOC added, summary edited):
  → incident_service calls: trigger_debounced_sync(incident_id)

trigger_debounced_sync(incident_id):
  → Query: are there active sync policies for this incident?
  → For each active policy:
      SET Redis key "sync_pending:{incident_id}:{policy_id}" TTL=debounce_seconds
      (If key exists, EXPIRE resets it — debounce effect)

Celery Beat runs every 10 seconds:
  → Scan for expired "sync_pending:*" keys that were set and have now expired
  → (Redis keyspace notifications are enabled: notify-keyspace-events Ex)
  → On key expiry event: enqueue sync_to_sharepoint.delay(incident_id, policy_id)
```

Using Redis keyspace notifications on key expiry is the cleanest approach — no polling, no race conditions. The Celery Beat scheduler simply subscribes to the expiry channel.

### 3.2 SharePoint Upload Worker

```python
# app/plugins/integrations/sharepoint.py

@register_plugin
class SharePointPlugin:
    name = "sharepoint"
    display_name = "SharePoint / OneDrive"
    category = "storage_sync"
    is_premium = True

    config_schema = {
        "tenant_id":    { "type": "string",   "label": "Azure Tenant ID",    "required": True },
        "client_id":    { "type": "string",   "label": "App Client ID",      "required": True },
        "client_secret":{ "type": "password", "label": "Client Secret",      "required": True },
        "site_url":     { "type": "string",   "label": "SharePoint Site URL","required": True,
                          "placeholder": "https://company.sharepoint.com/sites/SOC" },
        "library":      { "type": "string",   "label": "Document Library",   "default": "IR Reports" },
    }

    async def push_report(self, report_bytes: bytes, filename: str, config: dict) -> str:
        """
        Upload bytes to SharePoint via Microsoft Graph API.
        Uses client credentials flow (app registration, no user interaction).
        If the file already exists at that path, it is overwritten (Graph PUT).
        Returns the SharePoint item URL.
        """
        token = await self._get_access_token(config)
        site_id = await self._resolve_site_id(config["site_url"], token)
        drive_id = await self._resolve_drive_id(site_id, config["library"], token)

        upload_url = (
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}"
            f"/root:/{filename}:/content"
        )

        async with httpx.AsyncClient() as client:
            resp = await client.put(
                upload_url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/pdf"},
                content=report_bytes
            )
            resp.raise_for_status()
            return resp.json()["webUrl"]
```

### 3.3 Sync Worker Task

```python
# app/workers/tasks.py

@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def sync_to_sharepoint(self, incident_id: str, policy_id: str):
    try:
        policy = db.get(SyncPolicy, policy_id)
        if not policy or not policy.is_active:
            return

        # Render the report using the policy's linked template
        report_payload = report_service.build_payload(incident_id)
        template = db.get(ReportTemplate, policy.report_template_id)
        rendered = ReportRenderer().render(template.schema_json, report_payload, format="pdf")

        # Build filename from pattern: "{incident_ref} - {incident_title}.pdf"
        filename = policy.destination_config.get("filename_pattern", "{incident_ref}.pdf")
        filename = filename.format(
            incident_ref=report_payload.incident.incident_ref,
            incident_title=report_payload.incident.title[:50]
        )

        # Upload via SharePoint plugin
        config = decrypt(policy.destination_config)
        sp = SharePointPlugin()
        sharepoint_url = asyncio.run(sp.push_report(rendered, filename, config))

        # Update policy
        db.update(policy,
            last_synced_at=datetime.utcnow(),
            last_sync_status="success",
            last_error=None
        )

        # Notify the team
        websocket_emit("sync:complete", {
            "policy_id": policy_id,
            "url": sharepoint_url,
            "incident_id": incident_id
        }, room=incident_id)

    except Exception as exc:
        db.update(policy, last_sync_status="failed", last_error=str(exc))
        self.retry(exc=exc)
```

### 3.4 What Management Sees

Management receives a link to the SharePoint document (shared with them by the SOC admin once, at incident creation). From that point forward, every time the incident is updated, the document at that link regenerates automatically — they just refresh the page in their browser.

The document format, fields, and branding are controlled entirely by the Management Brief report template. Management never needs access to IRDoc.

---

## 4. IOC Auto-Enrichment

### 4.1 Flow

```
Analyst adds IOC → POST /iocs creates IOC row with enrichment: {}
  → API enqueues: enrich_ioc.delay(ioc_id)

Worker: enrich_ioc(ioc_id)
  → Load IOC + org integration configs
  → For each enabled enrichment plugin applicable to this IOC type:
      → Call plugin.enrich_ioc(ioc, config)
      → Merge results into enrichment JSONB
  → Recalculate confidence score
  → If AI narrative enabled: enqueue ai_ioc_narrative.delay(ioc_id)
  → Update IOC row
  → Emit WebSocket: "ioc:enriched" { ioc_id, enrichment, confidence }
```

### 4.2 Enrichment Data Structure

```json
{
  "virustotal": {
    "last_checked": "2026-03-15T10:30:00Z",
    "malicious": 47,
    "suspicious": 12,
    "harmless": 3,
    "categories": ["phishing", "malware"],
    "first_submission": "2026-03-01",
    "permalink": "https://www.virustotal.com/gui/domain/..."
  },
  "abuseipdb": {
    "last_checked": "2026-03-15T10:30:00Z",
    "abuse_confidence_score": 89,
    "country_code": "RU",
    "isp": "Aeza Group",
    "total_reports": 234,
    "num_distinct_users": 89
  },
  "shodan": {
    "ports": [80, 443, 8080],
    "hostnames": ["mail.support-secure-verify.ru"],
    "country": "RU",
    "org": "Aeza Group"
  },
  "ai_narrative": "This domain has been flagged as malicious by 47 of 64 vendors on VirusTotal, primarily categorized as phishing. It was first observed on March 1st, 2026 and is hosted by a known Russian bulletproof hosting provider."
}
```

### 4.3 Confidence Score Algorithm

```python
def calculate_confidence(enrichment: dict) -> int:
    scores = []
    if vt := enrichment.get("virustotal"):
        total = sum([vt["malicious"], vt["suspicious"], vt.get("harmless",0), vt.get("undetected",0)])
        if total > 0:
            score = (vt["malicious"] + vt["suspicious"] * 0.5) / total * 100
            scores.append((score, 0.6))
    if ab := enrichment.get("abuseipdb"):
        scores.append((ab["abuse_confidence_score"], 0.4))
    if not scores:
        return 50
    return round(sum(s * w for s, w in scores) / sum(w for _, w in scores))
```

---

## 5. Integration Implementations

### 5.1 VirusTotal (Core — IOC enrichment for all org plans)

```python
@register_plugin
class VirusTotalPlugin:
    name = "virustotal"
    category = "ti"
    is_premium = False   # Basic enrichment is free for all

    config_schema = {
        "api_key": { "type": "password", "label": "API Key", "required": True }
    }

    async def enrich_ioc(self, ioc: IOC, config: dict) -> dict:
        endpoint_map = {
            "domain": f"https://www.virustotal.com/api/v3/domains/{ioc.value}",
            "ip":     f"https://www.virustotal.com/api/v3/ip_addresses/{ioc.value}",
            "url":    f"https://www.virustotal.com/api/v3/urls/{b64url(ioc.value)}",
            "hash":   f"https://www.virustotal.com/api/v3/files/{ioc.value}",
        }
        # Respects 4 req/min free tier via Redis rate limiter
```

### 5.2 AbuseIPDB (Core — IP enrichment only)

```python
@register_plugin
class AbuseIPDBPlugin:
    name = "abuseipdb"
    category = "ti"
    is_premium = False

    async def enrich_ioc(self, ioc: IOC, config: dict) -> dict:
        if ioc.ioc_type != "ip":
            return {}
        # GET https://api.abuseipdb.com/api/v2/check?ipAddress={ioc.value}
```

### 5.3 Microsoft Sentinel (Premium)

```python
@register_plugin
class SentinelPlugin:
    name = "sentinel"
    display_name = "Microsoft Sentinel"
    category = "siem"
    is_premium = True

    config_schema = {
        "workspace_id":  { "type": "string",   "label": "Workspace ID",  "required": True },
        "tenant_id":     { "type": "string",   "label": "Tenant ID",     "required": True },
        "client_id":     { "type": "string",   "label": "App Client ID", "required": True },
        "client_secret": { "type": "password", "label": "Client Secret", "required": True },
    }

    async def pull_alerts(self, incident_id: str, config: dict) -> list[dict]:
        """
        Executes a KQL query against the Sentinel workspace.
        Analyst specifies time range and optional query in the UI.
        Results are returned as structured timeline entry candidates.
        Uses azure-monitor-query SDK.
        """

    async def run_query(self, kql: str, config: dict) -> list[dict]:
        """Free-form KQL execution. Analyst pastes KQL, results import as entries."""
```

UI: "Pull from Sentinel" button in Timeline page. Opens a dialog: date range + optional KQL filter. Results shown in a preview table — analyst selects which results to import as timeline entries. Imported entries are tagged `source: sentinel`.

### 5.4 CrowdStrike Falcon (Premium)

```python
@register_plugin
class CrowdStrikePlugin:
    name = "crowdstrike"
    category = "edr"
    is_premium = True

    async def pull_detections(self, incident_id: str, config: dict) -> list[dict]:
        """Fetch detections via FalconPy SDK. Returns timeline entry candidates."""

    async def contain_host(self, device_id: str, config: dict) -> bool:
        """Initiate host containment directly from IR workspace."""
        # Requires confirmation modal in UI — destructive action
```

### 5.5 Azure AD / Entra (Premium)

```python
@register_plugin
class AzureADPlugin:
    name = "azuread"
    display_name = "Azure AD / Entra ID"
    category = "iam"
    is_premium = True

    async def get_sign_in_logs(self, user_upn: str, config: dict) -> list[dict]: ...
    async def revoke_sessions(self, user_id: str, config: dict) -> bool: ...
    async def reset_password(self, user_id: str, config: dict) -> str: ...
```

Revoke + reset actions appear as buttons within relevant timeline entries. All require a confirmation modal. All are logged as audit events with HIGH visibility.

### 5.6 Slack / Microsoft Teams (Core — Webhook)

```python
@register_plugin
class SlackPlugin:
    name = "slack"
    category = "comms"
    is_premium = False

    config_schema = {
        "webhook_url": { "type": "string", "label": "Incoming Webhook URL", "required": True }
    }

    async def send_notification(self, event: str, payload: dict, config: dict):
        """
        Events and messages:
        incident.created     → "🔴 New SEV-1 incident opened: {title} [{ref}]"
        timeline.entry.added → "📋 {analyst} added [{type}] entry to {ref}"
        task.completed       → "✅ Task completed: {task_title} — {ref}"
        report.ready         → "📄 {type} report ready for {ref} — {url}"
        sync.complete        → "📤 SharePoint updated for {ref} — {url}"
        ioc.added            → "🎯 New IOC added to {ref}: {type} {value}"
        """
```

Teams uses the same structure with a different payload format — a `TeamsPlugin` shares 90% of the logic.

### 5.7 Proofpoint / Microsoft Defender for Email (Premium)

```python
@register_plugin
class ProofpointPlugin:
    name = "proofpoint"
    category = "email"
    is_premium = True

    async def search_messages(self, sender: str, recipient: str, subject: str, config: dict) -> list: ...
    async def get_message_trace(self, message_id: str, config: dict) -> dict: ...
```

### 5.8 Shodan (Premium — IOC enrichment only)

```python
@register_plugin
class ShodanPlugin:
    name = "shodan"
    category = "ti"
    is_premium = True

    async def enrich_ioc(self, ioc: IOC, config: dict) -> dict:
        if ioc.ioc_type not in ["ip", "domain"]:
            return {}
        # shodan.host(ip) or shodan.search("hostname:{domain}")
```

---

## 6. Inbound Webhook Integration Guide (Published as Documentation)

The inbound webhook API (`POST /api/v1/external/incidents`) is built in Phase 1 but this phase produces the integration guides for external teams. These ship as documentation pages and are linked from the Integrations settings page.

### 6.1 ServiceDesk Plus (ManageEngine SDP)

SDP supports custom buttons and automation workflows. Configuration:
1. Create an API key in IRDoc: Settings → API Keys → New → name: "SDP Integration", scope: `incidents:create`
2. In SDP: Automations → Custom Triggers → On "Security Incident" category → HTTP POST action
3. Payload mapping (SDP variables → IRDoc fields):
   ```
   title        = ${SUBJECT}
   external_ref = ${REQUESTID}
   external_source = "servicedesk_plus"
   external_url = https://sdp.company.com/requests/${REQUESTID}
   reported_by  = ${REQUESTER_EMAIL}
   severity     = "sev2"
   template     = "phishing"   (or map from SDP category)
   ```
4. The IRDoc workspace URL returned in the response can be stored as a SDP custom field

### 6.2 ManageEngine ServiceDesk (Desktop Central / ITSM)

Same pattern as SDP — ME supports HTTP actions in automation rules.

### 6.3 Jira (Service Management or Software)

Two options:
- **Jira Automation:** "When issue created in Security project → POST to IRDoc webhook"
- **Jira Webhook:** Configure outgoing webhook on issue creation, filtered by project/label

### 6.4 Any Other Tool

Any tool that can make an HTTP POST with JSON headers and a bearer token can create IRDoc cases. The API is intentionally simple — no special SDKs, no OAuth dance required.

---

## 7. Investigation Graph

### 7.1 Purpose

Answers the question: "How do all these entities relate to each other in this attack?" For a phishing case, this might show: email sender → phishing URL → credential harvester domain → IP address → affected user accounts.

### 7.2 Entities and Relationships

**Node types:**
- 👤 User (from `incident.affected_users`, mentioned in timeline text)
- 💻 Host/Device (extracted from timeline entries via regex)
- 📧 Email address IOC
- 🌐 Domain IOC
- 🔢 IP address IOC
- 🔗 URL IOC
- 🔢 File hash IOC
- 🔔 Alert (entries sourced from Sentinel/CrowdStrike)
- 📎 Evidence file (attachments)
- 📌 Key event (pinned timeline entries)

**Relationship types (auto-extracted):**
- IOC mentioned in timeline entry → `mentioned in`
- Two IOCs sharing same VirusTotal cluster → `related to`
- Same IP in multiple entries → `observed in`
- IOC to IOC from enrichment data (VT relations API) → `resolves to`, `communicates with`
- Manual drag-to-link by analyst

### 7.3 Tech: React Flow

```tsx
// components/graph/InvestigationGraph.tsx
import ReactFlow, { Background, Controls, MiniMap } from '@xyflow/react';

const nodeTypes = {
  user:       UserNode,
  ioc_ip:     IPNode,
  ioc_domain: DomainNode,
  ioc_email:  EmailNode,
  ioc_url:    URLNode,
  ioc_hash:   HashNode,
  event:      EventNode,
  evidence:   EvidenceNode,
};
```

Node colors mirror the existing color system: red for malicious IOCs, yellow for suspicious, green for clean, blue for events, grey for evidence. This keeps visual consistency with the rest of the UI.

### 7.4 Graph API

```python
# GET /api/v1/incidents/{id}/graph
{
  "nodes": [
    {
      "id": "ioc-{uuid}",
      "type": "ioc_domain",
      "position": { "x": 100, "y": 200 },   # computed by dagre layout
      "data": {
        "label": "support-secure-verify.ru",
        "status": "active",
        "confidence": 95,
        "ioc_type": "domain"
      }
    }
  ],
  "edges": [
    {
      "id": "e1",
      "source": "ioc-{uuid}",
      "target": "entry-{uuid}",
      "label": "mentioned in",
      "animated": true
    }
  ]
}
```

Layout computed server-side using `networkx` (Python) with a hierarchical layout algorithm. Client-side React Flow renders and allows pan/zoom/re-layout.

### 7.5 Graph Features

- Auto-layout on load (dagre/hierarchical)
- Zoom, pan, minimap
- Click node → side panel with full entity details
- Export as SVG/PNG (one click)
- Analyst can drag entities together to manually create relationships
- "Highlight path" — select two nodes, graph highlights shortest connection path

---

## 8. Integration Settings UI (Fully Functional)

```
┌───────────────────────────────────────────────────────────────┐
│  🔷 Microsoft Sentinel               ● Connected              │
│  Pull alerts and run KQL queries                             │
│                                                               │
│  [Configure]  [Test Connection ✓]  [●  Enabled]              │
│  Last synced: 5 min ago                                       │
└───────────────────────────────────────────────────────────────┘
```

**Configure** opens a modal with the integration's `config_schema` rendered as a form. This is fully dynamic — no custom form code per integration. The schema defines field types (string, password, select), labels, and validation rules. The frontend renders them generically.

**Test Connection** calls `POST /api/v1/integrations/{plugin_name}/test` and shows green ✓ or red ✗ with the error message.

---

## 9. New API Endpoints (Phase 4)

### Integrations

| Method | Path | Description |
|---|---|---|
| GET    | `/integrations` | List all plugins + org config status |
| PUT    | `/integrations/{name}` | Save configuration (encrypted) |
| POST   | `/integrations/{name}/test` | Test connection |
| POST   | `/integrations/{name}/toggle` | Enable/disable |
| POST   | `/integrations/sentinel/pull` | Pull alerts (modal with KQL + date range) |
| POST   | `/integrations/crowdstrike/contain` | Contain a host (confirmation required) |
| POST   | `/integrations/azuread/revoke-sessions` | Revoke user sessions |
| POST   | `/integrations/azuread/reset-password` | Reset user password |
| POST   | `/iocs/{ioc_id}/enrich` | Manually trigger re-enrichment |

### Graph

| Method | Path | Description |
|---|---|---|
| GET    | `/incidents/{id}/graph` | Full graph (nodes + edges) |
| POST   | `/incidents/{id}/graph/edges` | Manually add relationship |
| DELETE | `/incidents/{id}/graph/edges/{edge_id}` | Remove relationship |

### AI — IOC Enrichment Narrative

| Method | Path | Description |
|---|---|---|
| POST   | `/iocs/{id}/ai/narrative` | Generate plain-English enrichment description (premium) |

---

## 10. Security Considerations for Integrations

- All integration credentials Fernet-encrypted in `org_integrations.config`
- Config field values never returned via API — only status (last_tested, is_enabled, last_error)
- Every integration action logged to audit_log
- **Destructive actions** (CrowdStrike contain, Azure AD revoke/reset) require:
  1. Confirmation modal with explicit text ("You are about to revoke all sessions for john.doe@company.com")
  2. Senior Analyst or Admin role minimum
  3. Rate limit: max 10 destructive actions per hour per org
- Integration API calls execute in Celery worker — never in the request thread (no timeout risk)
- SharePoint credentials never leave the worker — never sent to frontend

---

## 11. Deliverables Checklist

### Architect
- [ ] Plugin registry pattern reviewed
- [ ] SharePoint Graph API app registration requirements documented for deployers
- [ ] Redis keyspace notifications configuration confirmed (notify-keyspace-events Ex)
- [ ] Networkx graph layout validated for 20+ node graphs

### Developer (Backend)
- [ ] `org_integrations` table migration
- [ ] Plugin base class + registry
- [ ] VirusTotal plugin (enrichment, all applicable IOC types)
- [ ] AbuseIPDB plugin (IP enrichment)
- [ ] Shodan plugin (premium)
- [ ] Sentinel plugin (pull alerts, KQL query — premium)
- [ ] CrowdStrike plugin (detections, contain — premium)
- [ ] Azure AD plugin (sign-in logs, revoke, reset — premium)
- [ ] Slack plugin (notifications — core)
- [ ] Teams plugin (notifications — core)
- [ ] Proofpoint plugin (email trace — premium)
- [ ] SharePoint plugin (push_report — premium)
- [ ] `enrich_ioc` Celery task (multi-provider, confidence recalculation)
- [ ] `sync_to_sharepoint` Celery task (full implementation with retry)
- [ ] Redis keyspace notification subscription for debounce expiry
- [ ] Graph endpoint (nodes + edges from DB)
- [ ] Integration CRUD + test + toggle endpoints
- [ ] Manual trigger endpoint for sync policies
- [ ] `ai_ioc_narrative` task (premium)
- [ ] Credential encryption/decryption utility

### Developer (Frontend)
- [ ] Integration cards fully functional (configure, test, toggle, status)
- [ ] Schema-driven integration config modal
- [ ] IOC table enrichment display (VT badge, AbuseIPDB score, Shodan ports)
- [ ] "Enriching..." loading state per IOC row
- [ ] AI narrative display in IOC row expand
- [ ] Investigation Graph page (new nav item)
- [ ] React Flow with custom node types
- [ ] Graph side panel (entity detail on click)
- [ ] Graph export (SVG/PNG)
- [ ] Sentinel "Pull Alerts" button + preview modal in Timeline
- [ ] Azure AD action buttons in summary/timeline context
- [ ] CrowdStrike "Contain Host" button with confirmation
- [ ] SharePoint sync "Sync Now" button (triggers manual task)
- [ ] Sync policy status updates via WebSocket ("sync:complete")

### QA
- [ ] IOC enrichment: add IP → VT + AbuseIPDB results appear within 30s
- [ ] Confidence score recalculates correctly from enrichment data
- [ ] SharePoint sync: edit incident → wait 60s → document updates on SharePoint
- [ ] SharePoint sync: 5 rapid edits → only 1 upload fires (debounce working)
- [ ] Integration test connection shows ✓ / ✗ correctly
- [ ] CrowdStrike contain shows confirmation modal, logs to audit
- [ ] Azure AD revoke sessions logs to audit with "high_risk" flag
- [ ] Graph renders correctly for a realistic incident with 10+ IOCs
- [ ] Slack notification fires on timeline entry add
- [ ] All integration credentials encrypted in DB (confirm raw values absent)

---

*Next: Phase 5 — Multi-Tenancy, User Management & Enterprise Features*
