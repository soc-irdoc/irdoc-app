# Dashboard

The dashboard is the landing page after login. It shows a summary of incident activity and operational metrics relevant to your role. All counts respond to the **time range selector** in the top-right corner (default: last 7 days). Clicking any incident card or metric navigates to the filtered incidents list.

---

## All Roles

Every role sees:

- **Incidents by status** — count of open, contained, monitoring, and closed incidents
- **Incidents by severity** — count of sev1, sev2, sev3, sev4 incidents

---

## Viewer

In addition to the shared counts:

- **Top 5 attack vectors** — the most frequently tagged attack vectors across all incidents in the selected time range

---

## Analyst

In addition to the shared counts:

- **My open assigned cases** — incidents assigned to you with status open, contained, or monitoring
- **My pending tasks** — tasks assigned to you with status open or in_progress
- **My recent task activity** — a feed of task completions and updates you made recently

---

## Senior Analyst

> **Senior Analyst role or higher required** to see these panels.

In addition to the shared counts:

- **Incidents I lead** — incidents assigned to you as the lead investigator
- **Unassigned incidents** — count of open incidents with no assignee, for triage purposes

---

## Admin

> **Admin role required** to see these panels.

Admins see everything above, plus:

**Org health panel:**

| Metric | Description |
|---|---|
| Active users | Number of users who have logged in during the selected period |
| MFA enrollment rate | Percentage of active users with MFA enabled |
| Pending invites | Number of sent invitations not yet accepted |
| Configured integrations | Number of active external integrations |

**Recent audit log entries** — the 5 most recent entries from the audit log. Click **View all** to go to the full audit log at **Admin → Audit Log**.

**Team workload** — a table showing each analyst and how many open incidents they currently have assigned.

**Resolved incidents** — count of incidents moved to closed status within the selected time range.
