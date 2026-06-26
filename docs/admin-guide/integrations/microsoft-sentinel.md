# Microsoft Sentinel

> **Premium feature** — requires a commercial license key.

> **Admin role required** to configure. **Analyst role or higher** to use.

Pulls security alerts from Microsoft Sentinel directly into an IRDoc incident as timeline entries, and allows running custom KQL queries against your Sentinel workspace from within the incident.

---

## Prerequisites

- An Azure subscription with Microsoft Sentinel enabled on a Log Analytics workspace
- An Azure App Registration with the following permissions on the Sentinel workspace:
  - `Microsoft.SecurityInsights/incidents/read`
  - `Microsoft.OperationalInsights/workspaces/query/read`
- The App Registration's Tenant ID, Client ID, and Client Secret

---

## Configuration

Go to **Admin → Integrations → Microsoft Sentinel → Configure**.

| Field | Description |
|---|---|
| Tenant ID | Your Azure AD tenant ID (GUID format) |
| Client ID | Application (client) ID of the App Registration |
| Client Secret | Client secret value from the App Registration |
| Subscription ID | Azure subscription ID containing the Sentinel workspace |
| Resource Group | Resource group name containing the workspace |
| Workspace Name | Log Analytics workspace name |

1. Go to **Admin → Integrations**
2. Find the Microsoft Sentinel card, click **Configure**
3. Fill in all fields above, then click **Save**
4. Click **Test Connection** — this verifies the credentials and workspace access. The integration cannot be enabled until this succeeds.
5. Toggle the integration **Enabled**

All credentials are encrypted at rest with Fernet symmetric encryption.

---

## How Analysts Use It

### Pull Alerts

1. Open an incident → **Timeline** tab → click **Import from Sentinel**
2. Search by alert name, rule name, or time range
3. Select one or more alerts and click **Import**
4. Each selected alert is added as a timeline entry with type `detection`, with the alert ID, severity, and rule name stored in entry metadata

### Run a KQL Query

1. Open an incident → **Timeline** tab → click **Query Sentinel**
2. Write your KQL query in the editor
3. Click **Run** — results appear as a table below the editor
4. Select rows and click **Add to Timeline** to save results as timeline entries

All Sentinel queries and imports are recorded in the audit log.

---

## Troubleshooting

- **Test Connection fails with 401:** The Client Secret may have expired in Azure. Rotate the secret in the App Registration, then update the Client Secret field in IRDoc and click **Save** before re-testing.
- **Test Connection fails with 403:** The App Registration does not have the required permissions, or admin consent has not been granted. Open the App Registration in the Azure portal → **API Permissions** and verify that both permissions are present and show a green consent checkmark.
- **No alerts returned:** Verify that the Workspace Name, Resource Group, and Subscription ID are correct. Query your workspace directly in the Azure portal to confirm alerts exist in the expected time range.
