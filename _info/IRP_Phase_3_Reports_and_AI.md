# IRP Phase 3 — Report Template Builder & Report Generation

> **Status:** Planning  
> **Depends on:** Phase 2 complete (full React app running against real API)  
> **Estimated effort:** 4–5 weeks  
> **Goal:** Analysts can build their own report templates by composing field blocks visually, assign templates to destinations (management, legal, analyst), and generate professional reports in one click. Reports generate asynchronously. AI-generated summaries are the first premium feature. SharePoint auto-sync is wired at the policy level (sync delivery implemented in Phase 4).

---

## 1. Objectives

By end of Phase 3:
- **Core (free):** Markdown + HTML export using the default Technical Report template
- **Premium:** Visual drag-and-drop report template builder, multi-destination templates, PDF export (WeasyPrint), DOCX export (python-docx), AI-assisted executive summaries and recommendations
- Analysts can create unlimited named report templates, each with a different selection and ordering of case fields
- Three system templates ship by default (Management Brief, Technical Report, Legal/Compliance) — clonable and customisable by orgs
- Report generation is async (Celery) — WebSocket notifies when ready
- All generated reports stored and downloadable at any time
- Sync policy table exists and is populated here — delivery to SharePoint implemented in Phase 4

---

## 2. The Report Template Architecture (Detailed)

### 2.1 Philosophy

Reports are not hardcoded. They are **user-composed schemas** — ordered arrays of block definitions stored as JSONB in `report_templates.schema_json`. The rendering engine reads the schema and assembles the report from Jinja2 partials. A new block type requires only a new partial and a renderer entry. No migrations, no frontend rebuild.

### 2.2 Block Types

| Block Type | Description | Config Options |
|---|---|---|
| `cover` | Title page with incident metadata | fields to show, classification watermark |
| `section` | A titled text section from a single field | label, field path, editable |
| `stat_row` | A horizontal row of metric cards | which stats (severity, duration, affected_users, status, ioc_count) |
| `timeline` | Chronological list of entries | filter by type, show/hide attachments, max entries |
| `ioc_table` | Table of indicators | filter by status/type, columns to show |
| `task_list` | Checklist of response tasks | filter by phase, show completed/skipped |
| `evidence_register` | Table of uploaded files with hashes | show sha256, show uploader |
| `text_block` | Free-text or AI-generated narrative | label, field path or AI source |
| `divider` | Visual separator | — |
| `page_break` | Forces page break in PDF | — |
| `header` | Section heading text | text content |
| `tag_list` | Renders array fields as chips | field path, label |

### 2.3 Field Paths

Every block that binds to case data uses a **dot-notation field path** that the renderer resolves against the ReportPayload:

| Field Path | Resolves To |
|---|---|
| `incident.title` | Incident title |
| `incident.ref` | INC-2026-0315 |
| `incident.severity` | SEV-1 (Critical) |
| `incident.status` | Open / Contained / Closed |
| `incident.duration` | "4 hours 32 minutes" |
| `incident.affected_users` | Integer |
| `incident.executive_summary` | Free-text field |
| `incident.attack_vector` | Array of tags |
| `incident.opened_at` | Formatted datetime |
| `incident.external_refs` | List of external ticket references |
| `timeline.all` | All entries |
| `timeline.by_type.detection` | Detection entries only |
| `timeline.by_type.containment` | Containment entries only |
| `iocs.all` | All IOCs |
| `iocs.active` | Active IOCs only |
| `iocs.blocked` | Blocked IOCs |
| `tasks.all` | All tasks |
| `tasks.by_phase.{n}` | Tasks in a specific phase |
| `attachments.all` | Evidence register |
| `analyst.full_name` | Report requester name |
| `generated_at` | Report generation timestamp |
| `ai.executive_summary` | AI-generated summary (premium) |
| `ai.recommendations` | AI-generated recommendations (premium) |

### 2.4 Example Template Schemas

**Management Brief** (ships as system template):
```json
[
  { "type": "cover",       "fields": ["incident.title", "incident.ref", "incident.severity", "incident.status", "generated_at"], "watermark": "CONFIDENTIAL" },
  { "type": "stat_row",    "stats": ["severity", "status", "duration", "affected_users"] },
  { "type": "section",     "label": "Executive Summary",     "field": "incident.executive_summary" },
  { "type": "text_block",  "label": "AI Narrative",          "field": "ai.executive_summary",      "premium": true },
  { "type": "section",     "label": "Attack Overview",       "field": "incident.attack_vector" },
  { "type": "ioc_table",   "filter": "status=active",        "columns": ["type", "value", "status"] },
  { "type": "timeline",    "filter": "type=containment",     "show_attachments": false, "label": "Containment Actions" },
  { "type": "task_list",   "filter": "phase=3",              "label": "Containment Tasks" },
  { "type": "text_block",  "label": "Recommendations",       "field": "ai.recommendations",        "premium": true }
]
```

**Technical Report** (ships as system template):
```json
[
  { "type": "cover",            "fields": ["incident.title", "incident.ref", "incident.severity", "analyst.full_name", "generated_at"] },
  { "type": "stat_row",         "stats": ["severity", "status", "duration", "affected_users", "ioc_count", "entry_count"] },
  { "type": "section",          "label": "Executive Summary",     "field": "incident.executive_summary" },
  { "type": "section",          "label": "Attack Vector",         "field": "incident.attack_vector" },
  { "type": "timeline",         "filter": "all",                  "show_attachments": true,  "label": "Full Incident Timeline" },
  { "type": "ioc_table",        "filter": "all",                  "columns": ["type", "value", "description", "status", "confidence", "first_seen"] },
  { "type": "evidence_register","label": "Evidence Register" },
  { "type": "task_list",        "filter": "all",                  "show_completed": true,    "label": "Full Response Checklist" },
  { "type": "section",          "label": "Analyst Notes",         "field": "incident.metadata.notes" }
]
```

**Legal / Compliance** (ships as system template):
```json
[
  { "type": "cover",     "fields": ["incident.title", "incident.ref", "incident.opened_at", "generated_at"], "watermark": "RESTRICTED" },
  { "type": "section",   "label": "Incident Description",        "field": "incident.executive_summary" },
  { "type": "stat_row",  "stats": ["severity", "opened_at", "contained_at", "closed_at"] },
  { "type": "section",   "label": "Data / Systems Affected",     "field": "incident.metadata.affected_data" },
  { "type": "timeline",  "filter": "type=detection",             "label": "Detection Events" },
  { "type": "timeline",  "filter": "type=containment",           "label": "Response Actions" },
  { "type": "ioc_table", "filter": "all",                        "columns": ["type", "value", "status", "first_seen"] },
  { "type": "section",   "label": "Root Cause",                  "field": "incident.metadata.root_cause" },
  { "type": "section",   "label": "Regulatory Obligations",      "field": "incident.metadata.regulatory_notes" },
  { "type": "section",   "label": "Preventive Actions",          "field": "incident.metadata.preventive_actions" }
]
```

---

## 3. Report Template Builder UI

### 3.1 Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Report Templates          [+ New Template]   [System Templates ▾]      │
│─────────────────────────────────────────────────────────────────────────│
│  Management Brief  [Edit]  [Clone]  [Delete]    destination: management  │
│  Technical Report  [Edit]  [Clone]              destination: analyst     │
│  Legal/Compliance  [Edit]  [Clone]              destination: legal       │
│  My Custom Template [Edit] [Clone]  [Delete]    destination: custom      │
└─────────────────────────────────────────────────────────────────────────┘
```

Clicking "Edit" or "+ New Template" opens the Builder:

```
┌─────────────────────────────────────────────────────┬───────────────────┐
│  Template Name: [Management Brief              ]    │  AVAILABLE BLOCKS │
│  Destination:   [Management          ▾]             │─────────────────  │
│  Classification:[CONFIDENTIAL        ▾]             │  📄 Cover Page    │
│─────────────────────────────────────────────────────│  📊 Stat Row      │
│  CANVAS (drag to reorder)                           │  📝 Section       │
│  ─────────────────────────────────────────          │  🕐 Timeline      │
│  ≡  📄  Cover Page                          [✕]     │  🎯 IOC Table     │
│  ≡  📊  Stat Row    severity · duration     [✕]     │  ✅ Task List     │
│  ≡  📝  Executive Summary   → executive_summ [✕]   │  📎 Evidence Reg. │
│  ≡  🤖  AI Narrative  [PREMIUM]              [✕]   │  📋 Text Block    │
│  ≡  🎯  IOC Table   filter: active           [✕]   │  ─────────────    │
│  ≡  🕐  Timeline    filter: containment      [✕]   │  ── Divider       │
│  ≡  ✅  Task List   phase 3                  [✕]   │  ↵  Page Break    │
│  ─────────────────────────────────────────          │  H  Header Text   │
│  [+ Add Block]                                      │                   │
│─────────────────────────────────────────────────────│                   │
│  [Preview]    [Save Template]    [Save & Generate]  │                   │
└─────────────────────────────────────────────────────┴───────────────────┘
```

**Interactions:**
- Drag blocks from the right panel onto the canvas, or click to add at the bottom
- Drag `≡` handle on canvas blocks to reorder
- Click any canvas block to expand its configuration panel (inline, below the block)
- `[✕]` removes a block
- `[Preview]` renders a live preview using the current incident's real data (in a modal or side panel)
- `[Save & Generate]` saves the template and immediately queues a report generation job

**Block configuration panels (inline expansion):**

Timeline block config:
```
Filter:  [All entries ▾]   /   [Detection ▾]   /   [Containment ▾]   /  Custom...
Label:   [Full Incident Timeline          ]
Show attachments: [●  Yes]  [○  No]
Max entries:      [  50   ] (0 = all)
```

IOC Table config:
```
Filter by status: [☑ Active]  [☑ Blocked]  [☐ Remediated]  [☐ False Positive]
Filter by type:   [☑ All]     or pick specific types
Columns:          [☑ Type]  [☑ Value]  [☑ Description]  [☑ Status]  [☐ Confidence]  [☐ First Seen]
```

---

## 4. Report Generation Flow (Backend)

```
POST /api/v1/incidents/{id}/reports
{
  "report_template_id": "uuid...",
  "format": "pdf",              -- pdf | docx | markdown | html
  "classification": "confidential"
}

→ Creates Report row (status: "pending")
→ Returns { report_id, status: "pending" }
→ Enqueues Celery task: generate_report.delay(report_id)

Frontend: polls GET /api/v1/reports/{report_id}
  OR receives WebSocket "report:ready" event

Worker: generate_report(report_id)
  1. Load Report + ReportTemplate + full incident payload
  2. Build ReportPayload dataclass
  3. If any AI blocks present and licensed: call AI service, inject results
  4. Iterate schema_json blocks → render each Jinja2 partial
  5. Assemble under base.html layout
  6. Render to requested format:
     - markdown: direct text assembly from partials
     - html: assembled HTML string
     - pdf: HTML → WeasyPrint → bytes
     - docx: ReportPayload → python-docx builder (premium)
  7. Store via StorageBackend
  8. Update Report: status="ready", storage_path, generated_at
  9. Emit WebSocket: "report:ready" { report_id }
```

### 4.1 ReportPayload Dataclass

```python
@dataclass
class ReportPayload:
    # Raw data
    incident: Incident
    entries: list[TimelineEntry]         # sorted by occurred_at ASC
    iocs: list[IOC]
    tasks: list[Task]
    attachments: list[Attachment]
    analyst: User
    generated_at: datetime

    # Resolved field paths (cached)
    duration_str: str                    # "4 hours 32 minutes"
    entry_count: int
    ioc_count: int
    task_completion_pct: int
    tasks_by_phase: dict[str, list[Task]]
    entries_by_type: dict[str, list[TimelineEntry]]
    iocs_by_status: dict[str, list[IOC]]
    iocs_by_type: dict[str, list[IOC]]
    severity_label: str                  # "SEV-1 (Critical)"
    external_refs: list[IncidentExternalRef]

    # AI-generated (premium, populated before rendering if blocks require it)
    ai_executive_summary: str | None = None
    ai_recommendations: str | None = None
```

### 4.2 Rendering Engine

```python
# app/services/report_renderer/engine.py

class ReportRenderer:
    def __init__(self, template_env: jinja2.Environment):
        self.env = template_env

    def render(self, schema: list[dict], payload: ReportPayload, format: str) -> bytes:
        # Render each block
        rendered_blocks = []
        for block in schema:
            partial = self.env.get_template(f"reports/blocks/{block['type']}.html")
            rendered_blocks.append(partial.render(block=block, p=payload))

        # Assemble in base layout
        base = self.env.get_template("reports/base.html")
        html = base.render(
            blocks=rendered_blocks,
            incident=payload.incident,
            classification=payload.incident.metadata.get("classification", "CONFIDENTIAL"),
            generated_at=payload.generated_at,
            analyst=payload.analyst
        )

        if format == "html":
            return html.encode()
        elif format == "markdown":
            return html_to_markdown(html).encode()
        elif format == "pdf":
            from weasyprint import HTML
            return HTML(string=html, base_url=STATIC_BASE_URL).write_pdf()
        elif format == "docx":
            check_feature("report_docx_export")
            return DocxBuilder().build(payload, schema)
```

---

## 5. AI Assistance (Premium)

### 5.1 Provider-Agnostic Architecture

```python
# app/services/ai_service.py

class AIProvider(Protocol):
    async def complete(self, system: str, user: str, max_tokens: int) -> str: ...

class AnthropicProvider:
    """Uses claude-sonnet-4-6 by default."""
    async def complete(self, system, user, max_tokens):
        response = await anthropic.messages.create(
            model=settings.AI_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": user}],
            system=system
        )
        return response.content[0].text

class OpenAIProvider:
    async def complete(self, system, user, max_tokens): ...

class OllamaProvider:
    """Local LLM — for air-gapped deployments. Supports llama3, mistral, etc."""
    async def complete(self, system, user, max_tokens): ...

def get_ai_provider() -> AIProvider:
    backend = settings.AI_BACKEND  # anthropic | openai | ollama
    return { "anthropic": AnthropicProvider, "openai": OpenAIProvider, "ollama": OllamaProvider }[backend]()
```

This is critical for organizations in air-gapped environments — they can run Ollama locally and get full AI capabilities without sending case data to cloud APIs.

### 5.2 AI Executive Summary

```python
@celery_app.task
async def generate_ai_summary(incident_id: str) -> str:
    check_feature("ai_summary")

    payload = build_report_payload(incident_id)

    system = """You are a senior incident response analyst writing a concise executive
    summary for a non-technical management audience. Focus on: what happened, what was
    affected, what was done, and current status. Write in 3-5 clear sentences.
    Use plain language. Past tense for resolved items."""

    user = f"""
    Incident: {payload.incident.title}
    Severity: {payload.severity_label}
    Duration: {payload.duration_str}
    Affected users: {payload.incident.affected_users}

    Timeline summary (first 20 events):
    {chr(10).join([f"[{e.entry_type.upper()}] {e.description[:200]}" for e in payload.entries[:20]])}

    IOCs: {payload.ioc_count} total ({len(payload.iocs_by_status.get('active', []))} active)
    Task completion: {payload.task_completion_pct}%
    """

    return await ai_service.complete(system, user, max_tokens=400)
```

### 5.3 AI Recommendations

```python
@celery_app.task
async def generate_ai_recommendations(incident_id: str) -> str:
    check_feature("ai_summary")

    payload = build_report_payload(incident_id)

    system = """You are a senior incident response analyst writing post-incident
    recommendations. Provide 3-5 specific, actionable technical recommendations
    to prevent recurrence. Be concrete — reference the specific attack vector."""

    # ... similar user prompt ...
    return await ai_service.complete(system, user, max_tokens=600)
```

### 5.4 AI Features Map

| Feature | Trigger | Output |
|---|---|---|
| Executive summary | Report generation (if template has `ai.executive_summary` block) | 3-5 sentence narrative |
| Recommendations | Report generation (if template has `ai.recommendations` block) | 3-5 actionable items |
| IOC enrichment narrative | After VT/AbuseIPDB enrichment (Phase 4) | 2-sentence plain-English IOC description |
| Timeline cleanup | Manual button on timeline view | Suggested reordering or merges |
| Natural language search | Search bar | SQL-translated query |

---

## 6. Sync Policy (Wired Here, Delivered in Phase 4)

The `sync_policies` table was created in Phase 1. In Phase 3, the UI for **creating and managing sync policies** is built. The actual SharePoint upload worker is implemented in Phase 4.

### 6.1 Sync Policy UI (in incident workspace — Reports section)

```
┌─────────────────────────────────────────────────────────┐
│  AUTO-SYNC POLICIES                      [+ Add Policy]  │
│─────────────────────────────────────────────────────────│
│  📤 SharePoint               ● Active                   │
│     Template: Management Brief                          │
│     Trigger: On change (60s debounce)                   │
│     Last synced: 3 minutes ago  ✓ Success               │
│     SharePoint path: /sites/SOC/IR Reports/INC-0315.pdf │
│     [Configure]  [Sync Now]  [Disable]                  │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Add Sync Policy Modal

```
Destination:        [SharePoint          ▾]      [PREMIUM]
Report Template:    [Management Brief    ▾]
Trigger:            [On every change     ▾]
Debounce (seconds): [60                  ]
SharePoint Site:    [https://company.sharepoint.com/sites/SOC]
Library:            [IR Reports                              ]
Filename pattern:   [{incident_ref} - {incident_title}.pdf   ]
```

### 6.3 Sync Policy API

| Method | Path | Description |
|---|---|---|
| GET    | `/incidents/{id}/sync-policies` | List policies for incident |
| POST   | `/incidents/{id}/sync-policies` | Create policy (premium gate) |
| PUT    | `/incidents/{id}/sync-policies/{pid}` | Update policy |
| DELETE | `/incidents/{id}/sync-policies/{pid}` | Delete |
| POST   | `/incidents/{id}/sync-policies/{pid}/trigger` | Manual sync now |

---

## 7. Report Page UI (Now Fully Functional)

The Reports page replaces the Phase 2 shell with a fully functional interface.

### 7.1 Layout

```
REPORTS                                          [Manage Templates]

Generate a Report:
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ 📊           │  │ 🔬           │  │ ⚖️           │
│ Management   │  │ Technical    │  │ Legal/        │
│ Brief        │  │ Report       │  │ Compliance    │
│ [Generate]   │  │ [Generate]   │  │ [Generate]    │
└──────────────┘  └──────────────┘  └──────────────┘
┌──────────────┐  ┌──────────────┐
│ ✏️           │  │ +            │
│ My Custom    │  │ New Template │
│ Template     │  │              │
│ [Generate]   │  │              │
└──────────────┘  └──────────────┘

Auto-Sync Policies:
  [section showing sync_policies, wired to SharePoint in Phase 4]

Generated Reports:
┌──────────────────────────────────────────────────────────────────┐
│ Type               Format  Generated        By         Actions   │
│ Management Brief   PDF     2026-03-15 11:30 John Doe  ⬇ Delete  │
│ Technical Report   DOCX    2026-03-15 10:15 John Doe  ⬇ Delete  │
└──────────────────────────────────────────────────────────────────┘
```

### 7.2 Generation Modal

When clicking "Generate" on any report card:

```
Generate: Management Brief

Format:         [PDF ▾]           [PREMIUM for PDF/DOCX]
Classification: [CONFIDENTIAL ▾]
Include AI:     [● Yes  ○ No]     [PREMIUM]

[Cancel]                          [Generate Report]
```

After clicking Generate:
- Button: "Generating..." with spinner
- WebSocket "report:ready" fires when done
- Row appears in Generated Reports table: "✅ Ready — ⬇ Download"

---

## 8. New API Endpoints (Phase 3)

### Report Templates

| Method | Path | Description |
|---|---|---|
| GET    | `/report-templates` | List system + org templates |
| POST   | `/report-templates` | Create custom template (premium) |
| GET    | `/report-templates/{id}` | Get template with schema |
| PUT    | `/report-templates/{id}` | Update schema (premium) |
| DELETE | `/report-templates/{id}` | Delete (org templates only) |
| POST   | `/report-templates/{id}/clone` | Clone system template to customize |
| GET    | `/report-templates/{id}/preview` | Preview rendered HTML for current incident |

### Reports

| Method | Path | Description |
|---|---|---|
| POST   | `/incidents/{id}/reports` | Enqueue generation |
| GET    | `/incidents/{id}/reports` | List generated reports |
| GET    | `/reports/{id}` | Report status + metadata |
| GET    | `/reports/{id}/download` | Stream file |
| DELETE | `/reports/{id}` | Delete report |

### AI

| Method | Path | Description |
|---|---|---|
| POST   | `/incidents/{id}/ai/summary` | Generate executive summary (premium) |
| POST   | `/incidents/{id}/ai/recommendations` | Generate recommendations (premium) |

### Sync Policies

| Method | Path | Description |
|---|---|---|
| GET    | `/incidents/{id}/sync-policies` | List policies |
| POST   | `/incidents/{id}/sync-policies` | Create (premium) |
| PUT    | `/incidents/{id}/sync-policies/{pid}` | Update |
| DELETE | `/incidents/{id}/sync-policies/{pid}` | Delete |
| POST   | `/incidents/{id}/sync-policies/{pid}/trigger` | Manual trigger (stub — functional in Phase 4) |

---

## 9. Deliverables Checklist

### Architect
- [ ] Report block schema format reviewed (all block types, all field paths)
- [ ] WeasyPrint validated — sample PDF output reviewed
- [ ] AI provider adapter pattern reviewed
- [ ] Sync policy table reviewed (aligns with Phase 4 worker needs)

### Developer (Backend)
- [ ] `generate_report` Celery task (full implementation)
- [ ] `ReportRenderer` engine (block iteration + Jinja2 partial assembly)
- [ ] Jinja2 partials for all block types
- [ ] Base HTML layout + print CSS (WeasyPrint-compatible)
- [ ] WeasyPrint PDF renderer
- [ ] Markdown export
- [ ] python-docx builder (premium, basic implementation)
- [ ] AI service with provider adapters (Anthropic, OpenAI, Ollama stubs)
- [ ] `generate_ai_summary` task
- [ ] `generate_ai_recommendations` task
- [ ] Report template CRUD endpoints + clone
- [ ] Report endpoints (enqueue, list, status, download, delete)
- [ ] AI endpoints
- [ ] Sync policy CRUD endpoints (manual trigger stub)
- [ ] Feature flag checks on all premium endpoints

### Developer (Frontend)
- [ ] Report Template Builder page (list view)
- [ ] Builder canvas (drag/drop via @dnd-kit)
- [ ] Block library panel (right side)
- [ ] Per-block configuration panels (inline expansion)
- [ ] Template preview modal (renders real incident data)
- [ ] Report page (fully functional — generation cards)
- [ ] Generation modal (format, classification, AI toggle)
- [ ] Loading state during generation (WebSocket driven)
- [ ] Generated reports history table + download
- [ ] Sync policy section in Reports page (UI + CRUD, trigger non-functional until Phase 4)
- [ ] PremiumGate on builder, PDF/DOCX format options, AI toggle

### QA
- [ ] Build a custom template with 5+ blocks — generates valid PDF
- [ ] Clone system template, modify, generate — output reflects changes
- [ ] Markdown export opens cleanly in a text editor
- [ ] DOCX opens correctly in Word
- [ ] AI summary generates coherent 3-5 sentences
- [ ] AI recommendations are specific and relevant to the incident
- [ ] Premium gate shows correctly for core users on builder, PDF, DOCX
- [ ] Report generation failure surfaces error in UI (not silent)
- [ ] Sync policy can be created, configured, and deleted (trigger stub returns 202)

### Product Owner
- [ ] Build a "Management Brief" template from scratch using the builder
- [ ] Generate a PDF of a realistic incident — acceptable as a real deliverable?
- [ ] Review AI summary quality on a sample incident
- [ ] Confirm system templates cover the three key destinations adequately

---

*Next: Phase 4 — Integrations, IOC Enrichment, SharePoint Delivery & Investigation Graph*
