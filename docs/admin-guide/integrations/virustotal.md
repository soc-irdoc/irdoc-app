# VirusTotal

> **Admin role required** to configure.

Automatically enriches IOCs (IP addresses, domains, file hashes) with VirusTotal reputation data. Enrichment runs in the background when an IOC is added and populates detection counts, vendor verdicts, and community score directly on the IOC record.

---

## Prerequisites

- A VirusTotal account with an API key
- Free tier: 4 lookups/minute, 500/day — sufficient for low-volume deployments
- VirusTotal Enterprise: higher rate limits and additional data fields

---

## Configuration

Go to **Admin → Integrations → VirusTotal → Configure**.

| Field | Description |
|---|---|
| API Key | Your VirusTotal API key (from virustotal.com → Your Profile → API Key) |

1. Go to **Admin → Integrations**
2. Find the VirusTotal card, click **Configure**
3. Enter your API Key, then click **Save**
4. Click **Test Connection** — must succeed before the integration is usable
5. Toggle the integration **Enabled**

All credentials are encrypted at rest with Fernet symmetric encryption.

---

## How It Works

When an analyst adds an IOC of type `ip`, `domain`, or `hash`, IRDoc automatically queues a VirusTotal lookup. The result is stored on the IOC record and displayed in the IOC list and IOC detail view.

**Enrichment data shown per IOC:**
- Detection count — e.g. "38/90 vendors flagged this" with a red/yellow/green indicator
- Community score
- First seen / last seen in VirusTotal
- Top vendor tags (e.g. "malware", "phishing", "trojan")
- Direct link to the full VirusTotal report

**IOC types enriched:**

| IOC Type | VirusTotal Lookup |
|---|---|
| `ip` | IP address report |
| `domain` | Domain report |
| `hash` (MD5 / SHA1 / SHA256) | File report |
| `url` | Not enriched automatically (rate limit impact) |
| `email`, `username`, `file` | Not enriched |

**Manual re-enrichment:**
Click the refresh icon on any IOC in the list to re-trigger enrichment immediately, regardless of when the last lookup ran.

**Rate limiting:**
IRDoc queues enrichment requests and respects VirusTotal API rate limits. On free-tier keys, enrichment for a burst of new IOCs may take a few minutes to complete.

---

## Troubleshooting

- **Enrichment data not appearing:** Verify the integration is enabled. Click the refresh icon on the IOC to manually trigger enrichment. If the problem persists, check backend logs: `docker compose logs irdoc-backend | grep virustotal`
- **Test Connection returns 403:** The API key is invalid or the free-tier daily quota is exhausted. Free-tier quotas reset at midnight UTC. To avoid interruptions, upgrade to a paid VirusTotal plan or reduce IOC ingestion volume.
