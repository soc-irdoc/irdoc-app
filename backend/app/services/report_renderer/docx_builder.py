"""
DOCX report builder (premium).

Builds a python-docx document from the ReportPayload and report schema.
Intentionally straightforward — structured content over perfect styling.
"""
from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.report_renderer.payload import ReportPayload

logger = logging.getLogger(__name__)


class DocxBuilder:
    def build(self, payload: "ReportPayload", schema: list[dict]) -> bytes:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()

        # Set narrow margins
        from docx.shared import Inches
        for section in doc.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1.2)
            section.right_margin = Inches(1.2)

        for block in schema:
            block_type = block.get("type", "text_block")
            try:
                self._render_block(doc, block_type, block, payload)
            except Exception as exc:
                logger.warning("DOCX block render failed (%s): %s", block_type, exc)
                doc.add_paragraph(f"[Block render error: {block_type}]")

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def _render_block(self, doc, block_type: str, block: dict, payload: "ReportPayload"):
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        if block_type == "cover":
            p = doc.add_heading(payload.incident.title, level=1)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_paragraph(f"Incident Reference: {payload.incident.incident_ref}")
            doc.add_paragraph(f"Severity: {payload.severity_label}")
            doc.add_paragraph(f"Status: {payload.status_label}")
            if block.get("watermark"):
                wp = doc.add_paragraph(block["watermark"])
                wp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_paragraph(f"Generated: {payload.generated_at.strftime('%Y-%m-%d %H:%M UTC')}")
            doc.add_paragraph(f"Analyst: {payload.analyst.full_name}")
            doc.add_page_break()

        elif block_type == "section":
            label = block.get("label", "Section")
            doc.add_heading(label, level=2)
            field_path = block.get("field", "")
            value = self._resolve_field(field_path, payload)
            if isinstance(value, list):
                for item in value:
                    doc.add_paragraph(str(item), style="List Bullet")
            else:
                doc.add_paragraph(str(value) if value else "No data.")

        elif block_type == "header":
            doc.add_heading(block.get("text", ""), level=2)

        elif block_type == "text_block":
            label = block.get("label", "")
            if label:
                doc.add_heading(label, level=2)
            field_path = block.get("field", "")
            value = self._resolve_field(field_path, payload)
            doc.add_paragraph(str(value) if value else "No data.")

        elif block_type == "stat_row":
            doc.add_heading("Summary", level=2)
            stats = block.get("stats", [])
            for stat in stats:
                val = self._get_stat(stat, payload)
                doc.add_paragraph(f"{stat.replace('_', ' ').title()}: {val}")

        elif block_type == "timeline":
            label = block.get("label", "Timeline")
            doc.add_heading(label, level=2)
            filter_val = block.get("filter", "all")
            entries = self._filter_entries(filter_val, payload)
            max_entries = block.get("max_entries", 0)
            if max_entries:
                entries = entries[:max_entries]
            if not entries:
                doc.add_paragraph("No timeline entries.")
            for e in entries:
                ts = e.occurred_at.strftime("%Y-%m-%d %H:%M") if e.occurred_at else ""
                doc.add_paragraph(f"[{e.entry_type.upper()}] {ts} — {e.description}")

        elif block_type == "ioc_table":
            label = block.get("label", "Indicators of Compromise")
            doc.add_heading(label, level=2)
            iocs = self._filter_iocs(block.get("filter", "all"), payload)
            if not iocs:
                doc.add_paragraph("No IOCs.")
            else:
                cols = block.get("columns", ["type", "value", "status"])
                table = doc.add_table(rows=1, cols=len(cols))
                table.style = "Table Grid"
                hdr = table.rows[0].cells
                for i, col in enumerate(cols):
                    hdr[i].text = col.title()
                for ioc in iocs:
                    row = table.add_row().cells
                    for i, col in enumerate(cols):
                        row[i].text = str(getattr(ioc, col, "—") or "—")

        elif block_type == "task_list":
            label = block.get("label", "Response Tasks")
            doc.add_heading(label, level=2)
            tasks = self._filter_tasks(block, payload)
            if not tasks:
                doc.add_paragraph("No tasks.")
            for t in tasks:
                status_sym = "✓" if t.status == "done" else "○"
                doc.add_paragraph(f"{status_sym} {t.title} [{t.phase or 'General'}]")

        elif block_type == "evidence_register":
            label = block.get("label", "Evidence Register")
            doc.add_heading(label, level=2)
            if not payload.attachments:
                doc.add_paragraph("No evidence uploaded.")
            else:
                table = doc.add_table(rows=1, cols=3)
                table.style = "Table Grid"
                hdr = table.rows[0].cells
                hdr[0].text = "Filename"
                hdr[1].text = "Size"
                hdr[2].text = "SHA-256"
                for att in payload.attachments:
                    row = table.add_row().cells
                    row[0].text = att.original_name
                    row[1].text = self._fmt_size(att.file_size)
                    row[2].text = att.sha256[:16] + "…" if att.sha256 else "—"

        elif block_type == "tag_list":
            label = block.get("label", "Tags")
            doc.add_heading(label, level=2)
            field_path = block.get("field", "")
            value = self._resolve_field(field_path, payload)
            if isinstance(value, list):
                doc.add_paragraph(", ".join(str(v) for v in value))
            else:
                doc.add_paragraph(str(value) if value else "—")

        elif block_type == "divider":
            doc.add_paragraph("─" * 60)

        elif block_type == "page_break":
            doc.add_page_break()

    def _resolve_field(self, path: str, payload: "ReportPayload"):
        parts = path.split(".")
        obj = payload
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif hasattr(obj, "metadata_") and part == "metadata":
                obj = obj.metadata_
            elif isinstance(obj, dict):
                obj = obj.get(part)
            else:
                return None
        return obj

    def _get_stat(self, stat: str, payload: "ReportPayload") -> str:
        mapping = {
            "severity": payload.severity_label,
            "status": payload.status_label,
            "duration": payload.duration_str,
            "affected_users": str(payload.incident.affected_users),
            "ioc_count": str(payload.ioc_count),
            "entry_count": str(payload.entry_count),
            "opened_at": payload.incident.opened_at.strftime("%Y-%m-%d %H:%M UTC") if payload.incident.opened_at else "—",
            "contained_at": payload.contained_at_str or "—",
            "closed_at": payload.closed_at_str or "—",
        }
        return mapping.get(stat, "—")

    def _filter_entries(self, filter_val: str, payload: "ReportPayload"):
        if filter_val == "all" or not filter_val:
            return payload.entries
        if filter_val.startswith("type="):
            t = filter_val.split("=", 1)[1]
            return payload.entries_by_type.get(t, [])
        return payload.entries

    def _filter_iocs(self, filter_val: str, payload: "ReportPayload"):
        if filter_val == "all" or not filter_val:
            return payload.iocs
        if filter_val.startswith("status="):
            s = filter_val.split("=", 1)[1]
            return payload.iocs_by_status.get(s, [])
        return payload.iocs

    def _filter_tasks(self, block: dict, payload: "ReportPayload"):
        tasks = payload.tasks
        phase_filter = block.get("filter", "")
        if phase_filter.startswith("phase="):
            phase = phase_filter.split("=", 1)[1]
            tasks = payload.tasks_by_phase.get(phase, [])
        if not block.get("show_completed", True):
            tasks = [t for t in tasks if t.status != "done"]
        return tasks

    def _fmt_size(self, size: int | None) -> str:
        if size is None:
            return "—"
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
