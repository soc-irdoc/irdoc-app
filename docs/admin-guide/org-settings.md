# Organisation Settings

> **Admin role required.**

Org Settings is the central control panel for your IRDoc deployment — covering your organisation's display name, branding, registration policy, and license. Find it at **Admin → Org Settings**.

---

## Finding it

**Admin → Org Settings**

---

## Organisation name

Change the display name of your organisation as it appears throughout IRDoc — in the header, reports, and email notifications.

The org **slug** (used in internal identifiers) is set at initial setup and cannot be changed after installation. Changing the display name does not affect the slug or any URLs.

---

## Branding

| Field | Description |
|---|---|
| Logo URL | A publicly accessible image URL for your org logo. Shown in report headers and email notifications. |
| Accent color | Hex color code used for UI highlights and report styling (e.g. `#1a56db`). |

---

## Registration policy

| Policy | Behaviour |
|---|---|
| Open registration | Anyone who can reach the IRDoc URL can self-register an account. Corresponds to `ALLOW_REGISTRATION=true`. Use only in internal or closed environments. |
| Invite only | New accounts can only be created via admin invite or SSO auto-provisioning. Recommended for production deployments. |

Toggle between the two from this page. The change takes effect immediately.

---

## Plan & license

This section shows your current plan tier: **community** or **premium**.

To activate or update a license:

1. Paste your license key into the **License Key** field
2. Click **Save**

Premium features unlock immediately after a valid key is saved. If the key is invalid or expired, an error is shown and the tier does not change.

---

## Audit log

All changes made in Org Settings — including name, branding, registration policy, and license key updates — are recorded in the audit log.
