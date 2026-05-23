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
