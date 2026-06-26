# Assets

Assets are the infrastructure, accounts, and services involved in an incident — compromised servers, affected user accounts, attacker-controlled resources, and anything else that played a role. The Assets tab is inside the incident workspace.

---

## Asset Fields

| Field | Type | Description |
|---|---|---|
| Name | Required | Hostname, IP address, username, or service name |
| Type | Required | endpoint, server, account, network_device, cloud_resource, email, or other |
| Status | Required | clean, compromised, remediated, or unknown (default) |
| IP address | Optional | IPv4 or IPv6 address |
| Hostname | Optional | Fully-qualified or short hostname |
| Description | Optional | Free-text notes about the asset |

---

## Adding a Single Asset

> **Analyst role or higher required.**

1. Open the **Assets** tab in the incident workspace
2. Click **Add Asset**
3. Fill in the name, type, and status fields
4. Add optional IP address, hostname, or description as needed
5. Click **Save**

---

## Bulk Import

> **Analyst role or higher required.**

Use bulk import to quickly add multiple assets at once:

1. Click **Import**
2. Paste a list of asset names — one asset per line
3. Click **Import**

Each line becomes one asset with type `other` and status `unknown`. Edit assets individually after import to set types, statuses, and other fields.

---

## Updating an Asset

Click any asset row to expand it and edit its fields inline. Changes save automatically when you click outside the field.

To change status directly without expanding the row, click the status badge on the asset row.

---

## Deleting an Asset

> **Senior Analyst role or higher required.**

Hover over an asset row and click the delete icon. Confirm when prompted. Deletion also removes any links from that asset to other assets and to timeline entries.

---

## Asset Links (Relationships)

You can define directed relationships between assets to model how an attacker moved through the environment.

**Relationship types:**

| Type | Use case |
|---|---|
| infection_vector | How the initial compromise reached this asset |
| lateral_movement | Attacker moved from one asset to another |
| c2_communication | Asset communicating with attacker infrastructure |
| data_exfiltration | Data left the environment through this path |
| related | General association with no specific relationship type |

**To create a link:**

1. Click **Link Assets** on the source asset
2. Select the target asset from the list
3. Choose a relationship type
4. Click **Save**

Links are directional: `endpoint-012 → [lateral_movement] → srv-dc01`. They appear as directed edges in the Investigation Graph.

---

## Asset ↔ Timeline Links

Associate an asset with a specific timeline entry to record which events involved which assets:

1. Open a timeline entry (click it in the Timeline tab)
2. Click **Link Asset**
3. Select the asset from the list
4. Click **Save**

These associations are visible in the Investigation Graph and in the expanded timeline entry view.

---

## Role Summary

| Action | Minimum role |
|---|---|
| View assets | viewer |
| Add or edit assets | analyst |
| Create asset links | analyst |
| Link assets to timeline entries | analyst |
| Delete assets | senior_analyst |
