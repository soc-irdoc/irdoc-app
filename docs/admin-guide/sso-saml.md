# SSO / SAML 2.0

IRDoc supports SAML 2.0 single sign-on with any compliant identity provider.

---

## Supported Identity Providers

- Okta
- Microsoft Azure Active Directory (Entra ID)
- Google Workspace
- Any SAML 2.0-compliant IdP

---

## Setup

### 1. Get your SP metadata

In IRDoc, go to **Admin → SSO**. At the bottom of the page, click **View SP Metadata** to get your Service Provider metadata XML, or note these values:

- **Entity ID:** `https://your-irdoc/api/v1/auth/saml/metadata`
- **ACS URL:** `https://your-irdoc/api/v1/auth/saml/acs`

### 2. Configure your IdP

Create a new SAML application in your IdP:

**Okta:**
1. Applications → Create App Integration → SAML 2.0
2. Single sign-on URL: your ACS URL
3. Audience URI: your Entity ID
4. Attribute statements: `email` → `user.email`, `name` → `user.displayName`

**Azure AD:**
1. Enterprise Applications → New Application → Non-gallery
2. Set up single sign-on → SAML
3. Identifier (Entity ID): your Entity ID
4. Reply URL (ACS URL): your ACS URL
5. Attributes: `emailaddress` → `user.mail`, `name` → `user.displayname`

### 3. Configure IRDoc

In **Admin → SSO**:

1. Select your IdP type
2. Paste your IdP metadata URL or enter the fields manually:
   - **IdP Entity ID**
   - **SSO URL** (IdP sign-in URL)
   - **Certificate** (IdP signing certificate, PEM format)
3. Configure **Attribute Mapping**:
   - Email attribute name (e.g., `email`, `emailaddress`, `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress`)
   - Name attribute name
4. Configure **Role Mappings** (optional): map IdP groups to IRDoc roles

Click **Save**.

### 4. Test

Click the **Sign in with SSO** button on the login page. You should be redirected to your IdP and back.

---

## Role Mappings

Map IdP group membership to IRDoc roles:

| IdP Group | IRDoc Role |
|---|---|
| `SOC-Admins` | `admin` |
| `SOC-Senior` | `senior_analyst` |
| `SOC-Analysts` | `analyst` |
| `SOC-Viewers` | `viewer` |

Users not matched by any role mapping are assigned `viewer` by default.

Role mappings are applied on every login — if a user's IdP group changes, their IRDoc role updates on next sign-in.

---

## Auto-Provisioning

IRDoc automatically creates a new user account on first SSO login if no account with that email exists. Password login is not available for SSO-provisioned accounts (no password is set).

---

## Disabling SSO

To disable SSO, go to **Admin → SSO** and toggle SSO off. The login page SSO button is hidden. Existing SSO-provisioned users can use the forgot-password flow to set a password if needed.
