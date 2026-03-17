# IRDoc Documentation

**IRDoc** is a self-hostable, open-core incident response documentation platform for SOC analysts, IR engineers, and MSSPs.

---

## Quick Start (5 minutes)

```bash
git clone https://github.com/irpdoc/irpdoc
cd irpdoc && cp .env.example .env
# Edit .env: set DB_PASSWORD, REDIS_PASSWORD, SECRET_KEY
cd docker && docker compose up
```

Open **http://localhost:3000** — complete the first-run setup to create your admin account.

---

## Documentation Sections

### Installation
- [Docker Compose Setup](installation/docker-compose.md) — standard self-hosted deployment
- [Environment Variables](installation/environment-variables.md) — all `.env` options explained
- [Upgrading](installation/upgrading.md) — one-command upgrade procedure
- [Backup & Restore](installation/backup-restore.md) — database and file backup
- [Troubleshooting](installation/troubleshooting.md) — common errors and fixes

### User Guide
- [Creating Incidents](user-guide/creating-incidents.md)
- [Timeline](user-guide/timeline.md) — entries, screenshots, attachments
- [IOC Management](user-guide/ioc-management.md) — add IOCs, enrichment, bulk import
- [Report Template Builder](user-guide/report-template-builder.md) — visual block editor
- [Generating Reports](user-guide/generating-reports.md)
- [SharePoint Sync](user-guide/sharepoint-sync.md) — auto-sync setup
- [Tasks & Templates](user-guide/tasks-and-templates.md)
- [Keyboard Shortcuts](user-guide/keyboard-shortcuts.md)

### Admin Guide
- [User Management](admin-guide/user-management.md) — invites, roles, SSO
- [Storage Backends](admin-guide/storage-backends.md) — S3, Azure Blob, GCS
- [API Keys](admin-guide/api-keys.md) — creating keys for service desk integrations
- [SSO / SAML](admin-guide/sso-saml.md) — Okta, Azure AD, Google Workspace
- [Licensing](admin-guide/licensing.md) — core vs premium
- Integrations:
  - [VirusTotal](admin-guide/integrations/virustotal.md)
  - [Microsoft Sentinel](admin-guide/integrations/sentinel.md)
  - [CrowdStrike](admin-guide/integrations/crowdstrike.md)
  - [SharePoint](admin-guide/integrations/sharepoint.md)
  - [Slack](admin-guide/integrations/slack.md)
  - [ServiceDesk Plus](admin-guide/integrations/servicedesk-plus.md)

### API Reference
- [REST API Reference](api/reference.md) — links to auto-generated OpenAPI docs

### Contributing
- [Development Setup](contributing/development-setup.md)
- [Architecture Overview](contributing/architecture.md)
- [Adding Integrations](contributing/adding-integrations.md)

### [Changelog](changelog.md)
