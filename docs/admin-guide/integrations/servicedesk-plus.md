# ServiceDesk Plus — Inbound Webhook

This guide configures ManageEngine ServiceDesk Plus to automatically create IRDoc cases when tickets are raised.

---

## Prerequisites

- IRDoc API key with `incidents:create` scope (see [API Keys](../api-keys.md))
- ServiceDesk Plus admin access
- IRDoc accessible from the SDP server (network connectivity)

---

## Configuration

### 1. Create the Notification Rule in SDP

1. Log into SDP as administrator
2. Navigate to **Admin → Notification Rules**
3. Click **Add Notification Rule**
4. Configure:
   - **Event:** Request Created (or your preferred trigger)
   - **Notification Type:** Execute Script / HTTP webhook (varies by SDP version)

### 2. HTTP Webhook settings

- **URL:** `https://your-irdoc/api/v1/external/incidents`
- **Method:** POST
- **Headers:**
  ```
  Authorization: ApiKey irp_key_your_key_here
  Content-Type: application/json
  ```
- **Body:**
  ```json
  {
    "title": "${WorkOrder.Subject}",
    "severity": "sev2",
    "external_source": "servicedesk_plus",
    "external_ref": "SDP-${WorkOrder.RequestID}",
    "external_url": "https://your-sdp/WorkOrder.do?woMode=viewWO&woID=${WorkOrder.RequestID}"
  }
  ```

### Severity mapping

Adjust the `severity` field based on SDP priority if desired:

| SDP Priority | IRDoc Severity |
|---|---|
| High | `sev1` |
| Medium | `sev2` |
| Low | `sev3` |
| Planning | `sev4` |

SDP doesn't support conditional logic in webhook bodies natively — consider using a simple middleware script or accepting a fixed severity and updating manually in IRDoc.

---

## Result

When a ticket is created in SDP, an IRDoc incident appears within seconds with:
- The SDP subject as the incident title
- An **SDP badge** in the incident header linking back to the original ticket
- The SDP ticket number stored as `external_ref`

---

## Troubleshooting

**IRDoc returns 401:** Check the `Authorization` header format — it must be `ApiKey irp_key_xxx`, not `Bearer`.

**IRDoc returns 422:** Check the JSON body is valid and `severity` is one of `sev1`, `sev2`, `sev3`, `sev4`.

**Webhook not triggering:** Check SDP notification rule is active and the IRDoc URL is reachable from the SDP server. Try `curl` from the SDP server.

**Rate limited (429):** The default limit is 20 requests/minute per key. Adjust `WEBHOOK_RATE_LIMIT` in `.env` if needed.
