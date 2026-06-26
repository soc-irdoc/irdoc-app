# Audit Log

> **Admin role required.**
> **Premium feature** — requires a commercial license key.

The audit log is an append-only record of every significant action taken in IRDoc: who did what, when, and to which resource. Go to **Admin → Audit Log**.

---

## What is logged

- User login and logout
- Incident creation, update, severity/status changes, assignment changes, deletion
- Timeline entry creation and deletion
- IOC creation and deletion
- User invites, role changes, deactivation
- API key creation and revocation
- Storage backend changes
- SSO configuration changes
- Integration tests and enablement/disabling
- High-risk actions: device containment (CrowdStrike), session revocation (Azure AD), MFA resets
- Org settings changes

---

## Filtering the log

| Filter | Options |
|---|---|
| User | Filter by who performed the action |
| Action | e.g. `incident.created`, `user.role_changed`, `api_key.revoked` |
| Entity type | `incident`, `user`, `api_key`, `integration`, `storage`, etc. |
| Incident | Filter to events related to a specific incident |
| Date range | Start and end date/time |

Filters can be combined. Click **Clear** to reset all filters.

---

## Exporting

Click **Export CSV** to download all visible entries (respecting current filters) as a CSV file. Useful for compliance reporting, SIEM ingestion, or external review.

CSV columns: `timestamp`, `user_email`, `user_role`, `action`, `entity_type`, `entity_id`, `incident_ref`, `ip_address`, `details`

---

## Retention

The audit log is retained indefinitely in the current version — there is no automatic rotation. If you need to archive old entries, export them via CSV periodically.

---

## Audit log integrity

The audit log is append-only. Existing entries cannot be modified or deleted through the UI or API. Admin-level direct database access would be required to alter entries.
