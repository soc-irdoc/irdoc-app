# PDF Report Template System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the DOCX placeholder report system with a mammoth-based PDF pipeline where companies upload a branded DOCX template (with a `{{IRDoc_CONTENT}}` marker page) and IRDoc generates a complete, fixed-section incident report wrapped in the company's branding.

**Architecture:** DOCX upload → mammoth converts body to HTML → split at `{{IRDoc_CONTENT}}` marker → store prefix/suffix HTML + @page CSS in `PdfTemplate` record. At render time: generate fixed content HTML via existing Jinja2 partials → assemble with prefix/suffix → single WeasyPrint pass → PDF.

**Tech Stack:** Python, FastAPI, SQLAlchemy 2.0, Alembic, mammoth (new), python-docx (kept for header/footer extraction), WeasyPrint (kept), Jinja2, Celery, pytest

**Spec:** `docs/superpowers/specs/2026-05-23-pdf-report-template-system-design.md`

---

## File Map

**Create:**
- `backend/app/models/pdf_template.py`
- `backend/app/schemas/pdf_template.py`
- `backend/alembic/versions/008_pdf_template.py`
- `backend/app/services/pdf_template_service.py`
- `backend/app/services/report_renderer/fixed_report.py`
- `backend/app/api/v1/pdf_templates.py`
- `backend/tests/unit/test_pdf_template_service.py`
- `backend/tests/unit/test_fixed_report.py`

**Modify:**
- `backend/requirements.txt` — add `mammoth`
- `backend/templates/reports/base.html` — add `prefix_html`, `suffix_html`, `page_css` support
- `backend/app/services/report_renderer/engine.py` — replace with `render_incident_pdf()`
- `backend/app/services/report_renderer/__init__.py` — update exports
- `backend/app/models/report.py` — add `pdf_template_id`, remove `format` + `report_template_id`
- `backend/app/schemas/report.py` — update `ReportGenerateRequest` and `ReportOut`
- `backend/app/services/report_service.py` — simplify to single PDF path
- `backend/app/workers/tasks.py` — simplify `generate_report`, update `sync_to_sharepoint`
- `backend/app/api/v1/reports.py` — hardcode PDF MIME in download, remove format param
- `backend/app/main.py` — swap `docx_templates` → `pdf_templates` router

**Delete:**
- `backend/app/services/docx_template_service.py`
- `backend/app/services/report_renderer/docx_builder.py`
- `backend/app/api/v1/docx_templates.py`
- `backend/app/models/docx_template.py`
- `backend/app/schemas/docx_template.py`

---

## Task 1: Add mammoth dependency

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add mammoth to requirements.txt**

Open `backend/requirements.txt` and add after the `python-docx==1.1.2` line:

```
mammoth==1.8.0
```

- [ ] **Step 2: Install the dependency**

```bash
cd backend
pip install mammoth==1.8.0
```

Expected: `Successfully installed mammoth-1.8.0`

- [ ] **Step 3: Verify import works**

```bash
python -c "import mammoth; print(mammoth.__version__)"
```

Expected: `1.8.0`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "feat(deps): add mammoth for DOCX-to-HTML conversion"
```

---

## Task 2: PdfTemplate model and schema

**Files:**
- Create: `backend/app/models/pdf_template.py`
- Create: `backend/app/schemas/pdf_template.py`

- [ ] **Step 1: Write failing test for model import**

Create `backend/tests/unit/test_pdf_template_model.py`:

```python
"""Smoke test: PdfTemplate model imports and has expected columns."""
from app.models.pdf_template import PdfTemplate


def test_pdf_template_has_required_columns():
    cols = {c.key for c in PdfTemplate.__table__.columns}
    assert "id" in cols
    assert "org_id" in cols
    assert "prefix_html" in cols
    assert "suffix_html" in cols
    assert "page_css" in cols
    assert "mammoth_warnings" in cols
    assert "original_docx_path" in cols
    assert "is_default" in cols
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/unit/test_pdf_template_model.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.pdf_template'`

- [ ] **Step 3: Create the model**

Create `backend/app/models/pdf_template.py`:

```python
"""PdfTemplate model — company-branded DOCX templates for PDF report generation."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PdfTemplate(Base):
    __tablename__ = "pdf_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    original_docx_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    prefix_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    suffix_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_css: Mapped[str | None] = mapped_column(Text, nullable=True)
    mammoth_warnings: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 4: Create the schema**

Create `backend/app/schemas/pdf_template.py`:

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PdfTemplateOut(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    is_default: bool
    file_size: int | None
    mammoth_warnings: list | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PdfTemplateRename(BaseModel):
    name: str
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_pdf_template_model.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/pdf_template.py backend/app/schemas/pdf_template.py backend/tests/unit/test_pdf_template_model.py
git commit -m "feat(model): add PdfTemplate model and schema"
```

---

## Task 3: Database migration 008

**Files:**
- Create: `backend/alembic/versions/008_pdf_template.py`

- [ ] **Step 1: Create the migration file**

Create `backend/alembic/versions/008_pdf_template.py`:

```python
"""Replace docx_templates with pdf_templates; update reports table.

Revision ID: 008
Revises: 007
Create Date: 2026-05-23
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Create pdf_templates ──────────────────────────────────────────────────
    op.create_table(
        "pdf_templates",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("original_docx_path", sa.String(500), nullable=True),
        sa.Column("prefix_html", sa.Text(), nullable=True),
        sa.Column("suffix_html", sa.Text(), nullable=True),
        sa.Column("page_css", sa.Text(), nullable=True),
        sa.Column("mammoth_warnings", postgresql.JSONB(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pdf_templates_org_id", "pdf_templates", ["org_id"])

    # ── Update reports ────────────────────────────────────────────────────────
    op.add_column("reports", sa.Column(
        "pdf_template_id",
        postgresql.UUID(as_uuid=False),
        sa.ForeignKey("pdf_templates.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.drop_column("reports", "format")
    op.execute("UPDATE reports SET report_template_id = NULL")
    op.drop_constraint("reports_report_template_id_fkey", "reports", type_="foreignkey")
    op.drop_column("reports", "report_template_id")

    # ── Drop docx_templates ───────────────────────────────────────────────────
    op.drop_index("ix_docx_templates_org_id", "docx_templates")
    op.drop_table("docx_templates")


def downgrade() -> None:
    op.create_table(
        "docx_templates",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("storage_path", sa.String(500), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_docx_templates_org_id", "docx_templates", ["org_id"])
    op.add_column("reports", sa.Column("format", sa.String(20), nullable=False, server_default="pdf"))
    op.add_column("reports", sa.Column(
        "report_template_id",
        postgresql.UUID(as_uuid=False),
        sa.ForeignKey("report_templates.id"),
        nullable=True,
    ))
    op.drop_column("reports", "pdf_template_id")
    op.drop_index("ix_pdf_templates_org_id", "pdf_templates")
    op.drop_table("pdf_templates")
```

- [ ] **Step 2: Run the migration**

```bash
cd backend
alembic upgrade 008
```

Expected: Migration completes without error. Check output contains `Running upgrade 007 -> 008`.

- [ ] **Step 3: Verify schema**

```bash
python -c "
import asyncio
from app.core.database import engine
from sqlalchemy import inspect, text

async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='reports' ORDER BY column_name\"))
        cols = [r[0] for r in result.fetchall()]
        print('reports cols:', cols)
        assert 'pdf_template_id' in cols, 'pdf_template_id missing'
        assert 'format' not in cols, 'format should be gone'
        assert 'report_template_id' not in cols, 'report_template_id should be gone'
        print('OK')

asyncio.run(check())
"
```

Expected: Prints `reports cols: [...]` with `pdf_template_id` present, `format` and `report_template_id` absent.

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/008_pdf_template.py
git commit -m "feat(migration): add pdf_templates, update reports table (008)"
```

---

## Task 4: PdfTemplate service

**Files:**
- Create: `backend/app/services/pdf_template_service.py`
- Create: `backend/tests/unit/test_pdf_template_service.py`

- [ ] **Step 1: Write failing unit tests**

Create `backend/tests/unit/test_pdf_template_service.py`:

```python
"""Unit tests for pdf_template_service parsing logic."""
import pytest
from app.services.pdf_template_service import _split_at_marker, _extract_page_css


# ── _split_at_marker ──────────────────────────────────────────────────────────

def test_split_at_marker_basic():
    html = "<p>Cover content</p><p>{{IRDoc_CONTENT}}</p><p>Back matter</p>"
    prefix, suffix = _split_at_marker(html)
    assert "Cover content" in prefix
    assert "Back matter" in suffix
    assert "IRDoc_CONTENT" not in prefix
    assert "IRDoc_CONTENT" not in suffix


def test_split_at_marker_no_marker_raises():
    html = "<p>Some content without the marker</p>"
    with pytest.raises(ValueError, match="{{IRDoc_CONTENT}}"):
        _split_at_marker(html)


def test_split_empty_prefix():
    html = "<p>{{IRDoc_CONTENT}}</p><p>Back matter</p>"
    prefix, suffix = _split_at_marker(html)
    assert prefix == ""
    assert "Back matter" in suffix


def test_split_empty_suffix():
    html = "<p>Cover content</p><p>{{IRDoc_CONTENT}}</p>"
    prefix, suffix = _split_at_marker(html)
    assert "Cover content" in prefix
    assert suffix == ""


# ── _extract_page_css ─────────────────────────────────────────────────────────

def test_extract_page_css_returns_string():
    # Minimal valid DOCX bytes (we mock with an empty doc)
    import io
    from docx import Document
    doc = Document()
    buf = io.BytesIO()
    doc.save(buf)
    css = _extract_page_css(buf.getvalue())
    assert isinstance(css, str)
    assert "@page" in css


def test_extract_page_css_includes_page_numbers():
    import io
    from docx import Document
    doc = Document()
    buf = io.BytesIO()
    doc.save(buf)
    css = _extract_page_css(buf.getvalue())
    assert "counter(page)" in css
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/unit/test_pdf_template_service.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.pdf_template_service'`

- [ ] **Step 3: Create the service**

Create `backend/app/services/pdf_template_service.py`:

```python
"""
PdfTemplate service.

Handles DOCX upload processing:
- Convert DOCX body to HTML via mammoth
- Split HTML at {{IRDoc_CONTENT}} marker
- Extract logo and header/footer from DOCX → WeasyPrint @page CSS
- CRUD operations on PdfTemplate records
"""
from __future__ import annotations

import base64
import io
import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pdf_template import PdfTemplate

logger = logging.getLogger(__name__)

_MARKER = "{{IRDoc_CONTENT}}"

_DEFAULT_PAGE_CSS = """
@page {
    margin: 25mm 20mm 25mm 20mm;
    @bottom-right {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 9pt;
        color: #94a3b8;
    }
}
"""


# ── Parsing helpers ───────────────────────────────────────────────────────────

def _split_at_marker(html: str) -> tuple[str, str]:
    """Split mammoth HTML at the {{IRDoc_CONTENT}} marker paragraph.

    Returns (prefix_html, suffix_html). Raises ValueError if marker is absent.
    """
    if _MARKER not in html:
        raise ValueError(
            f"Template must contain a paragraph with exactly {_MARKER}"
        )

    idx = html.index(_MARKER)
    para_start = html.rfind("<p", 0, idx)
    para_end_raw = html.find("</p>", idx)
    para_end = para_end_raw + len("</p>") if para_end_raw != -1 else idx + len(_MARKER)

    prefix_html = (html[:para_start] if para_start != -1 else html[:idx]).strip()
    suffix_html = html[para_end:].strip()
    return prefix_html, suffix_html


def _extract_page_css(docx_bytes: bytes) -> str:
    """Extract header/footer logo from DOCX and return WeasyPrint @page CSS.

    Looks for the first image in the default header. Falls back to page-numbers-only.
    """
    from docx import Document

    doc = Document(io.BytesIO(docx_bytes))
    logo_data_uri: str | None = None

    for section in doc.sections:
        header = section.header
        if header is None:
            continue
        try:
            for rel in header.part.rels.values():
                if "image" in rel.reltype:
                    img_bytes = rel.target_part.blob
                    content_type = rel.target_part.content_type
                    b64 = base64.b64encode(img_bytes).decode()
                    logo_data_uri = f"data:{content_type};base64,{b64}"
                    break
        except Exception as exc:
            logger.debug("Could not extract header image: %s", exc)
        if logo_data_uri:
            break

    if logo_data_uri:
        return f"""
@page {{
    margin: 25mm 20mm 25mm 20mm;
    @top-right {{
        content: url("{logo_data_uri}");
        height: 30px;
    }}
    @bottom-right {{
        content: "Page " counter(page) " of " counter(pages);
        font-size: 9pt;
        color: #94a3b8;
    }}
}}
"""
    return _DEFAULT_PAGE_CSS


def _process_docx(docx_bytes: bytes) -> tuple[str, str, str, list[str]]:
    """Convert DOCX to prefix_html, suffix_html, page_css, warnings.

    Raises ValueError if the {{IRDoc_CONTENT}} marker is missing.
    """
    import mammoth

    result = mammoth.convert_to_html(io.BytesIO(docx_bytes))
    warnings = [str(m.message) for m in result.messages]
    prefix_html, suffix_html = _split_at_marker(result.value)
    page_css = _extract_page_css(docx_bytes)
    return prefix_html, suffix_html, page_css, warnings


# ── CRUD ──────────────────────────────────────────────────────────────────────

async def create_template(
    org_id: str,
    name: str,
    file_bytes: bytes,
    file_size: int,
    created_by: str,
    db: AsyncSession,
) -> PdfTemplate:
    """Process DOCX upload and create a PdfTemplate record."""
    from app.services.storage.resolver import get_storage_backend

    prefix_html, suffix_html, page_css, warnings = _process_docx(file_bytes)

    storage_path = f"pdf-templates/{org_id}/{uuid.uuid4()}.docx"
    backend = get_storage_backend()
    await backend.store(file_bytes, storage_path)

    template = PdfTemplate(
        org_id=org_id,
        name=name,
        is_default=False,
        original_docx_path=storage_path,
        prefix_html=prefix_html,
        suffix_html=suffix_html,
        page_css=page_css,
        mammoth_warnings=warnings or None,
        file_size=file_size,
        created_by=created_by,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def list_templates(org_id: str, db: AsyncSession) -> list[PdfTemplate]:
    result = await db.execute(
        select(PdfTemplate)
        .where(PdfTemplate.org_id == org_id)
        .order_by(PdfTemplate.is_default.desc(), PdfTemplate.created_at.asc())
    )
    return list(result.scalars().all())


async def get_template(template_id: str, org_id: str, db: AsyncSession) -> PdfTemplate:
    result = await db.execute(
        select(PdfTemplate).where(
            PdfTemplate.id == template_id,
            PdfTemplate.org_id == org_id,
        )
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="PDF template not found")
    return t


async def rename_template(
    template_id: str, org_id: str, name: str, db: AsyncSession
) -> PdfTemplate:
    t = await get_template(template_id, org_id, db)
    t.name = name
    await db.commit()
    await db.refresh(t)
    return t


async def set_default(
    template_id: str, org_id: str, db: AsyncSession
) -> PdfTemplate:
    await db.execute(
        update(PdfTemplate)
        .where(PdfTemplate.org_id == org_id)
        .values(is_default=False)
    )
    t = await get_template(template_id, org_id, db)
    t.is_default = True
    await db.commit()
    await db.refresh(t)
    return t


async def delete_template(
    template_id: str, org_id: str, db: AsyncSession
) -> None:
    t = await get_template(template_id, org_id, db)
    if t.original_docx_path:
        try:
            from app.services.storage.resolver import get_storage_backend
            backend = get_storage_backend()
            await backend.delete(t.original_docx_path)
        except Exception:
            pass
    await db.delete(t)
    await db.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_pdf_template_service.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pdf_template_service.py backend/tests/unit/test_pdf_template_service.py
git commit -m "feat(service): add PdfTemplate service with mammoth import pipeline"
```

---

## Task 5: Fixed report renderer

**Files:**
- Create: `backend/app/services/report_renderer/fixed_report.py`
- Create: `backend/tests/unit/test_fixed_report.py`

- [ ] **Step 1: Write failing unit tests**

Create `backend/tests/unit/test_fixed_report.py`:

```python
"""Unit tests for fixed report section has_data() checks."""
import pytest
from unittest.mock import MagicMock
from app.services.report_renderer.fixed_report import _FIXED_SECTIONS


def _make_payload(**overrides):
    """Build a minimal mock ReportPayload."""
    p = MagicMock()
    p.entries = []
    p.iocs = []
    p.tasks = []
    p.attachments = []
    p.ai_executive_summary = None
    p.incident.executive_summary = None
    for k, v in overrides.items():
        setattr(p, k, v)
    return p


def _section(type_):
    return next(s for s in _FIXED_SECTIONS if s["type"] == type_)


def test_cover_always_shown():
    p = _make_payload()
    assert _section("cover")["has_data"](p) is True


def test_stat_row_always_shown():
    p = _make_payload()
    assert _section("stat_row")["has_data"](p) is True


def test_executive_summary_hidden_when_empty():
    p = _make_payload()
    p.incident.executive_summary = None
    assert _section("section")["has_data"](p) is False


def test_executive_summary_shown_when_set():
    p = _make_payload()
    p.incident.executive_summary = "This is the exec summary."
    assert _section("section")["has_data"](p) is True


def test_timeline_hidden_when_no_entries():
    p = _make_payload(entries=[])
    assert _section("timeline")["has_data"](p) is False


def test_timeline_shown_with_entries():
    p = _make_payload(entries=[MagicMock()])
    assert _section("timeline")["has_data"](p) is True


def test_ioc_table_hidden_when_no_iocs():
    p = _make_payload(iocs=[])
    assert _section("ioc_table")["has_data"](p) is False


def test_ioc_table_shown_with_iocs():
    p = _make_payload(iocs=[MagicMock()])
    assert _section("ioc_table")["has_data"](p) is True


def test_task_list_hidden_when_no_tasks():
    p = _make_payload(tasks=[])
    assert _section("task_list")["has_data"](p) is False


def test_evidence_register_hidden_when_no_attachments():
    p = _make_payload(attachments=[])
    assert _section("evidence_register")["has_data"](p) is False


def test_ai_narrative_hidden_when_no_summary():
    p = _make_payload()
    p.ai_executive_summary = None
    assert _section("text_block")["has_data"](p) is False


def test_ai_narrative_shown_when_summary_present():
    p = _make_payload()
    p.ai_executive_summary = "AI generated text."
    assert _section("text_block")["has_data"](p) is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/unit/test_fixed_report.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.report_renderer.fixed_report'`

- [ ] **Step 3: Create the fixed report renderer**

Create `backend/app/services/report_renderer/fixed_report.py`:

```python
"""
Fixed incident report renderer.

Defines the canonical set of report sections with auto-hide logic.
Renders using existing Jinja2 block partials — no schema JSON needed.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import jinja2

if TYPE_CHECKING:
    from app.services.report_renderer.payload import ReportPayload

logger = logging.getLogger(__name__)

# Ordered list of fixed sections.
# Each entry: type (matches blocks/{type}.html), has_data predicate, block config factory.
_FIXED_SECTIONS = [
    {
        "type": "cover",
        "has_data": lambda p: True,
        "block": lambda p, classification: {
            "type": "cover",
            "watermark": classification,
            "fields": [
                "incident.severity",
                "incident.status",
                "analyst.full_name",
                "incident.opened_at",
                "generated_at",
            ],
        },
    },
    {
        "type": "stat_row",
        "has_data": lambda p: True,
        "block": lambda p, classification: {
            "type": "stat_row",
            "stats": ["severity", "status", "duration", "affected_users", "ioc_count", "entry_count"],
        },
    },
    {
        "type": "section",
        "has_data": lambda p: bool(p.incident.executive_summary),
        "block": lambda p, classification: {
            "type": "section",
            "field": "incident.executive_summary",
            "label": "Executive Summary",
        },
    },
    {
        "type": "timeline",
        "has_data": lambda p: len(p.entries) > 0,
        "block": lambda p, classification: {"type": "timeline"},
    },
    {
        "type": "ioc_table",
        "has_data": lambda p: len(p.iocs) > 0,
        "block": lambda p, classification: {"type": "ioc_table"},
    },
    {
        "type": "task_list",
        "has_data": lambda p: len(p.tasks) > 0,
        "block": lambda p, classification: {"type": "task_list"},
    },
    {
        "type": "evidence_register",
        "has_data": lambda p: len(p.attachments) > 0,
        "block": lambda p, classification: {"type": "evidence_register"},
    },
    {
        "type": "text_block",
        "has_data": lambda p: bool(p.ai_executive_summary),
        "block": lambda p, classification: {
            "type": "text_block",
            "field": "ai.executive_summary",
            "label": "AI Analysis",
        },
    },
]


def render_fixed_report_html(
    payload: "ReportPayload",
    classification: str = "CONFIDENTIAL",
    env: jinja2.Environment | None = None,
    prefix_html: str = "",
    suffix_html: str = "",
    page_css: str = "",
) -> str:
    """Render the complete fixed incident report as an HTML string.

    Uses existing Jinja2 block partials. Sections with no data are skipped.
    Prefix and suffix HTML (from a PdfTemplate) are injected into base.html.
    """
    from pathlib import Path
    from app.services.report_renderer.engine import _build_jinja_env, _TEMPLATE_DIR

    jinja_env = env or _build_jinja_env()

    rendered_blocks: list[str] = []
    for section in _FIXED_SECTIONS:
        if not section["has_data"](payload):
            continue
        block_config = section["block"](payload, classification)
        block_type = block_config["type"]
        try:
            partial = jinja_env.get_template(f"reports/blocks/{block_type}.html")
            rendered_blocks.append(partial.render(block=block_config, p=payload))
        except jinja2.TemplateNotFound:
            logger.warning("Block template not found: %s", block_type)

    base = jinja_env.get_template("reports/base.html")
    return base.render(
        blocks=rendered_blocks,
        incident=payload.incident,
        classification=classification,
        generated_at=payload.generated_at,
        analyst=payload.analyst,
        p=payload,
        prefix_html=prefix_html,
        suffix_html=suffix_html,
        page_css=page_css,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_fixed_report.py -v
```

Expected: All 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/report_renderer/fixed_report.py backend/tests/unit/test_fixed_report.py
git commit -m "feat(renderer): add fixed report renderer with auto-hide section logic"
```

---

## Task 6: Update base.html and engine.py

**Files:**
- Modify: `backend/templates/reports/base.html`
- Modify: `backend/app/services/report_renderer/engine.py`
- Modify: `backend/app/services/report_renderer/__init__.py`

- [ ] **Step 1: Update base.html to accept prefix/suffix/page_css**

In `backend/templates/reports/base.html`, make two changes:

**Change 1** — Add `{{ page_css | safe }}` inside `<style>` (after line 132 `</style>`), actually insert as a second `<style>` block just before `</head>`:

Replace the `</style>` closing tag at line 132 (end of existing styles) followed by `</head>`:

Find this block:
```html
  @media print {
    .classification-banner { position: static; }
    .content-offset { margin-top: 0; }
    h2 { page-break-after: avoid; }
    .timeline-entry, .task-item { page-break-inside: avoid; }
    .page-break { page-break-before: always; }
  }
</style>
</head>
<body>
<div class="classification-banner">{{ classification | upper }}</div>
<div class="page-wrapper content-offset">
  {% for block_html in blocks %}
  {{ block_html | safe }}
  {% endfor %}
  <div class="report-footer">
    <span>{{ classification | upper }} — {{ incident.incident_ref }}</span>
    <span>Generated {{ generated_at | format_dt }} by {{ analyst.full_name }}</span>
  </div>
</div>
</body>
</html>
```

Replace with:
```html
  @media print {
    .classification-banner { position: static; }
    .content-offset { margin-top: 0; }
    h2 { page-break-after: avoid; }
    .timeline-entry, .task-item { page-break-inside: avoid; }
    .page-break { page-break-before: always; }
  }
</style>
{% if page_css %}<style>{{ page_css | safe }}</style>{% endif %}
</head>
<body>
{% if prefix_html %}
<div class="template-prefix">{{ prefix_html | safe }}</div>
<div style="page-break-after: always;"></div>
{% endif %}
<div class="classification-banner">{{ classification | upper }}</div>
<div class="page-wrapper content-offset">
  {% for block_html in blocks %}
  {{ block_html | safe }}
  {% endfor %}
  <div class="report-footer">
    <span>{{ classification | upper }} — {{ incident.incident_ref }}</span>
    <span>Generated {{ generated_at | format_dt }} by {{ analyst.full_name }}</span>
  </div>
</div>
{% if suffix_html %}
<div style="page-break-before: always;"></div>
<div class="template-suffix">{{ suffix_html | safe }}</div>
{% endif %}
</body>
</html>
```

- [ ] **Step 2: Simplify engine.py**

Replace the entire content of `backend/app/services/report_renderer/engine.py` with:

```python
"""
Report rendering engine.

render_incident_pdf() is the main entry point.
Calls fixed_report.render_fixed_report_html() then converts to PDF via WeasyPrint.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import jinja2

if TYPE_CHECKING:
    from app.models.pdf_template import PdfTemplate
    from app.services.report_renderer.payload import ReportPayload

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent.parent.parent.parent / "templates"

_DEFAULT_PAGE_CSS = """
@page {
    margin: 25mm 20mm 25mm 20mm;
    @bottom-right {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 9pt;
        color: #94a3b8;
    }
}
"""


def _build_jinja_env() -> jinja2.Environment:
    loader = jinja2.FileSystemLoader(str(_TEMPLATE_DIR))
    env = jinja2.Environment(
        loader=loader,
        autoescape=jinja2.select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    def format_dt(value):
        if value is None:
            return "—"
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d %H:%M UTC")
        return str(value)

    def filesize(value):
        if value is None:
            return "—"
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024:
                return f"{value:.0f} {unit}"
            value /= 1024
        return f"{value:.1f} TB"

    env.filters["format_dt"] = format_dt
    env.filters["filesize"] = filesize
    return env


_jinja_env = _build_jinja_env()


def render_incident_pdf(
    payload: "ReportPayload",
    pdf_template: "PdfTemplate | None" = None,
    classification: str = "CONFIDENTIAL",
) -> bytes:
    """Render a complete fixed incident report as PDF bytes.

    If pdf_template is provided, its prefix/suffix pages and @page CSS wrap the content.
    """
    from app.services.report_renderer.fixed_report import render_fixed_report_html
    from weasyprint import HTML as WeasyHTML

    prefix_html = (pdf_template.prefix_html or "") if pdf_template else ""
    suffix_html = (pdf_template.suffix_html or "") if pdf_template else ""
    page_css = (pdf_template.page_css or _DEFAULT_PAGE_CSS) if pdf_template else _DEFAULT_PAGE_CSS

    html = render_fixed_report_html(
        payload=payload,
        classification=classification,
        env=_jinja_env,
        prefix_html=prefix_html,
        suffix_html=suffix_html,
        page_css=page_css,
    )

    try:
        return WeasyHTML(
            string=html,
            base_url=str(_TEMPLATE_DIR / "reports"),
        ).write_pdf()
    except Exception as exc:
        logger.error("WeasyPrint PDF render failed: %s", exc)
        raise
```

- [ ] **Step 3: Update __init__.py exports**

Read `backend/app/services/report_renderer/__init__.py` and update it to export `render_incident_pdf` instead of `ReportRenderer`:

```python
from app.services.report_renderer.engine import render_incident_pdf
from app.services.report_renderer.payload import build_report_payload

__all__ = ["render_incident_pdf", "build_report_payload"]
```

- [ ] **Step 4: Commit**

```bash
git add backend/templates/reports/base.html \
        backend/app/services/report_renderer/engine.py \
        backend/app/services/report_renderer/__init__.py
git commit -m "feat(engine): replace block renderer with fixed render_incident_pdf()"
```

---

## Task 7: Update Report model, schemas, and service

**Files:**
- Modify: `backend/app/models/report.py`
- Modify: `backend/app/schemas/report.py`
- Modify: `backend/app/services/report_service.py`

- [ ] **Step 1: Update Report model**

In `backend/app/models/report.py`, replace the `Report` class with:

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    pdf_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pdf_templates.id", ondelete="SET NULL"), nullable=True
    )
    report_type: Mapped[str] = mapped_column(String(30), nullable=False)
    destination: Mapped[str | None] = mapped_column(String(30), nullable=True)
    classification: Mapped[str] = mapped_column(String(30), default="confidential")
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_ai_assisted: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Keep the `SyncPolicy` class exactly as it is (do not change it).

- [ ] **Step 2: Update report schemas**

Replace the full content of `backend/app/schemas/report.py` with:

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# ─── Report Schemas ──────────────────────────────────────────────────────────

class ReportGenerateRequest(BaseModel):
    pdf_template_id: str | None = None
    classification: str = "confidential"
    include_ai: bool = False


class ReportOut(BaseModel):
    id: UUID
    incident_id: UUID
    pdf_template_id: UUID | None
    report_type: str
    destination: str | None
    classification: str
    generated_by: UUID | None
    is_ai_assisted: bool
    status: str                       # pending | generating | ready | failed
    error_message: str | None
    storage_path: str | None
    generated_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Sync Policy Schemas ─────────────────────────────────────────────────────

class SyncPolicyCreate(BaseModel):
    destination: str
    report_template_id: str | None = None
    trigger_type: str = "on_change"
    debounce_seconds: int = 60
    destination_config: dict = {}


class SyncPolicyUpdate(BaseModel):
    destination: str | None = None
    report_template_id: str | None = None
    trigger_type: str | None = None
    debounce_seconds: int | None = None
    destination_config: dict | None = None
    is_active: bool | None = None


class SyncPolicyOut(BaseModel):
    id: UUID
    incident_id: UUID
    destination: str
    report_template_id: UUID | None
    is_active: bool
    trigger_type: str
    debounce_seconds: int
    last_synced_at: datetime | None
    last_sync_status: str | None
    last_error: str | None
    created_by: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Simplify report_service.py**

Replace the full content of `backend/app/services/report_service.py` with:

```python
"""
Report service — simplified PDF-only pipeline.

All reports generate a PDF via render_incident_pdf(). The optional
pdf_template_id wraps content with company branding.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report
from app.schemas.report import ReportGenerateRequest


async def enqueue_report(
    db: AsyncSession,
    incident_id: str,
    request: ReportGenerateRequest,
    generated_by: str,
    org_id: str,
) -> Report:
    """Create a pending Report record and enqueue the Celery task."""
    from app.workers.tasks import generate_report

    if request.include_ai:
        from app.core.feature_flags import check_feature
        if not check_feature("ai_summaries"):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="AI summaries require a premium license",
            )

    if request.pdf_template_id:
        from app.services.pdf_template_service import get_template
        tmpl = await get_template(request.pdf_template_id, org_id, db)
        report_name = tmpl.name
    else:
        report_name = "Incident Report"

    report = Report(
        incident_id=incident_id,
        pdf_template_id=request.pdf_template_id,
        report_type=report_name,
        destination=None,
        classification=request.classification,
        generated_by=generated_by,
        is_ai_assisted=request.include_ai,
        status="pending",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    generate_report.delay(str(report.id), request.include_ai)
    return report


async def list_reports(db: AsyncSession, incident_id: str) -> list[Report]:
    result = await db.execute(
        select(Report)
        .where(Report.incident_id == incident_id)
        .order_by(Report.created_at.desc())
    )
    return list(result.scalars().all())


async def get_report(db: AsyncSession, report_id: str) -> Report:
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


async def delete_report(db: AsyncSession, report: Report) -> None:
    from app.services.storage.resolver import get_storage_backend
    if report.storage_path:
        try:
            backend = get_storage_backend()
            await backend.delete(report.storage_path)
        except Exception:
            pass
    await db.delete(report)
    await db.commit()
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/report.py \
        backend/app/schemas/report.py \
        backend/app/services/report_service.py
git commit -m "feat(report): simplify Report model and service to PDF-only pipeline"
```

---

## Task 8: Update Celery tasks

**Files:**
- Modify: `backend/app/workers/tasks.py`

- [ ] **Step 1: Replace generate_report task**

In `backend/app/workers/tasks.py`, replace the `generate_report` function (lines 104–249) with:

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_report(self, report_id: str, include_ai: bool = False):
    """
    PDF report generation pipeline.
    1. Load Report + optional PdfTemplate + incident payload
    2. If include_ai and licensed: generate AI summary, inject into payload
    3. render_incident_pdf() → WeasyPrint → PDF bytes
    4. Store via StorageBackend, update Report status, emit WebSocket
    """
    async def _run():
        from datetime import datetime, timezone
        from app.core.database import AsyncSessionLocal
        from app.models.report import Report
        from app.models.pdf_template import PdfTemplate
        from app.models.user import User
        from app.services.report_renderer import render_incident_pdf, build_report_payload
        from app.services.storage.resolver import get_storage_backend
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Report).where(Report.id == report_id))
            report = result.scalar_one_or_none()
            if not report:
                logger.error("generate_report: report %s not found", report_id)
                return

            report.status = "generating"
            await db.commit()

            try:
                result = await db.execute(select(User).where(User.id == report.generated_by))
                analyst = result.scalar_one_or_none()
                if not analyst:
                    result = await db.execute(select(User).where(User.role == "admin").limit(1))
                    analyst = result.scalar_one()

                payload = await build_report_payload(
                    incident_id=str(report.incident_id),
                    analyst=analyst,
                    db=db,
                )

                if include_ai:
                    from app.core.feature_flags import check_feature
                    if check_feature("ai_summaries"):
                        from app.services.ai_service import (
                            get_ai_provider,
                            build_executive_summary_prompt,
                        )
                        provider = get_ai_provider()
                        sys_p, usr_p = build_executive_summary_prompt(payload)
                        payload.ai_executive_summary = await provider.complete(sys_p, usr_p, 400)

                pdf_template = None
                if report.pdf_template_id:
                    pt_result = await db.execute(
                        select(PdfTemplate).where(PdfTemplate.id == report.pdf_template_id)
                    )
                    pdf_template = pt_result.scalar_one_or_none()

                file_bytes = render_incident_pdf(
                    payload=payload,
                    pdf_template=pdf_template,
                    classification=report.classification.upper(),
                )

                backend = get_storage_backend()
                storage_path = f"reports/{report.incident_id}/{report_id}.pdf"
                await backend.store(file_bytes, storage_path)

                report.status = "ready"
                report.storage_path = storage_path
                report.generated_at = datetime.now(timezone.utc)
                await db.commit()

                logger.info(
                    "generate_report: %s completed — %d bytes at %s",
                    report_id, len(file_bytes), storage_path,
                )

                try:
                    _emit_ws(str(report.incident_id), "report:ready", {"report_id": report_id})
                except Exception as ws_err:
                    logger.warning("generate_report: WS emit failed: %s", ws_err)

            except Exception as exc:
                logger.exception("generate_report: failed for %s: %s", report_id, exc)
                report.status = "failed"
                report.error_message = str(exc)[:500]
                await db.commit()
                raise self.retry(exc=exc)

    run_async(_run())
```

- [ ] **Step 2: Update sync_to_sharepoint to use render_incident_pdf**

In `backend/app/workers/tasks.py`, replace the `sync_to_sharepoint` function. Find this block inside `_run()`:

```python
            renderer = ReportRenderer()
            report_bytes = renderer.render(template.schema_json, payload, "pdf")
```

Replace with:

```python
            from app.services.report_renderer import render_incident_pdf
            report_bytes = render_incident_pdf(payload=payload)
```

Also remove the now-unused imports in `sync_to_sharepoint._run()`:
- Remove `from app.models.template import ReportTemplate`
- Remove the block that loads `template` via `policy.report_template_id`
- Remove `from app.services.report_renderer import ReportRenderer, build_report_payload` — change to `from app.services.report_renderer import render_incident_pdf, build_report_payload`

The updated `sync_to_sharepoint._run()` function (complete replacement of the async inner function):

```python
    async def _run():
        import app.plugins  # noqa: F401

        from app.core.database import AsyncSessionLocal
        from app.models.report import SyncPolicy
        from app.models.user import User
        from app.services.report_renderer import render_incident_pdf, build_report_payload
        from app.services.integration_service import decrypt_config
        from app.plugins.registry import PLUGINS
        from sqlalchemy import select
        from datetime import datetime, timezone

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SyncPolicy).where(SyncPolicy.id == policy_id))
            policy = result.scalar_one_or_none()
            if not policy or not policy.is_active:
                logger.info("sync_to_sharepoint: policy %s inactive or missing", policy_id)
                return

            result = await db.execute(select(User).where(User.role == "admin").limit(1))
            analyst = result.scalar_one_or_none()
            if not analyst:
                return

            payload = await build_report_payload(incident_id=incident_id, analyst=analyst, db=db)
            report_bytes = render_incident_pdf(payload=payload)

            pattern = policy.destination_config.get("filename_pattern", "{incident_ref}.pdf")
            try:
                filename = pattern.format(
                    incident_ref=payload.incident.incident_ref,
                    incident_title=payload.incident.title[:50].replace("/", "-"),
                )
            except KeyError:
                filename = f"{payload.incident.incident_ref}.pdf"

            config = decrypt_config(dict(policy.destination_config))
            sp_plugin = PLUGINS.get("sharepoint")
            if not sp_plugin:
                raise RuntimeError("SharePoint plugin not loaded")

            sharepoint_url = await sp_plugin().push_report(report_bytes, filename, config)

            policy.last_synced_at = datetime.now(timezone.utc)
            policy.last_sync_status = "success"
            policy.last_error = None
            await db.commit()

            logger.info("sync_to_sharepoint: incident %s → %s", incident_id, sharepoint_url)

            try:
                _emit_ws(incident_id, "sync:complete", {"policy_id": policy_id, "url": sharepoint_url})
            except Exception:
                pass

            send_notification.delay(
                str(analyst.org_id), "sync.complete",
                {"ref": payload.incident.incident_ref, "url": sharepoint_url}
            )
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/workers/tasks.py
git commit -m "feat(tasks): simplify generate_report to PDF-only, update sync_to_sharepoint"
```

---

## Task 9: PDF templates API + main.py registration

**Files:**
- Create: `backend/app/api/v1/pdf_templates.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create the PDF templates API**

Create `backend/app/api/v1/pdf_templates.py`:

```python
"""
PDF Template endpoints.

GET    /pdf-templates             → list org's templates
POST   /pdf-templates             → upload DOCX template (multipart)
PATCH  /pdf-templates/{id}        → rename
POST   /pdf-templates/{id}/set-default  → set as org default
DELETE /pdf-templates/{id}        → delete
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.schemas.pdf_template import PdfTemplateOut, PdfTemplateRename
from app.services import pdf_template_service

router = APIRouter(tags=["pdf_templates"])

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.get("/pdf-templates")
async def list_pdf_templates(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports.read")),
):
    templates = await pdf_template_service.list_templates(str(current_user.org_id), db)
    return {
        "data": [PdfTemplateOut.model_validate(t) for t in templates],
        "meta": {"total": len(templates)},
        "error": None,
    }


@router.post("/pdf-templates", status_code=201)
async def upload_pdf_template(
    name: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.create")),
):
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are accepted")

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")

    try:
        import io as _io
        from docx import Document
        Document(_io.BytesIO(file_bytes))
    except Exception:
        raise HTTPException(status_code=400, detail="File is not a valid .docx document")

    try:
        t = await pdf_template_service.create_template(
            org_id=str(current_user.org_id),
            name=name,
            file_bytes=file_bytes,
            file_size=len(file_bytes),
            created_by=str(current_user.id),
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {"data": PdfTemplateOut.model_validate(t), "error": None}


@router.patch("/pdf-templates/{template_id}")
async def rename_pdf_template(
    template_id: str,
    body: PdfTemplateRename,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.create")),
):
    t = await pdf_template_service.rename_template(
        template_id, str(current_user.org_id), body.name, db
    )
    return {"data": PdfTemplateOut.model_validate(t), "error": None}


@router.post("/pdf-templates/{template_id}/set-default")
async def set_default_pdf_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.create")),
):
    t = await pdf_template_service.set_default(
        template_id, str(current_user.org_id), db
    )
    return {"data": PdfTemplateOut.model_validate(t), "error": None}


@router.delete("/pdf-templates/{template_id}", status_code=204)
async def delete_pdf_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.delete")),
):
    await pdf_template_service.delete_template(
        template_id, str(current_user.org_id), db
    )
```

- [ ] **Step 2: Register in main.py — swap docx_templates for pdf_templates**

In `backend/app/main.py`:

**Change the import block** (lines 128–152). Replace:
```python
    docx_templates,
```
with:
```python
    pdf_templates,
```

**Change the router registration** (line 183). Replace:
```python
application.include_router(docx_templates.router, prefix=API_PREFIX)
```
with:
```python
application.include_router(pdf_templates.router, prefix=API_PREFIX)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/v1/pdf_templates.py backend/app/main.py
git commit -m "feat(api): add PDF templates API, register router in main.py"
```

---

## Task 10: Update reports.py download endpoint

**Files:**
- Modify: `backend/app/api/v1/reports.py`

- [ ] **Step 1: Hardcode PDF in the download endpoint**

In `backend/app/api/v1/reports.py`, replace the `download_report` function with:

```python
@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports.read")),
):
    from fastapi import HTTPException
    from app.services.storage.resolver import get_storage_backend
    import io

    report = await report_service.get_report(db, report_id)
    if report.status != "ready" or not report.storage_path:
        raise HTTPException(status_code=404, detail="Report not ready or file not found")

    backend = get_storage_backend()
    file_bytes = await backend.retrieve(report.storage_path)
    filename = f"{report.report_type.replace(' ', '_')}_{report_id[:8]}.pdf"

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/v1/reports.py
git commit -m "feat(api): hardcode PDF MIME type in report download endpoint"
```

---

## Task 11: Delete old files

**Files:**
- Delete: `backend/app/services/docx_template_service.py`
- Delete: `backend/app/services/report_renderer/docx_builder.py`
- Delete: `backend/app/api/v1/docx_templates.py`
- Delete: `backend/app/models/docx_template.py`
- Delete: `backend/app/schemas/docx_template.py`

- [ ] **Step 1: Delete the old DOCX system files**

```bash
cd backend
rm app/services/docx_template_service.py
rm app/services/report_renderer/docx_builder.py
rm app/api/v1/docx_templates.py
rm app/models/docx_template.py
rm app/schemas/docx_template.py
```

- [ ] **Step 2: Verify no remaining imports of deleted modules**

```bash
grep -r "docx_template_service\|docx_builder\|DocxTemplate\|DocxTemplateOut\|DocxTemplateRename" app/ --include="*.py"
```

Expected: No output (zero matches).

- [ ] **Step 3: Run the full test suite**

```bash
cd backend
pytest tests/ -v --tb=short
```

Expected: All tests pass. No import errors.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove DOCX template system (placeholder-based pipeline)"
```

---

## Verification Checklist

Run these after all tasks are complete:

```bash
# 1. Migration applied
alembic current  # should show: 008 (head)

# 2. All tests pass
pytest tests/ -v

# 3. Server starts without import errors
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Expected: no ImportError in startup logs

# 4. Upload a DOCX with {{IRDoc_CONTENT}} marker
# POST /api/v1/pdf-templates (multipart)
# Expected: 201, PdfTemplateOut with non-null prefix_html

# 5. Upload a DOCX without the marker
# Expected: 422 with "Template must contain a paragraph with exactly {{IRDoc_CONTENT}}"

# 6. Generate a report with no template
# POST /api/v1/incidents/{id}/reports  {"classification": "confidential"}
# Expected: 202, status transitions pending → generating → ready
# GET /api/v1/reports/{id}/download
# Expected: PDF file downloads with Content-Type: application/pdf

# 7. Generate a report with a template
# Expected: PDF has company pages before/after IRDoc content

# 8. Incident with no IOCs — verify IOC Table absent in downloaded PDF (visual check)

# 9. SharePoint sync still works (check task logs)
```
