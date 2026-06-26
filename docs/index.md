# IRDoc Documentation

**IRDoc** is a self-hostable incident response documentation platform for SOC analysts, IR engineers, and MSSPs. It gives your team a single workspace to capture timelines, track IOCs and assets, assign tasks, and generate reports — all in one place.

---

## Installation

Get IRDoc running on your infrastructure.

- [Installation & Upgrade Wizard](installation/wizard.md) — browser-based guided setup **(recommended)**
- [Docker Compose Setup](installation/docker-compose.md) — manual deployment reference
- [Environment Variables](installation/environment-variables.md) — all `.env` configuration options
- [Upgrading](installation/upgrading.md) — one-command upgrade procedure
- [Backup & Restore](installation/backup-restore.md) — command-line backup and restore
- [Troubleshooting](installation/troubleshooting.md) — common errors and fixes

---

## Product Guide

Everything you need to use and configure IRDoc.

### Using IRDoc

Feature-by-feature guides for analysts and viewers.

- [Creating and Managing Incidents](user-guide/creating-incidents.md) — incident lifecycle, workspace, status, templates
- [Dashboard](user-guide/dashboard.md) — role-based metrics and workload overview
- [Timeline](user-guide/timeline.md) — entries, types, attachments, filters, IOC auto-linking
- [IOC Management](user-guide/ioc-management.md) — add IOCs, bulk import, enrichment, TLP levels
- [Assets](user-guide/assets.md) — track devices and accounts, link to timeline, build asset chains
- [Tasks](user-guide/tasks.md) — checklists, priorities, assignment, progress tracking
- [Investigation Graph](user-guide/investigation-graph.md) — relationship visualization, manual edges
- [Generating Reports](user-guide/generating-reports.md) — generate and download PDF reports
- [Report Template Builder](user-guide/report-template-builder.md) — custom HTML report templates
- [SharePoint Sync](user-guide/sharepoint-sync.md) — auto-deliver reports to SharePoint libraries
- [AI Report Generation](ai/ai-report-generation.md) — AI-powered summaries and recommendations
- [Keyboard Shortcuts](user-guide/keyboard-shortcuts.md) — complete shortcut reference
- [Setting Up MFA](user-guide/mfa-setup.md) — personal TOTP enrollment and backup codes

### Admin Guide

Configuration and management for administrators.

**Organisation**
- [Organisation Settings](admin-guide/org-settings.md) — name, branding, registration policy, license
- [User Management](admin-guide/user-management.md) — roles, invites, deactivation
- [MFA Enforcement](admin-guide/mfa-enforcement.md) — require MFA for all users
- [SSO / OIDC (Entra ID)](admin-guide/sso-saml.md) — single sign-on setup
  - [Entra ID Setup Guide](entra-id-sso-setup.md) — step-by-step Azure AD OIDC walkthrough
- [API Keys](admin-guide/api-keys.md) — keys for webhook integrations and automation

**Infrastructure**
- [Storage Backends](admin-guide/storage-backends.md) — local, S3, Azure Blob, GCS
- [Email / SMTP](admin-guide/smtp.md) — configure outbound email for invites and alerts
- [Backups](admin-guide/backups.md) — scheduled backup management via admin panel
- [Audit Log](admin-guide/audit-log.md) — who did what and when, CSV export

**AI**
- [AI Configuration](admin-guide/ai-configuration.md) — Ollama setup for AI summaries and recommendations

**Integrations**

Configure third-party integrations from **Admin → Integrations**.

| Integration | Category | Plan |
|---|---|---|
| [VirusTotal](admin-guide/integrations/virustotal.md) | Threat Intelligence | Core |
| [AbuseIPDB](admin-guide/integrations/abuseipdb.md) | Threat Intelligence | Core |
| [Microsoft Sentinel](admin-guide/integrations/microsoft-sentinel.md) | SIEM | Premium |
| [CrowdStrike Falcon](admin-guide/integrations/crowdstrike.md) | EDR / Containment | Premium |
| [Slack](admin-guide/integrations/slack.md) | Notifications | Core |
| [Microsoft Teams](admin-guide/integrations/microsoft-teams.md) | Notifications | Core |
| [ServiceDesk Plus](admin-guide/integrations/servicedesk-plus.md) | ITSM | Core |
| SharePoint | Storage / Sync | Premium |

---

## Developers

Build automations and integrations on top of IRDoc.

- [API Developer Guide](api/developer-guide.md) — authentication, response format, full endpoint reference with examples
- [REST API Reference](api/reference.md) — live Swagger UI at `/api/docs` on your instance
- [Development Setup](contributing/development-setup.md) — run IRDoc locally from source
- [Architecture Overview](contributing/architecture.md) — how the backend, worker, and frontend fit together
- [Adding Integrations](contributing/adding-integrations.md) — build a new integration plugin

---

## Changelog

- [Changelog](changelog.md)
