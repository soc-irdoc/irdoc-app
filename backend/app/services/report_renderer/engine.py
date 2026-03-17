"""
ReportRenderer — iterates a report template's schema_json, renders each
block as a Jinja2 partial, assembles them under base.html, then converts
to the requested format (html | markdown | pdf | docx).
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

import jinja2

if TYPE_CHECKING:
    from app.services.report_renderer.payload import ReportPayload

logger = logging.getLogger(__name__)

# Jinja2 template directory — backend/templates/
_TEMPLATE_DIR = Path(__file__).parent.parent.parent.parent / "templates"


def _build_jinja_env() -> jinja2.Environment:
    loader = jinja2.FileSystemLoader(str(_TEMPLATE_DIR))
    env = jinja2.Environment(
        loader=loader,
        autoescape=jinja2.select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Convenience filters
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


def _html_to_markdown(html: str) -> str:
    """Very lightweight HTML → Markdown conversion for the markdown export path."""
    # Remove style blocks
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
    # Headings
    for n in range(6, 0, -1):
        html = re.sub(rf"<h{n}[^>]*>(.*?)</h{n}>", r"#" * n + r" \1\n", html, flags=re.DOTALL)
    # Bold / italic
    html = re.sub(r"<(strong|b)[^>]*>(.*?)</(strong|b)>", r"**\2**", html, flags=re.DOTALL)
    html = re.sub(r"<(em|i)[^>]*>(.*?)</(em|i)>", r"*\2*", html, flags=re.DOTALL)
    # Table rows → pipe-separated
    html = re.sub(r"<tr[^>]*>", "", html)
    html = re.sub(r"</tr>", "\n", html)
    html = re.sub(r"<t[dh][^>]*>(.*?)</t[dh]>", r"| \1 ", html, flags=re.DOTALL)
    # Lists
    html = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", html, flags=re.DOTALL)
    # Paragraphs and breaks
    html = re.sub(r"<br\s*/?>", "\n", html)
    html = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", html, flags=re.DOTALL)
    html = re.sub(r"<div[^>]*>(.*?)</div>", r"\1\n", html, flags=re.DOTALL)
    # Strip remaining tags
    html = re.sub(r"<[^>]+>", "", html)
    # Decode entities
    html = html.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&nbsp;", " ")
    # Normalise whitespace
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


class ReportRenderer:
    def __init__(self, env: jinja2.Environment | None = None):
        self.env = env or _jinja_env

    def render_to_html(self, schema: list[dict], payload: "ReportPayload") -> str:
        """Render the full report as an HTML string."""
        rendered_blocks: list[str] = []
        for block in schema:
            block_type = block.get("type", "text_block")
            try:
                partial = self.env.get_template(f"reports/blocks/{block_type}.html")
                rendered_blocks.append(partial.render(block=block, p=payload))
            except jinja2.TemplateNotFound:
                logger.warning("Report block template not found: %s", block_type)
                rendered_blocks.append(
                    f'<div class="block-error">Unknown block type: {block_type}</div>'
                )

        base = self.env.get_template("reports/base.html")
        classification = ""
        if isinstance(payload.incident.metadata_, dict):
            classification = payload.incident.metadata_.get("classification", "CONFIDENTIAL")

        return base.render(
            blocks=rendered_blocks,
            incident=payload.incident,
            classification=classification or "CONFIDENTIAL",
            generated_at=payload.generated_at,
            analyst=payload.analyst,
            p=payload,
        )

    def render(self, schema: list[dict], payload: "ReportPayload", fmt: str) -> bytes:
        html = self.render_to_html(schema, payload)

        if fmt == "html":
            return html.encode("utf-8")

        elif fmt == "markdown":
            return _html_to_markdown(html).encode("utf-8")

        elif fmt == "pdf":
            from app.core.feature_flags import check_feature
            if not check_feature("report_pdf_export"):
                raise PermissionError("PDF export requires a premium license")
            try:
                from weasyprint import HTML as WeasyHTML
                pdf_bytes = WeasyHTML(
                    string=html,
                    base_url=str(_TEMPLATE_DIR / "reports"),
                ).write_pdf()
                return pdf_bytes
            except Exception as exc:
                logger.error("WeasyPrint PDF render failed: %s", exc)
                raise

        elif fmt == "docx":
            from app.core.feature_flags import check_feature
            if not check_feature("report_docx_export"):
                raise PermissionError("DOCX export requires a premium license")
            from app.services.report_renderer.docx_builder import DocxBuilder
            return DocxBuilder().build(payload, schema)

        else:
            raise ValueError(f"Unsupported report format: {fmt}")
