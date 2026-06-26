# CrowdStrike Falcon

> **Premium feature** — requires a commercial license key.

> **Senior Analyst role or higher required** to trigger containment actions.

Allows senior analysts to contain (isolate from the network) a CrowdStrike-managed endpoint directly from an IRDoc incident, without leaving the platform. Every containment action requires manual confirmation and is fully audited.

---

## Prerequisites

- A CrowdStrike Falcon subscription with Host Management permissions
- A CrowdStrike API client with the following scopes:
  - `Hosts: Read`
  - `Hosts: Write` (required for containment)
- The API client's Client ID and Client Secret — created in **Support → API Clients and Keys** in the Falcon console

---

## Configuration

Go to **Admin → Integrations → CrowdStrike → Configure**.

| Field | Description |
|---|---|
| Client ID | CrowdStrike API client ID |
| Client Secret | CrowdStrike API client secret |
| Base URL | Falcon API base URL. Default: `https://api.crowdstrike.com`. For GovCloud use: `https://api.laggar.gcw.crowdstrike.com` |
| Member CID | For MSSP parent CIDs managing multiple customers — enter the child CID to target. Leave blank for single-tenant deployments. |

1. Go to **Admin → Integrations**
2. Find the CrowdStrike card, click **Configure**
3. Fill in all fields above, then click **Save**
4. Click **Test Connection** — must succeed before the integration is usable
5. Toggle the integration **Enabled**

All credentials are encrypted at rest with Fernet symmetric encryption.

---

## How Analysts Use It

### Contain a Host

1. Open an incident → **Assets** tab
2. Find the asset to contain. The hostname must match the CrowdStrike device name exactly, or enter the Falcon device ID in the asset's hostname field.
3. Click **Contain Host** on the asset row
4. A confirmation dialog explains what containment does (blocks all network traffic except CrowdStrike management) — click **Confirm Containment**
5. IRDoc calls the CrowdStrike API and reports success or failure inline
6. A containment event is added to the incident timeline and recorded in the audit log

### Lift Containment

Follow the same steps as above. Once a host is contained, the button changes to **Lift Containment**. Confirming lifts the isolation and restores normal network access.

---

## Security Notes

- Containment is a high-risk, high-impact action — the confirmation dialog is mandatory and cannot be disabled or bypassed
- All containment and lift-containment actions are written to the audit log with the acting user's identity and timestamp
- Only `senior_analyst` and `admin` roles can trigger containment; analyst-role users do not see the **Contain Host** button

---

## Troubleshooting

- **Test Connection fails:** Ensure the API scopes include both `Hosts: Read` and `Hosts: Write`, and that the client has not been expired or suspended in the Falcon console.
- **Containment returns "device not found":** The asset hostname in IRDoc must match the CrowdStrike AID or device hostname exactly. Open the Falcon console and confirm the exact device name, then update the asset in IRDoc to match.
