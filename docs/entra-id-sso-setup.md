# Entra ID / Azure AD — SSO Setup Guide (OAuth2 / OIDC)

IRDoc integrates with Entra ID using **OAuth2 / OpenID Connect (OIDC)** for single sign-on. This is Microsoft's recommended protocol for new applications and requires an **App Registration** (not an Enterprise Application).

> **SharePoint sync is independent.** If you have already created an App Registration for SharePoint sync, you can reuse it for SSO — or create a separate one. Either way, configuring SSO does **not** automatically configure SharePoint sync, and vice versa.

---

## Overview

You will:
1. Create an App Registration in Entra ID
2. Add the IRDoc Redirect URI
3. Create a Client Secret
4. Copy the credentials into IRDoc
5. Optionally map Azure AD groups to IRDoc roles

---

## Step 1 — Create the App Registration

1. Open the [Azure portal](https://portal.azure.com) and go to **Entra ID → App registrations**
2. Click **+ New registration**
3. Give it a name, e.g. `IRDoc`
4. Under **Supported account types**, select **Accounts in this organizational directory only**
5. Leave Redirect URI blank for now — you'll add it in Step 2
6. Click **Register**

After registration, note down:
- **Directory (tenant) ID** — shown on the Overview page
- **Application (client) ID** — shown on the Overview page

---

## Step 2 — Add the Redirect URI

1. In your App Registration, click **Authentication** in the left sidebar
2. Click **+ Add a platform → Web**
3. In the **Redirect URIs** field, enter:

   ```
   https://<your-irdoc-domain>/api/v1/auth/oidc/callback
   ```

   You can copy the exact URL from **IRDoc → Admin → Integrations → Single Sign-On → Configure → Redirect URI**.

4. Under **Implicit grant and hybrid flows**, check **ID tokens**
5. Click **Configure**, then **Save**

---

## Step 3 — Create a Client Secret

1. In your App Registration, click **Certificates & secrets**
2. Click **+ New client secret**
3. Enter a description (e.g. `IRDoc SSO`) and choose an expiry
4. Click **Add**
5. **Copy the secret value immediately** — it is only shown once

---

## Step 4 — Configure API Permissions

1. In your App Registration, click **API permissions**
2. Ensure **Microsoft Graph → openid, profile, email** are listed (they are added by default)
3. If they are missing, click **+ Add a permission → Microsoft Graph → Delegated → openid / profile / email**
4. Click **Grant admin consent for [your tenant]** if required

---

## Step 5 — Enter Credentials in IRDoc

1. Go to **IRDoc → Admin → Integrations → Single Sign-On → Configure**
2. Enter:

   | Field | Where to find it |
   |-------|-----------------|
   | **Directory (Tenant) ID** | App Registration → Overview |
   | **Application (Client) ID** | App Registration → Overview |
   | **Client Secret** | The value you copied in Step 3 |

3. Click **Save SSO Configuration**
4. Toggle **SSO** on to enable it

---

## Step 6 — Assign Users

Users must be signed in to your tenant to authenticate via SSO. IRDoc provisions accounts automatically on first login — no pre-provisioning required.

To restrict access to specific users or groups:
1. In the Azure portal, find the **Enterprise Application** that was automatically created alongside your App Registration (same name)
2. Click **Users and groups → + Add user/group**
3. Assign the relevant users or security groups

---

## Step 7 — Configure Group-to-Role Mapping (optional)

IRDoc can automatically assign roles based on Azure AD group membership.

### Enable group claims in Azure

1. In your App Registration → **Token configuration**
2. Click **+ Add groups claim**
3. Select **Security groups**
4. Under **ID**, check that the group claim is emitted as **Group ID** (this sends Object IDs / GUIDs)
5. Click **Add**

> **Note:** Azure sends group **Object IDs** (GUIDs), not display names. Copy the Object ID from **Entra ID → Groups → your group → Overview → Object ID**.

### Map groups in IRDoc

1. In IRDoc → Integrations → SSO → **Role Mappings**, click **+ Add Mapping**
2. Enter the **Azure AD group Object ID** (GUID) in the left field
3. Select the target IRDoc role:
   - `viewer` — read-only
   - `analyst` — standard analyst
   - `senior_analyst` — can lead incidents
   - `admin` — full administrative access
4. Repeat for each group, then save

Unmapped users who successfully authenticate receive the **Analyst** role by default.

---

## Testing the SSO Login

1. Open IRDoc in a private browser window
2. On the login page, click **Sign in with SSO**
3. You will be redirected to Microsoft — authenticate with your Entra ID account
4. On success, you are redirected back to IRDoc and logged in

---

## Sharing an App Registration with SharePoint Sync

If you want a single App Registration for both SSO and SharePoint sync:

- SSO needs: **openid, profile, email** delegated permissions + a Redirect URI
- SharePoint sync needs: **Sites.ReadWrite.All** (or scoped site permissions) application permissions

Both can coexist in the same App Registration. Configure each feature independently in IRDoc — enabling SSO does **not** automatically enable SharePoint sync, and vice versa.

---

## Troubleshooting

**"SSO is not configured or not enabled"**
Go to Integrations → SSO, enter all three credentials, save, then toggle SSO on.

**"Failed to exchange authorization code — check your Client Secret"**
The client secret is incorrect or has expired. Create a new secret in Azure, paste it into IRDoc, and save.

**"OIDC token missing email"**
The `email` scope was not consented. Go to App Registration → API permissions and grant admin consent for `email`.

**User gets wrong role after SSO**
Check the group Object ID in Role Mappings. Azure sends Object IDs (GUIDs) by default. Copy the exact GUID from Entra ID → Groups → your group → Object ID.

**Groups claim is empty**
Group claims must be explicitly enabled. Go to App Registration → Token configuration → Add groups claim.

**"Invalid CSRF state"**
The browser blocked the state cookie (e.g. third-party cookie restrictions). Ensure IRDoc's domain is trusted and retry.
