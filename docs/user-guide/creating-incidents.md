# Creating and Managing Incidents

An incident in IRDoc is a record of a security event under investigation. Each incident is automatically assigned a unique reference number in the format **INC-YYYY-NNNN** (e.g. INC-2026-0042). The incident workspace organises all related evidence, tasks, and findings in one place.

---

## Creating an Incident

> **Analyst role or higher required.**

From the incidents list, click **New Incident** or press `C` from anywhere in IRDoc.

Fill in the creation form:

| Field | Description |
|---|---|
| Title | Short descriptive name for the incident. Required. |
| Severity | sev1 (critical), sev2 (high), sev3 (medium), sev4 (low). Defaults to sev2. |
| Assign to | Optionally assign the incident to a user immediately. |
| Template | Optionally choose a template to pre-populate a standard task checklist. |

After submitting, you land in the incident workspace with the reference number assigned.

---

## Incident Workspace

The workspace is divided into tabs:

| Tab | Contents |
|---|---|
| Timeline | Chronological log of events during the incident |
| IOCs | Indicators of compromise (IPs, domains, hashes, etc.) |
| Assets | Infrastructure, accounts, and services involved |
| Tasks | Checklist of action items |
| Summary | Rich-text fields: Executive Summary, Notes, Lessons Learned, Actions TODO |
| Reports | Generated reports for this incident |
| Graph | Visual investigation graph linking IOCs, assets, and timeline entries |

---

## Updating Incident Details

**From the incident header** (always visible at the top of the workspace):

- Change **severity** by clicking the severity badge
- Change **status** by clicking the status badge
- Change **assignment** by clicking the assignee field
- Add **external references** — links to tickets in other systems (see below)

**From the Summary tab:**

| Field | Description |
|---|---|
| Executive Summary | High-level narrative for leadership. Rich text. |
| Notes | Working notes during investigation. Rich text. |
| Lessons Learned | Post-incident learnings. Rich text. |
| Actions TODO | Follow-up items after closure. Rich text. |
| Attack vector tags | Tags describing how the attack occurred (e.g. `phishing`, `credential_stuffing`). Multiple allowed. |
| Affected users count | Number of user accounts impacted. |

---

## Status Lifecycle

Incidents move through the following statuses:

```
open → contained → closed
open → monitoring → closed
```

- **open** — active investigation in progress
- **contained** — threat is contained but not fully resolved
- **monitoring** — resolved but under observation
- **closed** — investigation complete

> **Senior Analyst role or higher required** to move an incident to **closed**.

---

## External References

Link incidents to tickets in external systems (Jira, ServiceDesk Plus, etc.) from the incident header.

1. Click **Add Reference** in the incident header
2. Fill in the fields:

| Field | Description |
|---|---|
| Source | Label for the external system (e.g. `Jira`, `ServiceDesk Plus`) |
| Ticket ID | The ticket or issue identifier in that system |
| URL | Optional direct link to the ticket |

3. Click **Save**

References appear in the header as clickable chips. Multiple references can be added to one incident.

---

## Incident Templates

Templates pre-populate a new incident with a standard task checklist so teams follow a consistent process.

- Choose a template in the **Template** field when creating an incident
- The template's tasks are added to the Tasks tab automatically
- Tasks added by a template can be edited or deleted after the incident is created
- Templates are managed by administrators at **Admin → Templates**

---

## Deleting an Incident

> **Senior Analyst role or higher required.**

Deletion is permanent and removes all associated data: timeline entries, IOCs, tasks, assets, and attachments.

1. Open the incident
2. Click the **⋯** menu in the incident header
3. Select **Delete Incident**
4. Confirm when prompted

There is no recovery from deletion. Export or archive the incident before deleting if a record is needed.
