# Generating Reports

---

## Quick Generate

1. Open an incident and click the **Reports** tab (or click **Report** in the top bar)
2. Click **Generate Report**
3. Select a template (Management Brief, Technical Report, Legal/Compliance, or a custom org template)
4. Select the export format: **Markdown**, **HTML**, **PDF**, or **DOCX**
5. Optionally set a classification label (e.g., TLP:AMBER, CONFIDENTIAL)
6. Toggle **Include AI Summary** if you have an AI backend configured
7. Click **Generate**

Report generation runs asynchronously. A progress indicator appears and the report is listed once ready. Large reports with many timeline entries typically complete in under 10 seconds.

---

## Downloading

Click **Download** on any ready report in the Reports tab.

Reports are stored via your configured storage backend (local or cloud) and served via signed URLs that expire after 1 hour. Re-click Download to get a fresh link.

---

## Templates

IRDoc ships three **system templates** that are available to all orgs:

| Template | Audience | Contents |
|---|---|---|
| Management Brief | Executives | Cover, executive summary, stat row, timeline highlights, recommendations |
| Technical Report | Analysts | Full timeline, IOC table, evidence register, task summary |
| Legal/Compliance | Legal/Compliance | Cover, incident overview, timeline, IOC table, evidence register, audit trail |

System templates cannot be edited. To customize, click **Clone** and edit your copy.

See [Report Template Builder](report-template-builder.md) for building custom templates.

---

## SharePoint Auto-Sync

Once a sync policy is configured (Reports tab → Sync Policies), IRDoc automatically re-uploads the report to SharePoint after every significant change to the incident, debounced to avoid flooding.

See [SharePoint Sync](sharepoint-sync.md).

---

## Formats

| Format | Notes |
|---|---|
| **Markdown** | Plain text, renderable in GitHub, Confluence, etc. |
| **HTML** | Inline-styled, suitable for email or web view. |
| **PDF** | Print-ready, WeasyPrint-rendered. |
| **DOCX** | Microsoft Word format. |
