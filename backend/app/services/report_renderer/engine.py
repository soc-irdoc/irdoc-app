"""
Report rendering engine.

render_incident_pdf() is the single entry point for PDF generation.
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
