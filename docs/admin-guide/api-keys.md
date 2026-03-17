# API Keys

API keys allow external tools (service desks, SOAR platforms, scripts) to create and read incident data via the IRDoc REST API without user credentials.

> **Admin role required** to create and manage API keys.

---

## Creating an API Key

1. Go to **Settings → API Keys**
2. Click **Create API Key**
3. Enter a name (e.g., `ServiceDesk Plus Production`)
4. Select the scopes the key needs (see below)
5. Optionally set an expiry date
6. Click **Create**

**The raw key is shown once.** Copy it immediately — it cannot be retrieved again. IRDoc stores only the Argon2id hash.

---

## Scopes

| Scope | What it allows |
|---|---|
| `incidents:create` | Create incidents via inbound webhook |
| `incidents:read` | Read incident list and details |
| `incidents:write` | Update existing incidents |
| `timeline:read` | Read timeline entries |
| `iocs:read` | Read IOCs |
| `reports:read` | Download generated reports |

For a service desk integration that only creates cases, grant only `incidents:create`.

---

## Using an API Key

Include the key in the `Authorization` header:

```
Authorization: ApiKey irp_key_your_key_value_here
```

**Not** `Bearer` — API keys use `ApiKey` prefix.

---

## Inbound Webhook Setup (ServiceDesk Plus / ManageEngine / Jira)

### 1. Create the key

Create a key with `incidents:create` scope. Note the raw key.

### 2. Configure the webhook in your service desk

**ServiceDesk Plus (ManageEngine):**
- Notification Rules → Add Rule → HTTP webhook
- URL: `https://your-irdoc/api/v1/external/incidents`
- Method: POST
- Headers: `Authorization: ApiKey irp_key_xxx`, `Content-Type: application/json`
- Body:
```json
{
  "title": "${WorkOrder.Subject}",
  "severity": "sev2",
  "external_source": "servicedesk_plus",
  "external_ref": "${WorkOrder.RequestID}",
  "external_url": "${WorkOrder.URL}"
}
```

**Jira:**
- Project Settings → Automation → Create rule
- Trigger: Issue created (filter by label or project)
- Action: Send web request
- URL: `https://your-irdoc/api/v1/external/incidents`
- Headers: `Authorization: ApiKey irp_key_xxx`
- Body:
```json
{
  "title": "{{issue.summary}}",
  "severity": "sev3",
  "external_source": "jira",
  "external_ref": "{{issue.key}}",
  "external_url": "{{issue.url}}"
}
```

### 3. Verify

A new incident with the external ref badge should appear in IRDoc within seconds of a ticket being created.

---

## Revoking a Key

Go to **Settings → API Keys** and click **Revoke** on the key row. Revocation is immediate — any request using that key will return `401`.
