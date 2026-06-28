#!/usr/bin/env node
const fs   = require('fs');
const path = require('path');

const DOCS_ROOT = path.join(__dirname, '..', 'docs');
const OUTPUT    = path.join(__dirname, 'docs-content.json');

const MANIFEST = [
  { section: 'Installation', items: [
    { path: 'installation/wizard',                title: 'Installation & Upgrade Wizard' },
    { path: 'installation/docker-compose',        title: 'Docker Compose Setup' },
    { path: 'installation/environment-variables', title: 'Environment Variables' },
    { path: 'installation/upgrading',             title: 'Upgrading' },
    { path: 'installation/backup-restore',        title: 'Backup & Restore' },
    { path: 'installation/troubleshooting',       title: 'Troubleshooting' },
  ]},
  { section: 'User Guide', items: [
    { path: 'user-guide/creating-incidents',      title: 'Creating and Managing Incidents' },
    { path: 'user-guide/dashboard',               title: 'Dashboard' },
    { path: 'user-guide/timeline',                title: 'Timeline' },
    { path: 'user-guide/ioc-management',          title: 'IOC Management' },
    { path: 'user-guide/assets',                  title: 'Assets' },
    { path: 'user-guide/tasks',                   title: 'Tasks' },
    { path: 'user-guide/investigation-graph',     title: 'Investigation Graph' },
    { path: 'user-guide/generating-reports',      title: 'Generating Reports' },
    { path: 'user-guide/report-template-builder', title: 'Report Template Builder' },
    { path: 'user-guide/sharepoint-sync',         title: 'SharePoint Sync' },
    { path: 'ai/ai-report-generation',            title: 'AI Report Generation' },
    { path: 'user-guide/keyboard-shortcuts',      title: 'Keyboard Shortcuts' },
    { path: 'user-guide/mfa-setup',               title: 'Setting Up MFA' },
  ]},
  { section: 'Admin Guide', items: [
    { path: 'admin-guide/org-settings',                      title: 'Organisation Settings' },
    { path: 'admin-guide/user-management',                   title: 'User Management' },
    { path: 'admin-guide/mfa-enforcement',                   title: 'MFA Enforcement' },
    { path: 'admin-guide/sso-saml',                          title: 'SSO / OIDC (Entra ID)' },
    { path: 'entra-id-sso-setup',                            title: 'Entra ID Setup Guide' },
    { path: 'admin-guide/api-keys',                          title: 'API Keys' },
    { path: 'admin-guide/storage-backends',                  title: 'Storage Backends' },
    { path: 'admin-guide/smtp',                              title: 'Email / SMTP' },
    { path: 'admin-guide/backups',                           title: 'Backups' },
    { path: 'admin-guide/audit-log',                         title: 'Audit Log' },
    { path: 'admin-guide/ai-configuration',                  title: 'AI Configuration' },
    { path: 'admin-guide/integrations/virustotal',           title: 'VirusTotal' },
    { path: 'admin-guide/integrations/abuseipdb',            title: 'AbuseIPDB' },
    { path: 'admin-guide/integrations/microsoft-sentinel',   title: 'Microsoft Sentinel' },
    { path: 'admin-guide/integrations/crowdstrike',          title: 'CrowdStrike Falcon' },
    { path: 'admin-guide/integrations/slack',                title: 'Slack' },
    { path: 'admin-guide/integrations/microsoft-teams',      title: 'Microsoft Teams' },
    { path: 'admin-guide/integrations/servicedesk-plus',     title: 'ServiceDesk Plus' },
  ]},
  { section: 'Developers', items: [
    { path: 'api/developer-guide',               title: 'API Developer Guide' },
    { path: 'api/reference',                     title: 'REST API Reference' },
    { path: 'contributing/development-setup',    title: 'Development Setup' },
    { path: 'contributing/architecture',         title: 'Architecture Overview' },
    { path: 'contributing/adding-integrations',  title: 'Adding Integrations' },
  ]},
  { section: 'Changelog', items: [
    { path: 'changelog', title: 'Changelog' },
  ]},
];

const docs = {};
let missing = 0;

for (const { section, items } of MANIFEST) {
  for (const { path: docPath, title } of items) {
    const filePath = path.join(DOCS_ROOT, docPath + '.md');
    if (!fs.existsSync(filePath)) {
      console.warn(`MISSING: ${filePath}`);
      missing++;
      continue;
    }
    docs[docPath] = { title, section, content: fs.readFileSync(filePath, 'utf8') };
  }
}

fs.writeFileSync(OUTPUT, JSON.stringify({ version: '1', generated: new Date().toISOString(), docs }, null, 2));
console.log(`Generated docs-content.json — ${Object.keys(docs).length} docs, ${missing} missing`);
