# Timeline

The timeline is the heart of an IRDoc incident workspace. Every significant event in the incident is recorded as a timeline entry — in chronological order, with the most recent at the top.

---

## Entry Types

| Type | When to use |
|---|---|
| **Detection** | When the incident was first identified (alert fired, user report, etc.) |
| **Analysis** | Findings from log review, malware analysis, forensic examination |
| **Containment** | Actions taken to isolate affected systems or block attacker access |
| **Evidence** | Artifact collection, screenshots, memory dumps |
| **Comms** | Stakeholder notifications, legal/HR/exec communications |
| **Note** | General notes, status updates, anything that doesn't fit above |

---

## Adding an Entry

1. Click in the **Add Entry** text area at the top of the timeline (or press `N`)
2. Select the entry type from the dropdown
3. Adjust the **occurred at** timestamp if needed (defaults to now)
4. Write your description
5. Attach files if needed (see below)
6. Click **Add Entry** or press `Ctrl+Enter`

Entries appear instantly via optimistic update and sync to all connected analysts in real time.

---

## Attachments

### Drag and drop
Drag files from your desktop directly onto the attachment zone below the text area.

### Paste screenshots
Press `Ctrl+V` (or `Cmd+V`) anywhere on the page — not just in a file input — to paste an image from your clipboard. This is the fastest way to capture a screenshot from an active investigation.

### Limits
- Maximum file size: 50MB per file
- All file types accepted; MIME type is validated on upload
- SHA-256 is computed and stored for every file (forensic integrity)

---

## Filters

Use the filter bar above the timeline to narrow entries:
- **Entry type** — show only detection events, containment actions, etc.
- **Date range** — focus on a specific time window
- **Author** — see only your own entries or a specific analyst's entries

---

## Pinning Entries

Senior Analysts and Admins can pin critical entries. Pinned entries appear with a visual indicator and are always included in generated reports.

To pin: hover over an entry and click the pin icon.

---

## Exporting

The timeline can be exported as CSV from the timeline filter bar. This exports all visible entries (respects current filters).

---

## IOC Auto-Linking

When you add a timeline entry, the backend scans the description for IOC patterns (IPs, domains, hashes, emails, URLs). Any matches are automatically linked to existing IOCs in the incident if the values match.

These links appear in the Investigation Graph as edges between timeline entries and IOC nodes.

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `N` | Focus the Add Entry text area |
| `Escape` | Close any open modal |
| `Ctrl+Enter` | Submit the current entry form |
