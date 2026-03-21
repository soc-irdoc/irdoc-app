"""
DOCX Template service.

Manages user-uploaded .docx report templates and handles:
- Base template generation (downloadable scaffold with all placeholders)
- Template storage via StorageBackend
- Placeholder-based report rendering using the uploaded template
"""
from __future__ import annotations

import io
import logging
import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.docx_template import DocxTemplate

if TYPE_CHECKING:
    from app.services.report_renderer.payload import ReportPayload

logger = logging.getLogger(__name__)

# ── CRUD ──────────────────────────────────────────────────────────────────────

async def list_templates(org_id: str, db: AsyncSession) -> list[DocxTemplate]:
    result = await db.execute(
        select(DocxTemplate)
        .where(DocxTemplate.org_id == org_id)
        .order_by(DocxTemplate.is_default.desc(), DocxTemplate.created_at.asc())
    )
    return list(result.scalars().all())


async def get_template(template_id: str, org_id: str, db: AsyncSession) -> DocxTemplate:
    result = await db.execute(
        select(DocxTemplate).where(
            DocxTemplate.id == template_id,
            DocxTemplate.org_id == org_id,
        )
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="DOCX template not found")
    return t


async def get_default_template(org_id: str, db: AsyncSession) -> DocxTemplate | None:
    result = await db.execute(
        select(DocxTemplate).where(
            DocxTemplate.org_id == org_id,
            DocxTemplate.is_default == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def create_template(
    org_id: str,
    name: str,
    file_bytes: bytes,
    file_size: int,
    created_by: str,
    db: AsyncSession,
) -> DocxTemplate:
    from app.services.storage.resolver import get_storage_backend

    template_id = str(uuid.uuid4())
    storage_path = f"docx_templates/{org_id}/{template_id}.docx"

    backend = get_storage_backend()
    await backend.store(file_bytes, storage_path)

    # Check if this should auto-become default (first template for org)
    existing = await list_templates(org_id, db)
    is_default = len(existing) == 0

    t = DocxTemplate(
        id=template_id,
        org_id=org_id,
        name=name,
        is_default=is_default,
        storage_path=storage_path,
        file_size=file_size,
        created_by=created_by,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


async def rename_template(
    template_id: str, org_id: str, name: str, db: AsyncSession
) -> DocxTemplate:
    t = await get_template(template_id, org_id, db)
    t.name = name
    await db.commit()
    await db.refresh(t)
    return t


async def set_default(template_id: str, org_id: str, db: AsyncSession) -> DocxTemplate:
    # Clear all defaults for this org
    await db.execute(
        update(DocxTemplate)
        .where(DocxTemplate.org_id == org_id)
        .values(is_default=False)
    )
    # Set the selected one as default
    t = await get_template(template_id, org_id, db)
    t.is_default = True
    await db.commit()
    await db.refresh(t)
    return t


async def delete_template(template_id: str, org_id: str, db: AsyncSession) -> None:
    from app.services.storage.resolver import get_storage_backend

    t = await get_template(template_id, org_id, db)

    # Delete file from storage (best effort)
    if t.storage_path:
        try:
            backend = get_storage_backend()
            await backend.delete(t.storage_path)
        except Exception as exc:
            logger.warning("docx_template_service: delete storage failed: %s", exc)

    await db.delete(t)
    await db.commit()


# ── Template file retrieval ───────────────────────────────────────────────────

async def get_template_bytes(template: DocxTemplate) -> bytes:
    """Return the .docx bytes for a stored template."""
    from app.services.storage.resolver import get_storage_backend

    if not template.storage_path:
        raise HTTPException(status_code=404, detail="Template file not found in storage")
    backend = get_storage_backend()
    return await backend.retrieve(template.storage_path)


# ── Base template generation ──────────────────────────────────────────────────

def generate_base_template() -> bytes:
    """
    Generate the downloadable base DOCX template.

    The document contains every possible section with {{PLACEHOLDER}} markers.
    Users download this, edit it in Word (add logo, change styles, adjust layout),
    then upload it back. The placeholders are replaced at report generation time.

    Placeholders:
      {{INCIDENT_TITLE}}       Incident title
      {{INCIDENT_REF}}         Reference number (INC-YYYY-NNNN)
      {{SEVERITY}}             Severity label (SEV-1 Critical, etc.)
      {{STATUS}}               Status (Open, Contained, Closed, Monitoring)
      {{CREATED_AT}}           Date/time incident was opened
      {{CONTAINED_AT}}         Date/time incident was contained (or "Not yet contained")
      {{CLOSED_AT}}            Date/time incident was closed (or "Not yet closed")
      {{DURATION}}             Human-readable incident duration
      {{AFFECTED_USERS}}       Number of affected users
      {{ATTACK_VECTOR}}        Attack vector(s), comma-separated
      {{EXECUTIVE_SUMMARY}}    Executive summary text
      {{TIMELINE_COUNT}}       Number of timeline entries
      {{IOC_COUNT}}            Number of IOCs
      {{TASK_COMPLETION_PCT}}  Task completion percentage (e.g. "75%")
      {{TIMELINE_SECTION}}     Replaced with a full timeline table
      {{IOC_TABLE}}            Replaced with a full IOC table
      {{TASKS_TABLE}}          Replaced with a full tasks table
      {{EVIDENCE_TABLE}}       Replaced with a full evidence register table
      {{GENERATED_AT}}         Report generation timestamp
      {{GENERATED_BY}}         Name of the analyst who generated the report
      {{CLASSIFICATION}}       Report classification (CONFIDENTIAL, RESTRICTED, etc.)
    """
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt, RGBColor

    doc = Document()

    # Page margins
    for sec in doc.sections:
        sec.top_margin = Inches(1)
        sec.bottom_margin = Inches(1)
        sec.left_margin = Inches(1.2)
        sec.right_margin = Inches(1.2)

    # ── Title Page ─────────────────────────────────────────────────────────────
    p = doc.add_paragraph("[ ADD COMPANY LOGO HERE ]")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _style_run(p.runs[0] if p.runs else p.add_run("[ ADD COMPANY LOGO HERE ]"),
               size=10, italic=True, color=RGBColor(0xAA, 0xAA, 0xAA))

    doc.add_paragraph()

    h = doc.add_heading("INCIDENT REPORT", level=1)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("{{CLASSIFICATION}}")
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)

    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("[ ORGANISATION NAME — Edit this page to match your branding ]")
    run.italic = True
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)

    doc.add_page_break()

    # ── Incident Overview ──────────────────────────────────────────────────────
    doc.add_heading("INCIDENT OVERVIEW", level=1)

    overview_rows = [
        ("Reference",      "{{INCIDENT_REF}}"),
        ("Title",          "{{INCIDENT_TITLE}}"),
        ("Severity",       "{{SEVERITY}}"),
        ("Status",         "{{STATUS}}"),
        ("Opened",         "{{CREATED_AT}}"),
        ("Contained",      "{{CONTAINED_AT}}"),
        ("Closed",         "{{CLOSED_AT}}"),
        ("Duration",       "{{DURATION}}"),
        ("Affected Users", "{{AFFECTED_USERS}}"),
        ("Attack Vector",  "{{ATTACK_VECTOR}}"),
    ]
    tbl = doc.add_table(rows=len(overview_rows), cols=2)
    tbl.style = "Table Grid"
    for i, (label, value) in enumerate(overview_rows):
        tbl.rows[i].cells[0].text = label
        tbl.rows[i].cells[1].text = value
        for para in tbl.rows[i].cells[0].paragraphs:
            for run in para.runs:
                run.bold = True

    doc.add_paragraph()

    # ── Executive Summary ──────────────────────────────────────────────────────
    doc.add_heading("EXECUTIVE SUMMARY", level=1)
    doc.add_paragraph("{{EXECUTIVE_SUMMARY}}")
    doc.add_paragraph()

    # ── Statistics ────────────────────────────────────────────────────────────
    doc.add_heading("STATISTICS", level=1)
    stat_tbl = doc.add_table(rows=2, cols=3)
    stat_tbl.style = "Table Grid"
    headers = stat_tbl.rows[0].cells
    headers[0].text = "Timeline Entries"
    headers[1].text = "IOCs Identified"
    headers[2].text = "Tasks Completed"
    for cell in headers:
        for para in cell.paragraphs:
            for run in para.runs:
                run.bold = True
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    values = stat_tbl.rows[1].cells
    values[0].text = "{{TIMELINE_COUNT}}"
    values[1].text = "{{IOC_COUNT}}"
    values[2].text = "{{TASK_COMPLETION_PCT}}"
    for cell in values:
        for para in cell.paragraphs:
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()

    # ── Timeline ──────────────────────────────────────────────────────────────
    doc.add_heading("TIMELINE OF EVENTS", level=1)
    p = doc.add_paragraph("{{TIMELINE_SECTION}}")
    p.add_run()  # ensure single run for clean replacement
    doc.add_paragraph()

    # ── IOCs ──────────────────────────────────────────────────────────────────
    doc.add_heading("INDICATORS OF COMPROMISE", level=1)
    doc.add_paragraph("{{IOC_TABLE}}")
    doc.add_paragraph()

    # ── Tasks ─────────────────────────────────────────────────────────────────
    doc.add_heading("RESPONSE TASKS", level=1)
    doc.add_paragraph("{{TASKS_TABLE}}")
    doc.add_paragraph()

    # ── Evidence ──────────────────────────────────────────────────────────────
    doc.add_heading("EVIDENCE REGISTER", level=1)
    doc.add_paragraph("{{EVIDENCE_TABLE}}")
    doc.add_paragraph()

    # ── Report Metadata ───────────────────────────────────────────────────────
    doc.add_heading("REPORT METADATA", level=2)
    meta_tbl = doc.add_table(rows=3, cols=2)
    meta_tbl.style = "Table Grid"
    for i, (label, value) in enumerate([
        ("Generated At",    "{{GENERATED_AT}}"),
        ("Generated By",    "{{GENERATED_BY}}"),
        ("Classification",  "{{CLASSIFICATION}}"),
    ]):
        meta_tbl.rows[i].cells[0].text = label
        meta_tbl.rows[i].cells[1].text = value
        for para in meta_tbl.rows[i].cells[0].paragraphs:
            for run in para.runs:
                run.bold = True

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _style_run(run, size: int = 12, bold: bool = False, italic: bool = False,
               color: RGBColor | None = None):
    from docx.shared import Pt
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color


# ── Template rendering ────────────────────────────────────────────────────────

def render_with_template(
    template_bytes: bytes,
    payload: "ReportPayload",
    classification: str,
) -> bytes:
    """
    Fill a DOCX template with real incident data.

    - Replaces all {{PLACEHOLDER}} markers via run-merging (handles Word's run splits)
    - Replaces {{TIMELINE_SECTION}}, {{IOC_TABLE}}, {{TASKS_TABLE}}, {{EVIDENCE_TABLE}}
      with actual Word tables inserted at the marker paragraph's position
    """
    from docx import Document

    doc = Document(io.BytesIO(template_bytes))

    simple_replacements = _build_replacements(payload, classification)

    # 1. Replace all simple text placeholders
    for para in _iter_all_paragraphs(doc):
        _replace_in_para(para, simple_replacements)

    # 2. Replace table section markers with real Word tables
    for marker, builder in [
        ("{{TIMELINE_SECTION}}", lambda: _build_timeline_table(doc, payload)),
        ("{{IOC_TABLE}}",        lambda: _build_ioc_table(doc, payload)),
        ("{{TASKS_TABLE}}",      lambda: _build_tasks_table(doc, payload)),
        ("{{EVIDENCE_TABLE}}",   lambda: _build_evidence_table(doc, payload)),
    ]:
        _replace_marker_with_table(doc, marker, builder)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _build_replacements(payload: "ReportPayload", classification: str) -> dict[str, str]:
    def _fmt(dt) -> str:
        if dt is None:
            return "—"
        return dt.strftime("%Y-%m-%d %H:%M UTC")

    return {
        "{{INCIDENT_TITLE}}":      payload.incident.title or "",
        "{{INCIDENT_REF}}":        payload.incident.incident_ref or "",
        "{{SEVERITY}}":            payload.severity_label,
        "{{STATUS}}":              payload.status_label,
        "{{CREATED_AT}}":          _fmt(payload.incident.created_at),
        "{{CONTAINED_AT}}":        payload.contained_at_str or "Not yet contained",
        "{{CLOSED_AT}}":           payload.closed_at_str or "Not yet closed",
        "{{DURATION}}":            payload.duration_str,
        "{{AFFECTED_USERS}}":      str(payload.incident.affected_users or "Unknown"),
        "{{ATTACK_VECTOR}}":       (
            ", ".join(payload.incident.attack_vector)
            if payload.incident.attack_vector
            else "Not specified"
        ),
        "{{EXECUTIVE_SUMMARY}}":   payload.incident.executive_summary or "No executive summary provided.",
        "{{TIMELINE_COUNT}}":      str(payload.entry_count),
        "{{IOC_COUNT}}":           str(payload.ioc_count),
        "{{TASK_COMPLETION_PCT}}": f"{payload.task_completion_pct}%",
        "{{GENERATED_AT}}":        payload.generated_at.strftime("%Y-%m-%d %H:%M UTC"),
        "{{GENERATED_BY}}":        (payload.analyst.full_name if payload.analyst else "System"),
        "{{CLASSIFICATION}}":      classification.upper(),
    }


def _iter_all_paragraphs(doc):
    """Yield every paragraph in the document — body, tables, headers, footers."""
    yield from doc.paragraphs
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from cell.paragraphs
    try:
        for section in doc.sections:
            if section.header:
                yield from section.header.paragraphs
            if section.footer:
                yield from section.footer.paragraphs
    except Exception:
        pass


def _replace_in_para(para, replacements: dict[str, str]) -> None:
    """
    Merge all runs in the paragraph, apply replacements, put result in run[0].
    This handles the common case where Word splits {{PLACEHOLDER}} across runs.
    """
    full_text = "".join(run.text for run in para.runs)
    if not any(k in full_text for k in replacements):
        return
    new_text = full_text
    for k, v in replacements.items():
        new_text = new_text.replace(k, str(v))
    if para.runs:
        para.runs[0].text = new_text
        for run in para.runs[1:]:
            run.text = ""


def _replace_marker_with_table(doc, marker: str, table_builder) -> None:
    """
    Find the paragraph that contains marker, build a table via table_builder(),
    insert the table at that position, and remove the marker paragraph.
    """
    for para in doc.paragraphs:
        full_text = "".join(r.text for r in para.runs)
        if marker not in full_text:
            continue
        # Build the table (it gets appended to doc body temporarily)
        table = table_builder()
        if table is None:
            # No data — replace marker with "None" message
            para.runs[0].text = f"No data available." if para.runs else ""
            for run in para.runs[1:]:
                run.text = ""
            return
        # Detach table from end of doc body
        table._tbl.getparent().remove(table._tbl)
        # Insert table right after the marker paragraph in the XML
        para._element.addnext(table._tbl)
        # Remove the marker paragraph
        para._element.getparent().remove(para._element)
        return


# ── Table builders ────────────────────────────────────────────────────────────

def _build_timeline_table(doc, payload: "ReportPayload"):
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    if not payload.entries:
        return None

    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(["Time", "Type", "Source", "Description"]):
        hdr[i].text = h
        for para in hdr[i].paragraphs:
            for run in para.runs:
                run.bold = True

    for e in payload.entries:
        row = table.add_row().cells
        row[0].text = e.occurred_at.strftime("%Y-%m-%d %H:%M") if e.occurred_at else "—"
        row[1].text = (e.entry_type or "").upper()
        row[2].text = e.source or "—"
        row[3].text = e.description or ""

    return table


def _build_ioc_table(doc, payload: "ReportPayload"):
    if not payload.iocs:
        return None

    table = doc.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(["Type", "Value", "Status", "Confidence", "TLP"]):
        hdr[i].text = h
        for para in hdr[i].paragraphs:
            for run in para.runs:
                run.bold = True

    for ioc in payload.iocs:
        row = table.add_row().cells
        row[0].text = ioc.ioc_type or "—"
        row[1].text = ioc.value or "—"
        row[2].text = ioc.status or "—"
        row[3].text = f"{ioc.confidence}%" if ioc.confidence is not None else "—"
        row[4].text = ioc.tlp_level or "—"

    return table


def _build_tasks_table(doc, payload: "ReportPayload"):
    if not payload.tasks:
        return None

    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(["Task", "Phase", "Priority", "Status"]):
        hdr[i].text = h
        for para in hdr[i].paragraphs:
            for run in para.runs:
                run.bold = True

    for t in payload.tasks:
        row = table.add_row().cells
        row[0].text = t.title or "—"
        row[1].text = t.phase or "—"
        row[2].text = t.priority or "—"
        row[3].text = "✓ Done" if t.status == "done" else "○ " + (t.status or "open")

    return table


def _build_evidence_table(doc, payload: "ReportPayload"):
    if not payload.attachments:
        return None

    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(["Filename", "Type", "Size", "SHA-256 (first 16)"]):
        hdr[i].text = h
        for para in hdr[i].paragraphs:
            for run in para.runs:
                run.bold = True

    for att in payload.attachments:
        row = table.add_row().cells
        row[0].text = getattr(att, "original_name", att.stored_path.split("/")[-1]) or "—"
        row[1].text = att.mime_type or "—"
        row[2].text = _fmt_size(att.file_size)
        row[3].text = (att.sha256[:16] + "…") if att.sha256 else "—"

    return table


def _fmt_size(size: int | None) -> str:
    if size is None:
        return "—"
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
