# Microsoft Teams

> **Admin role required** to configure.

Sends incident notifications to a Microsoft Teams channel — new incidents, status changes, severity escalations, and assignment updates.

---

## Prerequisites

- A Microsoft Teams workspace where you are an owner of the target team
- A Teams Incoming Webhook connector URL for the target channel

**Creating the Teams Incoming Webhook:**

1. In Microsoft Teams, navigate to the channel where you want notifications
2. Click **...** (More options) next to the channel name → **Connectors**
3. Search for **Incoming Webhook** → click **Configure**
4. Give the webhook a name (e.g. "IRDoc Alerts") and optionally upload an image
5. Click **Create** → copy the webhook URL
6. Click **Done**

> In newer Teams environments, Connectors may be managed via **Manage channel** → **Settings** → **Connectors**. If Connectors is not available in your organization, ask your Microsoft 365 admin to enable it, or use Power Automate as an alternative delivery method.

---

## Configuration

Go to **Admin → Integrations → Microsoft Teams → Configure**.

| Field | Description |
|---|---|
| Webhook URL | The Incoming Webhook URL from the Teams connector setup |

1. Go to **Admin → Integrations**
2. Find the Microsoft Teams card, click **Configure**
3. Paste the Webhook URL, then click **Save**
4. Click **Test Connection** — IRDoc sends a test card to the configured channel. Confirm it arrives before proceeding.
5. Toggle the integration **Enabled**

All credentials are encrypted at rest with Fernet symmetric encryption.

---

## What Triggers a Notification

| Event | Card Content |
|---|---|
| Incident created | Title, severity badge, assigned analyst, link |
| Severity changed | Previous → new severity, changed by whom |
| Status changed | Previous → new status, changed by whom |
| Incident assigned | Assigned to whom, incident title |

**Message format:** IRDoc sends Adaptive Cards to Teams with colour-coded severity and direct links to the incident workspace.

---

## Troubleshooting

- **Test Connection fails:** Ensure the webhook URL was copied in full. Teams webhook URLs are long and easy to truncate.
- **"The Connector has been disabled":** Microsoft may disable connectors after 90 days of inactivity or due to tenant policy. Re-configure the connector in Teams to obtain a new URL, then update the configuration in IRDoc.
- **Connectors not available in your org:** Your Microsoft 365 admin may have disabled third-party connectors. Use Power Automate with an HTTP trigger as an alternative, or switch to the Slack integration.
