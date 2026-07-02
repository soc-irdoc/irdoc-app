# SharePoint Auto-Sync

IRDoc can automatically push a report to a SharePoint document library whenever the incident changes. Management always has a current document — no manual effort.

---

## How it works

1. You configure a **Sync Policy** on an incident: which report template to use, which SharePoint library to push to, and a debounce window (default 60 seconds).
2. On every significant change (new timeline entry, IOC update, task completion), IRDoc sets a Redis TTL key.
3. If another change arrives within the debounce window, the TTL resets — preventing a flood of uploads during active investigation.
4. When the TTL expires with no further changes, a Celery task renders the report and uploads it to SharePoint.
5. A `sync:complete` WebSocket event notifies connected analysts with the document URL.

---

## Setup

### 1. Configure the SharePoint integration

Go to **Admin → Integrations → SharePoint** and enter your SharePoint credentials:
- **Tenant ID** — your Azure AD tenant ID
- **Client ID** — an Azure AD app registration with Sites.ReadWrite.All permission
- **Client Secret** — the app registration client secret
- **Site URL** — e.g. `https://yourcompany.sharepoint.com/sites/SOC`

Click **Test Connection** to verify. Click **Save**.

### 2. Create a Sync Policy on an incident

1. Open an incident and go to the **Reports** tab
2. Scroll to **Sync Policies** and click **+ Add Policy**
3. Select the report template to use (e.g., Management Brief)
4. Enter the SharePoint document library path (e.g., `/Shared Documents/Incident Reports/`)
5. Set the debounce window (default 60s — increase for fast-moving incidents)
6. Click **Save**

The policy is now active. The next change to the incident will trigger a sync after the debounce window.

### 3. Manual sync

Click **Trigger Sync** on any policy to push immediately without waiting for the debounce window.

---

## Document naming

Synced documents are named using the incident reference: `INC-2026-0042 - Technical Report.pdf`

If a document with that name already exists in the library, it is overwritten (versioning is handled by SharePoint's built-in version history).

---

## Troubleshooting

**Sync not triggering:**
- Check that Redis `notify-keyspace-events Ex` is enabled (`redis-cli config get notify-keyspace-events`)
- Check the Celery worker logs: `docker compose logs worker`

**Authentication errors:**
- Verify the Azure AD app has `Sites.ReadWrite.All` application permission (not delegated)
- Ensure admin consent has been granted in the Azure portal

**Document not appearing in the library:**
- Check the library path matches exactly (case-sensitive)
- Verify the app registration has access to the specific site
