# Setting Up Multi-Factor Authentication

IRDoc supports TOTP-based MFA, which works with any authenticator app — Google Authenticator, Authy, Microsoft Authenticator, 1Password, Bitwarden, and others. If your organisation has made MFA mandatory, you will be prompted to complete setup on your next login before you can access anything else.

---

## Enable MFA

1. Click your avatar in the top-right corner and select **Settings**
2. Go to **Settings → Security**
3. Click **Enable Two-Factor Authentication**
4. A QR code is displayed — open your authenticator app, tap the option to add a new account, and scan the code
5. Enter the 6-digit code currently shown in your app to confirm the setup
6. IRDoc displays **10 backup codes** — copy or download them and store them somewhere safe

Setup is complete. MFA will be required on your next login.

---

## Backup Codes

Backup codes let you log in if you cannot access your authenticator app. Each code is single-use — once used, it is crossed off and cannot be used again.

**To regenerate backup codes:**

1. Go to **Settings → Security**
2. Click **Regenerate Backup Codes**
3. Copy or download the new codes immediately

Regenerating a new set immediately invalidates all existing backup codes. If you have any codes stored elsewhere, discard them and replace them with the new set.

---

## Log In with MFA

1. Enter your email and password as normal
2. When the MFA prompt appears, open your authenticator app and enter the current 6-digit code
3. If you do not have your phone, enter one of your backup codes instead

---

## Disable MFA

1. Go to **Settings → Security**
2. Click **Disable Two-Factor Authentication**
3. Confirm when prompted

> If your organisation has enforced MFA for all users, the disable option will be greyed out. Contact your admin if you need an exemption.

---

## Lost Access to Your Authenticator App

If you can no longer generate codes from your authenticator app:

1. Use a backup code to log in (enter it at the MFA prompt in place of a 6-digit code)
2. After logging in, go to **Settings → Security**
3. Click **Reset Two-Factor Authentication** to register a new device

If you have no backup codes remaining, contact your admin — they can reset MFA for your account from **Admin → Users**.
