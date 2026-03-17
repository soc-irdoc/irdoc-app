# IOC Management

IRDoc tracks Indicators of Compromise (IOCs) associated with each incident — IPs, domains, hashes, emails, URLs, usernames, and files.

---

## IOC Types

| Type | Examples |
|---|---|
| `ip` | `192.168.1.100`, `10.0.0.5` |
| `domain` | `evil.example.com`, `c2.attacker.io` |
| `email` | `phishing@attacker.com` |
| `url` | `https://attacker.io/payload.exe` |
| `hash` | MD5, SHA-1, SHA-256 |
| `file` | `malware.exe`, `payload.dll` |
| `username` | `compromised_user`, `DOMAIN\svcaccount` |

---

## Adding an IOC

1. Click **+ Add IOC** in the IOC tab
2. Enter the value — the type is auto-detected
3. Set confidence (0–100) and initial status
4. Click **Add**

### Auto-detection

When you type or paste into the IOC value field, IRDoc detects the type automatically using the same regex patterns applied to timeline entries.

### Bulk Import

Paste a block of text containing multiple IOCs (e.g., a threat intel report excerpt). IRDoc scans the text and presents a modal showing all detected IOCs. Select which ones to add.

---

## IOC Status

| Status | Meaning |
|---|---|
| `active` | IOC is currently active in the environment |
| `blocked` | IOC has been blocked (firewall rule, EDR quarantine, etc.) |
| `remediated` | IOC has been fully remediated |
| `false_positive` | IOC was investigated and determined not malicious |

---

## Confidence Score

0–100 scale indicating how confident you are that this IOC is malicious:
- **90–100**: Confirmed malicious (e.g., known C2 from threat intel)
- **70–89**: High confidence (e.g., seen in logs, matches known TTPs)
- **50–69**: Medium confidence (e.g., suspicious but not confirmed)
- **< 50**: Low confidence / under investigation

---

## TLP Levels

Traffic Light Protocol levels for sharing sensitivity:
- **TLP:RED** — not for disclosure, restricted to named recipients only
- **TLP:AMBER** — limited disclosure to org and partners
- **TLP:GREEN** — limited disclosure to the community
- **TLP:WHITE** — unlimited disclosure

---

## Enrichment (Premium)

If VirusTotal, AbuseIPDB, or Shodan integrations are enabled (Admin → Integrations), IOCs are automatically enriched when added.

Enrichment data appears in the IOC table as per-provider summaries. Click an IOC to expand the full enrichment JSON.

To manually trigger enrichment on an existing IOC, use the **Enrich** button on the IOC row.

---

## IOC-Timeline Links

IOCs can be linked to specific timeline entries. These links are used to build the Investigation Graph and appear in the IOC table and evidence register blocks in reports.

Links are created automatically when an IOC value is mentioned in a timeline entry description. They can also be set manually on the timeline entry form.
