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


def render_from_schema(
    payload: "ReportPayload",
    schema_json: list[dict],
    brand: dict,
    classification: str = "CONFIDENTIAL",
    env: jinja2.Environment | None = None,
) -> str:
    """Render a report from a ReportTemplate's schema_json block list.

    Iterates blocks in order; unknown block types are skipped with a warning.
    brand dict: {logo_data_uri, primary_colour, company_name}
    """
    from app.services.report_renderer.engine import _build_jinja_env

    jinja_env = env or _build_jinja_env()

    rendered_blocks: list[str] = []
    for block_config in schema_json:
        block_type = block_config.get("type")
        if not block_type:
            continue
        try:
            partial = jinja_env.get_template(f"reports/blocks/{block_type}.html")
            rendered_blocks.append(partial.render(block=block_config, p=payload, brand=brand))
        except jinja2.TemplateNotFound:
            logger.warning("render_from_schema: unknown block type '%s' — skipped", block_type)

    base = jinja_env.get_template("reports/base.html")
    return base.render(
        blocks=rendered_blocks,
        incident=payload.incident,
        classification=classification,
        generated_at=payload.generated_at,
        analyst=payload.analyst,
        p=payload,
        brand=brand,
        prefix_html="",
        suffix_html="",
        page_css="",
    )


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
    from app.services.report_renderer.engine import _build_jinja_env

    jinja_env = env or _build_jinja_env()

    rendered_blocks: list[str] = []
    for section in _FIXED_SECTIONS:
        if not section["has_data"](payload):
            continue
        block_config = section["block"](payload, classification)
        block_type = block_config["type"]
        partial = jinja_env.get_template(f"reports/blocks/{block_type}.html")
        rendered_blocks.append(partial.render(block=block_config, p=payload, brand={}))

    base = jinja_env.get_template("reports/base.html")
    return base.render(
        blocks=rendered_blocks,
        incident=payload.incident,
        classification=classification,
        generated_at=payload.generated_at,
        analyst=payload.analyst,
        p=payload,
        brand={},
        prefix_html=prefix_html,
        suffix_html=suffix_html,
        page_css=page_css,
    )
