# SharePoint Sync Setup Guide

IRDoc can automatically push generated PDF reports to a SharePoint document library after every incident update. The sync uses the **Microsoft Graph API** with an Azure App Registration and **client credentials** (application-level auth — no user login required).

> **Independent from SSO.** SharePoint sync and Single Sign-On are configured separately. They can share the same App Registration, or use different ones — your choice.

---

## How it works

1. A report is generated (manually or via AI auto-generation)
2. After a configurable delay (default: 120 seconds), IRDoc uploads the PDF to your SharePoint document library
3. The file is named using a configurable pattern, e.g. `INC-2026-001 - Executive Summary.pdf`
4. If a file with the same name already exists, it is overwritten — always the latest version

---

## What you need

| Item | Where to get it |
|------|----------------|
| Azure Tenant ID | Entra ID → Overview → Directory (tenant) ID |
| Application (Client) ID | App Registration → Overview |
| Client Secret | App Registration → Certificates & secrets |
| SharePoint Site URL | Your browser's address bar when browsing the site |
| Document library name | Shown in the site's left sidebar (default: `Documents`) |

---

## Step 1 — Create the App Registration

If you already created an App Registration for SSO, you can reuse it by jumping to Step 2 and adding the new API permissions. Otherwise:

1. Open the [Azure portal](https://portal.azure.com) and go to **Entra ID → App registrations**
2. Click **+ New registration**
3. Name it (e.g. `IRDoc` or `IRDoc SharePoint Sync`)
4. Under **Supported account types**, select **Accounts in this organizational directory only**
5. Leave Redirect URI blank — SharePoint sync uses client credentials (no browser redirect)
6. Click **Register**

After registration, copy:
- **Directory (tenant) ID** — from the Overview page
- **Application (client) ID** — from the Overview page

---

## Step 2 — Grant Microsoft Graph API Permissions

IRDoc uses the Graph API to write files to SharePoint. You must grant **application** permissions (not delegated), because the sync runs in the background without a signed-in user.

1. In your App Registration, click **API permissions** in the left sidebar
2. Click **+ Add a permission → Microsoft APIs → Microsoft Graph**
3. Select **Application permissions** (not Delegated)
4. Search for and add:

   | Permission | Why it's needed |
   |------------|----------------|
   | `Sites.ReadWrite.All` | Read the SharePoint site structure and upload files |

   > **Scope restriction (recommended):** `Sites.ReadWrite.All` grants access to all sites in your tenant. If you want to restrict to a single site, use `Sites.Selected` instead — see [Step 2a](#step-2a-optional-restrict-to-a-specific-site-sites-selected) below.

5. Click **Add permissions**
6. Click **Grant admin consent for [your tenant]** — this is required for application permissions
7. Confirm. The permission status should show a green checkmark.

### Step 2a (optional) — Restrict to a specific site (Sites.Selected)

`Sites.Selected` limits the app to only the sites you explicitly allow. This is more secure than `Sites.ReadWrite.All`.

1. Add `Sites.Selected` (application permission) instead of `Sites.ReadWrite.All`
2. Grant admin consent as above
3. Then use the Graph API or SharePoint Admin PowerShell to grant site-specific access:

   ```powershell
   # SharePoint Admin PowerShell
   Connect-PnPOnline -Url "https://yourcompany.sharepoint.com" -Interactive
   Grant-PnPAzureADAppSitePermission `
     -AppId "<your-client-id>" `
     -DisplayName "IRDoc" `
     -Site "https://yourcompany.sharepoint.com/sites/SOC" `
     -Permissions Write
   ```

   Or via Graph API (see [Microsoft docs](https://learn.microsoft.com/en-us/graph/api/site-post-permissions)).

---

## Step 3 — Create a Client Secret

1. In your App Registration, click **Certificates & secrets**
2. Click **+ New client secret**
3. Enter a description (e.g. `IRDoc SharePoint Sync`) and choose an expiry (12 or 24 months)
4. Click **Add**
5. **Copy the secret value immediately** — it is shown only once

> Set a calendar reminder before the secret expires, or create a new secret and update IRDoc before the old one expires.

---

## Step 4 — Find your SharePoint Site URL

Navigate to your SharePoint site in a browser. The URL looks like:

```
https://yourcompany.sharepoint.com/sites/SOC
```

Copy the full URL — including the `/sites/...` path. This is what you'll paste into IRDoc.

---

## Step 5 — Configure SharePoint Sync in IRDoc

1. Go to **IRDoc → Admin → Integrations**
2. Find **SharePoint / OneDrive** and click **Configure**
3. Fill in the fields:

   | Field | Value |
   |-------|-------|
   | **Azure Tenant ID** | Your Directory (tenant) ID |
   | **App Client ID** | Your Application (client) ID |
   | **Client Secret** | The value you copied in Step 3 |
   | **SharePoint Site URL** | e.g. `https://yourcompany.sharepoint.com/sites/SOC` |
   | **Document Library** | Name of the library (default: `IR Reports`) — see note below |
   | **Filename Pattern** | `{incident_ref} - {template_name}.pdf` |
   | **Sync Delay (seconds)** | `120` — waits this long after the last update before syncing |

4. Click **Test Connection** to verify credentials and site access before saving
5. Click **Save**, then toggle the integration **On**

### Document library name

The **Document Library** field must exactly match the library's name as shown in SharePoint (case-insensitive). The default is `IR Reports`. If the library doesn't exist, IRDoc creates it automatically using the Microsoft Graph API — no manual setup required.

### Folder structure

Inside the document library, IRDoc organises reports into per-incident subfolders. The folder is named after the incident reference and is created automatically on the first sync:

```
IR Reports/
├── INC-2026-0021/
│   ├── INC-2026-0021 - Executive Summary.pdf
│   └── INC-2026-0021 - Technical Report.pdf
└── INC-2026-0022/
    └── INC-2026-0022 - Management Brief.pdf
```

The filename inside each folder follows the configured **Filename Pattern** unchanged.

### Filename pattern tokens

| Token | Example output |
|-------|---------------|
| `{incident_ref}` | `INC-2026-001` |
| `{template_name}` | `Executive Summary` |
| `{date}` | `2026-06-12` |

Example: `{date} - {incident_ref} - {template_name}.pdf` → `2026-06-12 - INC-2026-001 - Executive Summary.pdf`

---

## Step 6 — Test the integration

1. Open any incident and generate a report (Reports tab → Generate)
2. Wait the configured sync delay (default 2 minutes)
3. Browse to your SharePoint document library — the PDF should appear

You can also watch for the sync banner on the incident Reports tab — it shows "Synced to SharePoint" with a link to the file once the upload completes.

---

## Sharing an App Registration with SSO

If you want a single App Registration for both SSO and SharePoint sync:

| Feature | Auth type | Permissions needed |
|---------|-----------|-------------------|
| SharePoint sync | Client credentials (no user) | `Sites.ReadWrite.All` (application) |
| SSO (OIDC) | Authorization code (user login) | `openid profile email` (delegated) + Redirect URI |

Both can coexist in the same App Registration. Configure each feature independently in IRDoc — they do not affect each other.

---

## Troubleshooting

**Test connection fails — "401 Unauthorized"**
The client secret is wrong or expired. Create a new secret and update the IRDoc config.

**Test connection fails — "403 Forbidden"**
The app doesn't have permission to the SharePoint site. Check that:
- `Sites.ReadWrite.All` (or `Sites.Selected`) is granted with admin consent
- If using `Sites.Selected`, the site was explicitly granted to the app

**Test connection fails — "Site not found"**
The SharePoint Site URL is incorrect. Make sure it includes the full path, e.g. `https://company.sharepoint.com/sites/SOC`, not just the domain.

**Files appear in the wrong library**
The Document Library name is case-insensitive but must match exactly. If the named library is not found, IRDoc creates it automatically — so if creation is failing, verify that `Sites.ReadWrite.All` admin consent is granted in the Azure portal (required for library creation as well as uploads).

**Sync doesn't trigger after report generation**
Make sure the SharePoint integration toggle is **On** in Integrations. Also check that the Celery worker is running — SharePoint uploads happen in the background task queue.

**Client secret expires**
Create a new secret in Azure before the old one expires, paste it into IRDoc (Configure → Client Secret), save. The old secret becomes invalid on expiry — if you miss the window, reports will stop syncing until the config is updated.
