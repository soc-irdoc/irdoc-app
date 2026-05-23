# PDF Report Template System — Design Spec

## Context

IRDoc currently generates reports in two ways:
1. **V1 (DOCX placeholders):** Users download a base DOCX with `{{PLACEHOLDER}}` markers, edit it in Word, upload it, and IRDoc replaces placeholders with incident data to produce a DOCX file.
2. **V2 (block-based HTML→PDF):** Users build template schemas via drag-and-drop, IRDoc renders them to HTML via Jinja2 then converts to PDF via WeasyPrint.

**Why this change:**
- PDF becomes the sole output format. IRDoc is the source of truth for content.
- Companies still need their branding: cover pages, logo in headers, company fonts, back matter.
- The block-based drag-and-drop builder is deferred to a future version.
- The DOCX placeholder system is eliminated entirely.

**Outcome:** A single unified PDF pipeline where companies upload a branded DOCX template (with a `{{IRDoc_CONTENT}}` marker page), IRDoc extracts styling and fixed pages from it, then generates a complete fixed-section incident report wrapped in the company's branding.

---

## Architecture

```
DOCX Upload
    ↓
[Template Import Pipeline]
    mammoth → HTML (body content, embedded base64 images)
    python-docx → header/footer XML → @page CSS (logo, company name)
    Split at {{IRDoc_CONTENT}} → prefix_html + suffix_html + page_css
    Store in PdfTemplate record

Report Generation Request
    ↓
[Fixed Report Generator]
    build_report_payload(incident_id)  ← existing, reused unchanged
    For each section: has_data() → render via existing Jinja2 partials or skip
    → content_html

[PDF Assembly]
    prefix_html + content_html + suffix_html
    + page_css (@page rules: logo, header/footer from template)
    → WeasyPrint.HTML(string=full_html).write_pdf() → PDF bytes

[Storage + Notification]
    StorageBackend.store(bytes, "reports/{incident_id}/{report_id}.pdf")
    WebSocket emit: report:ready
```

**Key decisions:**
- `mammoth` converts DOCX body → HTML (handles embedded images as base64)
- `python-docx` reads `word/header1.xml` / `word/footer1.xml` separately to extract logo and repeating header text → WeasyPrint `@page` CSS rules
- Single WeasyPrint render pass — no PDF stitching, no LibreOffice dependency
- If no template is attached, IRDoc renders a plain styled PDF (prefix/suffix empty, default @page CSS)

---

## Template Import Pipeline

```
POST /api/v1/pdf-templates  (multipart DOCX upload)
    ↓
mammoth.convert_to_html(docx_bytes)
    → full_html (body with embedded base64 images)

Split full_html at paragraph containing "{{IRDoc_CONTENT}}"
    → prefix_html  (cover pages, TOC, intro sections)
    → suffix_html  (annexes, legal disclaimers, back matter)

python-docx reads header1.xml / footer1.xml
    → extract logo image → base64 data URI
    → extract header/footer text (company name, classification line)
    → generate @page CSS:
        @page {
          margin-top: 80px;
          @top-center { content: url("data:image/png;base64,..."); }
        }

Store PdfTemplate:
    prefix_html, suffix_html, page_css, mammoth_warnings
    original_docx_path (kept for re-processing if needed)
```

**Error handling at import time:**
- No `{{IRDoc_CONTENT}}` marker found → HTTP 422: `"Template must contain a paragraph with exactly {{IRDoc_CONTENT}}"`
- mammoth conversion warnings → stored in `PdfTemplate.mammoth_warnings`, surfaced in UI
- No header/footer in DOCX → `page_css` is empty string, content pages use plain margins

---

## Fixed Report Sections

IRDoc always generates a complete report. Sections auto-hide when no data exists.

| Order | Section | `has_data()` | Jinja2 partial |
|---|---|---|---|
| 1 | Cover | always shown | `blocks/cover.html` |
| 2 | Executive Summary | any summary field non-empty | `blocks/section.html` |
| 3 | Key Statistics | always shown | `blocks/stat_row.html` |
| 4 | Timeline | `len(payload.timeline) > 0` | `blocks/timeline.html` |
| 5 | IOC Table | `len(payload.iocs) > 0` | `blocks/ioc_table.html` |
| 6 | Response Tasks | `len(payload.tasks) > 0` | `blocks/task_list.html` |
| 7 | Evidence Register | `len(payload.attachments) > 0` | `blocks/evidence_register.html` |
| 8 | AI Narrative | `payload.is_ai_assisted and payload.narrative` | `blocks/text_block.html` |

Existing Jinja2 partials in `backend/templates/reports/blocks/` are reused as-is.
Only the orchestration layer in `engine.py` changes (block schema iteration → fixed section renderer).

---

## Data Model Changes

### New: `PdfTemplate` (replaces `DocxTemplate`)

```python
class PdfTemplate(Base):
    id                  UUID, PK
    org_id              UUID, FK
    name                str
    is_default          bool
    original_docx_path  str       # kept for re-processing
    prefix_html         text      # pages before {{IRDoc_CONTENT}}
    suffix_html         text      # pages after {{IRDoc_CONTENT}}
    page_css            text      # @page rules with logo, header/footer
    mammoth_warnings    JSON      # surfaced in UI
    file_size           int
    created_by          UUID, FK
    created_at          datetime
    updated_at          datetime
```

### Modified: `Report`

```python
# Remove:
- report_template_id   # was block-based template reference
- format               # was html/pdf/docx/md — now always pdf

# Add:
+ pdf_template_id      UUID, nullable FK → PdfTemplate

# Unchanged:
id, incident_id, report_type, destination, classification,
generated_by, storage_path, is_ai_assisted, status,
error_message, generated_at, created_at
```

### Removed: `DocxTemplate`

Model dropped. DB migration deletes table. Existing `Report` records with
`report_template_id` set get it nulled out. Stored DOCX template files deleted from storage.

---

## What Gets Removed

**Deleted files:**
- `backend/app/services/docx_template_service.py` — entire placeholder system
- `backend/app/services/report_renderer/docx_builder.py` — block-based DOCX builder
- `backend/app/api/v1/docx_templates.py` — replaced by `pdf_templates.py`
- `backend/app/models/docx_template.py` → replaced by `pdf_template.py`
- `backend/app/schemas/docx_template.py` → replaced by `pdf_template.py`

**Heavily modified:**
- `backend/app/services/report_renderer/engine.py` — strip DOCX/Markdown/HTML output paths, keep only PDF; replace block schema iteration with fixed section renderer
- `backend/app/workers/tasks.py` — remove `docx_template_id` logic, simplify to always produce PDF
- `backend/app/api/v1/reports.py` — remove format parameter, add `pdf_template_id`

**Frontend:**
- Remove DOCX template management UI (download base template, upload placeholder DOCX)
- Replace with PDF template management UI (upload DOCX, see mammoth warnings, set default)
- Remove format selector from report generation (always PDF)
- Remove block template schema builder references (already deferred)

---

## Critical Files

| File | Action |
|---|---|
| `backend/app/services/docx_template_service.py` | Delete |
| `backend/app/services/report_renderer/docx_builder.py` | Delete |
| `backend/app/services/report_renderer/engine.py` | Heavily modify |
| `backend/app/workers/tasks.py` | Modify |
| `backend/app/models/docx_template.py` | Replace with `pdf_template.py` |
| `backend/app/models/report.py` | Modify (remove format, add pdf_template_id) |
| `backend/app/api/v1/docx_templates.py` | Replace with `pdf_templates.py` |
| `backend/app/api/v1/reports.py` | Modify |
| `backend/app/schemas/docx_template.py` | Replace with `pdf_template.py` |
| `backend/app/schemas/report.py` | Modify |
| `backend/templates/reports/blocks/*.html` | Reuse as-is |

**New files to create:**

| File | Purpose |
|---|---|
| `backend/app/services/pdf_template_service.py` | mammoth import, @page CSS extraction, split logic |
| `backend/app/services/report_renderer/fixed_report.py` | Fixed section renderer with `has_data()` checks |
| `backend/app/models/pdf_template.py` | PdfTemplate SQLAlchemy model |
| `backend/app/schemas/pdf_template.py` | PdfTemplate Pydantic schemas |
| `backend/app/api/v1/pdf_templates.py` | Upload/manage PDF templates |
| `backend/alembic/versions/xxxx_pdf_template.py` | DB migration |

**New dependency:**
- `mammoth` — DOCX → HTML conversion (lightweight, no LibreOffice needed)

---

## Verification

**Template import:**
1. Upload DOCX with `{{IRDoc_CONTENT}}` marker → `PdfTemplate` record created with non-empty `prefix_html`, `suffix_html`, `page_css`
2. Upload DOCX without marker → API returns 422 with clear error message
3. mammoth warnings stored on record and returned in API response

**Report generation:**
1. Generate report with no template → PDF downloads, all sections present, no cover/back pages
2. Generate report with template → PDF has company cover before content, back matter after, logo in header throughout content pages
3. Incident with no IOCs → IOC Table section absent from PDF
4. Incident with no timeline entries → Timeline section absent
5. Incident with AI narrative enabled → AI section appears; without it → absent

**Regression:**
6. SharePoint sync still produces valid PDF
7. Existing `Report` records with null `pdf_template_id` still download correctly

**Migration:**
8. `DocxTemplate` table dropped, `PdfTemplate` table created
9. `Report.pdf_template_id` column exists, `Report.format` column removed
