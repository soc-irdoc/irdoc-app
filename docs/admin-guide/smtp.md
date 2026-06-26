# Email / SMTP Configuration

> **Admin role required.**

IRDoc sends email for user invitations, password resets, and (if configured) incident notification alerts. Without SMTP configured, invitation links are printed to the backend logs instead (`docker compose logs irdoc-backend`).

---

## Configuring SMTP

Go to **Admin → Email** and fill in the fields below, then click **Save**.

| Field | Description |
|---|---|
| Host | SMTP server hostname (e.g. `smtp.office365.com`, `smtp.gmail.com`) |
| Port | Typically `587` for STARTTLS, `465` for SSL, `25` for unencrypted |
| Use TLS | Enable STARTTLS (recommended). Use SSL if your provider requires port 465. |
| Username | SMTP authentication username (usually the sending email address) |
| Password | SMTP authentication password. Stored encrypted. |
| From address | The email address emails are sent from (e.g. `irdoc@yourcompany.com`) |
| From name | Display name in the From field (e.g. `IRDoc Platform`) |

---

## Email branding

| Field | Description |
|---|---|
| Logo URL | Image shown in email headers (same as org branding logo) |
| Accent color | Button and link color in email templates |
| Footer text | Custom text in email footer (e.g. your company name or legal notice) |

---

## Testing the configuration

Click **Send Test Email** — IRDoc sends a test message to the currently logged-in admin's email address. If the test fails, the error message from the SMTP server is displayed inline.

---

## Common setups

**Gmail / Google Workspace:**
- Host: `smtp.gmail.com`, Port: `587`, TLS: on
- Use an App Password (not your Google account password) — create one at myaccount.google.com → Security → App passwords

**Microsoft 365 / Exchange Online:**
- Host: `smtp.office365.com`, Port: `587`, TLS: on
- Enable "Authenticated SMTP" in Microsoft 365 admin → Users → Active users → Mail settings

**Self-hosted Postfix / Sendmail:**
- Host: your MTA hostname, Port: `25` or `587`
- Ensure the IRDoc container IP is allowed to relay

---

## Disabling email

Clear the **Host** field and save. IRDoc falls back to printing invite links to the backend logs.
