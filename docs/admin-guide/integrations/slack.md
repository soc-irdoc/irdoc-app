# Slack

> **Admin role required** to configure.

Sends incident notifications to a Slack channel — new incidents, status changes, severity escalations, and assignment updates.

---

## Prerequisites

- A Slack workspace where you have permission to create apps
- A Slack Incoming Webhook URL for the target channel

**Creating the Slack Incoming Webhook:**

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Give the app a name (e.g. "IRDoc Alerts") and select your workspace
3. In the app settings, click **Incoming Webhooks** → toggle **Activate Incoming Webhooks** on
4. Click **Add New Webhook to Workspace** → select the channel to post to → click **Allow**
5. Copy the Webhook URL (starts with `https://hooks.slack.com/services/...`)

---

## Configuration

Go to **Admin → Integrations → Slack → Configure**.

| Field | Description |
|---|---|
| Webhook URL | The Incoming Webhook URL from the Slack app settings |

1. Go to **Admin → Integrations**
2. Find the Slack card, click **Configure**
3. Paste the Webhook URL, then click **Save**
4. Click **Test Connection** — IRDoc sends a test message to the configured channel. Confirm it arrives before proceeding.
5. Toggle the integration **Enabled**

All credentials are encrypted at rest with Fernet symmetric encryption.

---

## What Triggers a Notification

| Event | Message Content |
|---|---|
| Incident created | Title, severity, assigned analyst, link to workspace |
| Severity changed | Old → new severity, who changed it |
| Status changed | Old → new status, who changed it |
| Incident assigned | Assigned to whom, incident title |

Timeline entry notifications are not sent by default (too noisy for most teams). This behaviour is not configurable in v1.0.

**Message format:** IRDoc posts formatted Slack messages with colour-coded severity (red = sev1, orange = sev2, yellow = sev3, grey = sev4) and a direct link to the incident workspace.

---

## Troubleshooting

- **Test Connection fails:** Check that the Webhook URL was copied in full — it is a single long URL and is easy to truncate accidentally.
- **Messages not appearing in the channel:** The Webhook URL is channel-specific. If the bot was removed from the channel or the channel was deleted, create a new webhook and update the configuration.
- **App was uninstalled from Slack:** You need to create a new webhook and re-configure the integration after reinstalling the app.
