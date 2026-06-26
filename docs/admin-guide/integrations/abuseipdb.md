# AbuseIPDB

> **Admin role required** to configure.

Enriches IP address IOCs with AbuseIPDB reputation data — abuse confidence score, total report count, usage type, ISP, and country. Runs automatically when an IP IOC is added, alongside VirusTotal enrichment if that integration is also configured.

---

## Prerequisites

- An AbuseIPDB account with an API key
- Free tier: 1,000 lookups/day — sufficient for most deployments
- Professional and Enterprise plans are available for higher volume

---

## Configuration

Go to **Admin → Integrations → AbuseIPDB → Configure**.

| Field | Description |
|---|---|
| API Key | Your AbuseIPDB API key (from abuseipdb.com → Account → API) |

1. Go to **Admin → Integrations**
2. Find the AbuseIPDB card, click **Configure**
3. Enter your API Key, then click **Save**
4. Click **Test Connection** — must succeed before the integration is usable
5. Toggle the integration **Enabled**

All credentials are encrypted at rest with Fernet symmetric encryption.

---

## How It Works

When an analyst adds an IOC of type `ip`, IRDoc queues an AbuseIPDB lookup automatically. The result is stored alongside any VirusTotal data on the same IOC record.

**Enrichment data shown:**
- Abuse confidence score: 0–100 (100 = universally reported as malicious)
- Total number of abuse reports submitted to AbuseIPDB
- Usage type: e.g. "Data Center/Web Hosting", "Fixed Line ISP", "Tor Exit Node"
- ISP and country
- Last reported timestamp
- Direct link to the full AbuseIPDB report

**Interpreting the confidence score:**

| Score | Interpretation |
|---|---|
| 0–10 | Low risk — likely clean |
| 11–50 | Suspicious — investigate further |
| 51–100 | High risk — likely malicious; consider blocking |

Note: AbuseIPDB enriches only `ip` type IOCs. Domains, hashes, URLs, and other types are not queried.

---

## Troubleshooting

- **Score shows "N/A":** The IP may not yet be in the AbuseIPDB database (new or very clean IP), or the daily quota has been reached. Free-tier quotas reset at midnight UTC.
- **Enrichment not appearing:** Ensure the integration is enabled, then click the refresh icon on the IOC to retry the lookup manually.
