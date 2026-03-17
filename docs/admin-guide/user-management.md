# User Management

---

## Roles

| Role | Capabilities |
|---|---|
| **Viewer** | Read-only access to all incident data; can generate reports |
| **Analyst** | Create/edit own timeline entries, add IOCs, create incidents |
| **Senior Analyst** | All analyst permissions + delete any entry, close incidents, manage templates, manage sync policies, containment actions |
| **Admin** | All permissions + manage users, API keys, integrations, storage, audit log |

Roles are enforced server-side on every API route. Frontend permission checks are supplementary only.

---

## Inviting Users

> **Admin role required.**

1. Go to **Admin → Team**
2. Click **Invite Member**
3. Enter the email address and select a role
4. Click **Send Invite**

IRDoc sends an invite email with a link valid for 48 hours. If `EMAIL_BACKEND=console`, the invite link is printed to the backend logs.

The invited user clicks the link, sets a password, and is automatically logged in.

---

## Changing a User's Role

1. Go to **Admin → Team**
2. Click the role dropdown on the user row
3. Select the new role — change takes effect immediately

**Last-admin guard:** IRDoc prevents you from demoting or deactivating the last admin in the org. You will receive an error if you try. Promote another user to admin first.

---

## Deactivating a User

Deactivated users cannot log in. Their timeline entries and audit log entries are preserved.

1. Go to **Admin → Team**
2. Click **Deactivate** on the user row
3. Confirm the action

To reactivate, contact the database administrator (there is no UI for reactivation in v1.0).

---

## SSO / SAML

Premium feature. See [SSO / SAML](sso-saml.md) for setup.

When SSO is enabled, users can sign in via your IdP. IRDoc auto-provisions accounts on first SSO login based on the role mappings you configure.

Password-based login remains available as a fallback unless you disable `ALLOW_REGISTRATION` and revoke existing passwords via API.

---

## Registration Policy

In **Admin → Org Settings**, you can control whether new accounts can self-register:

- **Open registration** (`ALLOW_REGISTRATION=true`) — anyone with the URL can create an account. Default in dev.
- **Invite only** (`ALLOW_REGISTRATION=false`) — accounts can only be created via admin invite or SSO auto-provision. Recommended for production.
