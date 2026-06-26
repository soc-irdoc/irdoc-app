# MFA Enforcement

> **Admin role required.**

Org-wide MFA enforcement requires every user in the organisation to have MFA configured before they can access IRDoc. Once enabled, users without MFA are redirected to the enrollment flow on their next login and cannot proceed until setup is complete.

---

## What org-wide MFA enforcement does

- Every user must have MFA set up to access IRDoc
- On their next login, users without MFA are redirected to the MFA setup flow before they can proceed
- Users cannot disable their own MFA while enforcement is active — the disable button is greyed out with an explanatory message

---

## Enabling enforcement

1. Go to **Admin → Org Settings**
2. Toggle **Require MFA for all users** to on
3. Click **Save**

From that point, any user without MFA will be forced to enroll on their next login.

---

## Checking enrollment status

- The Admin Dashboard shows MFA enrollment rate as a percentage (e.g. "14 of 16 users enrolled")
- **Admin → Team** shows each user's MFA status in their row

---

## Disabling enforcement

1. Go to **Admin → Org Settings**
2. Toggle **Require MFA for all users** off
3. Click **Save**

Existing MFA enrollments remain in place. Users can now disable MFA from their own profile settings if they choose.

---

## Admin reset (locked-out users)

If a user is locked out — they have lost their authenticator app and their backup codes — an admin can clear their MFA so they can re-enroll:

1. Go to **Admin → Team**
2. Find the user row and click the **...** menu
3. Select **Reset MFA**

The user's MFA configuration is cleared. They will be prompted to re-enroll on their next login.

---

## Recommendation

Enable MFA enforcement before inviting your team. Users who set up MFA as part of accepting an invite never experience a login interruption — they go through enrollment during the invite acceptance flow before they have ever logged in.
