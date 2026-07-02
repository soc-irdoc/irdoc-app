# Backup Management

> **Admin role required.**

IRDoc has a built-in scheduled backup system accessible from the admin panel. Go to **Admin → Backups**.

This page covers the **in-app backup scheduler**. For manual backup procedures via the command line, see [Backup & Restore](../installation/backup-restore.md). The upgrade wizard also creates automatic pre-upgrade snapshots (see [Wizard](../installation/wizard.md)).

---

## Enabling scheduled backups

1. Go to **Admin → Backups**
2. Toggle **Enable Scheduled Backups** on
3. Set the schedule and retention, then click **Save**

| Setting | Options |
|---|---|
| Schedule | Every 6 hours, Daily (default: 02:00), Weekly (default: Sunday 02:00), Monthly |
| Retention | Number of days to keep backups before auto-deletion (default: 30) |
| Destination | `local` — saved to the `backups/` directory on the host |

---

## What a backup includes

- Full PostgreSQL database dump (all incidents, timeline entries, IOCs, tasks, reports, users, templates)
- Storage files (evidence attachments and generated reports) — only when using the local storage backend; S3/Azure/GCS files are managed by your cloud provider

---

## Viewing backups

The backup list shows:

- Backup timestamp
- File size
- Status: `completed`, `in_progress`, `failed`
- Last error message (if status is `failed`)

---

## Manual backup

Click **Run Backup Now** to trigger an immediate backup outside of the schedule. The backup runs in the background — refresh the page to see the updated status.

---

## Downloading a backup

Click the download icon on any completed backup entry to download the backup archive.

---

## Restoring from a backup

Automated restore is not available through the UI. To restore:

1. Download the backup archive from the backup list
2. Follow the command-line restore procedure in [Backup & Restore](../installation/backup-restore.md)

---

## Troubleshooting

- If a backup shows `failed`, check the error message on the row and ensure Docker has write access to the `backups/` directory
- The backup process requires the `irdoc-db` container to be running
