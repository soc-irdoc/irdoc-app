# Investigation Graph

The Graph tab inside an incident workspace shows a visual map of every entity in the incident and the relationships between them. It connects IOCs, assets, and timeline entries into a single navigable diagram. The graph loads on demand when you open the Graph tab — it is not computed in the background.

---

## What the Graph Shows

**Node types:**

| Node | Description |
|---|---|
| IOC | Each indicator of compromise. Color-coded by type (IP, domain, hash, email, URL, etc.) |
| Asset | Servers, endpoints, accounts, and other assets added to the incident |
| Timeline entry | Key timeline entries, especially pinned ones |

**Automatic edges** — created by IRDoc based on your data:

| Edge | When it appears |
|---|---|
| IOC ↔ Timeline entry | An IOC's pattern (e.g. IP address, domain) is detected in a timeline entry's text |
| Asset ↔ Asset | You defined a link between two assets in the Assets tab |
| Asset ↔ Timeline entry | You linked an asset to a timeline entry |

**Manual edges** — connections you add yourself between any two nodes with a custom label (e.g. `pivoted from`, `dropped by`, `infected`).

---

## Navigating the Graph

| Action | How |
|---|---|
| Pan | Click and drag on the canvas |
| Zoom | Scroll up or down |
| Inspect a node | Click it — details appear in a side panel |
| Reset layout | Click **Auto-layout** in the toolbar |

The side panel shows the full details for the selected node: IOC type and value, asset name and status, or a preview of a timeline entry.

---

## Adding a Manual Edge

> **Analyst role or higher required.**

1. Click the source node to select it
2. Hold `Shift` and click the target node
3. Enter a label for the relationship
4. Press `Enter` or click **Save**

The edge appears as a directed arrow from source to target.

---

## Deleting a Manual Edge

> **Analyst role or higher required.**

Click the edge line to select it. Press `Delete` or click the **X** that appears on the edge. Automatic edges cannot be deleted from the graph — they reflect your underlying data and disappear when that data is removed.

---

## Interpreting the Graph

- **Hub nodes** — IOC or asset nodes with many connections often indicate the attacker's primary infrastructure or the most-pivoted host in the environment. These are high-value investigation targets.
- **Lateral movement chains** — a sequence of asset → asset edges (with type `lateral_movement`) traces the attacker's path through the network.
- **C2 infrastructure** — multiple endpoint or server nodes pointing to a single IOC node (IP or domain) indicates command-and-control communication.
- **Isolated nodes** — assets or IOCs with no edges may be unlinked because the relationship hasn't been documented yet, or they may genuinely be unrelated. Use them as a prompt to verify coverage.

---

## Role Summary

| Action | Minimum role |
|---|---|
| View graph | viewer |
| Add manual edges | analyst |
| Delete manual edges | analyst |
