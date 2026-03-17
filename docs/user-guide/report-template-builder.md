# Report Template Builder

The report template builder lets you compose custom report layouts by arranging blocks in a drag-and-drop canvas. Each block maps to a section of the generated document.

> **Premium feature** — requires a commercial license key.

---

## Opening the Builder

- **Admin → Incident Templates** — manage incident task templates
- **Admin → Report Templates** (or navigate to `/report-templates`) — manage report templates
- Click **New Template** or **Clone** an existing template, then click **Edit**

---

## Block Types

| Block | Description |
|---|---|
| `cover` | Title page with incident ref, severity, dates, and classification label |
| `section` | Heading + optional body text paragraph |
| `stat_row` | Row of stat cards (e.g., Duration, IOC Count, Affected Users) |
| `timeline` | Filtered timeline entries (configurable: all types, pinned only, by date range) |
| `ioc_table` | Table of IOCs with type, value, confidence, status, and enrichment summary |
| `task_list` | Task completion status grouped by phase |
| `evidence_register` | Table of attachments with filename, size, SHA-256, and uploader |
| `text_block` | Free-form Markdown text (use for static sections like legal disclaimers) |
| `divider` | Horizontal rule |
| `page_break` | Forces a new page in PDF/DOCX output |
| `header` | Running header text (appears at top of each page in PDF) |
| `tag_list` | Attack vector and tag chips |

---

## Building a Layout

1. Drag blocks from the **Block Library** panel on the right into the canvas
2. Reorder blocks by dragging them within the canvas
3. Click a block to open its **configuration panel** (title, filters, options)
4. Click **Save Template**

---

## Previewing

Click **Preview** to generate a Markdown preview using current incident data. This is a fast way to check layout before generating a formal report.

---

## Template Settings

| Setting | Description |
|---|---|
| **Name** | Template name shown in the Generate Report dialog |
| **Destination** | `management`, `analyst`, `legal`, or `custom` — used for labelling |
| **Default** | If set, this template is pre-selected in the Generate Report dialog |

---

## Sharing Templates

Templates belong to your organisation. All members can use them; only Senior Analysts and Admins can edit or delete them.

System templates (shipped with IRDoc) are read-only — clone them to create an editable copy.
