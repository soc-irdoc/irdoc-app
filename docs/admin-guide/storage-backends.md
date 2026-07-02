# Storage Backends

IRDoc uses a pluggable storage backend for all file uploads (evidence attachments, generated reports). You can switch backends at runtime from the admin panel without redeployment.

---

## Backends

### Local (default, core)

Files are stored on the container filesystem at `STORAGE_PATH` (`/app/storage` by default), mounted as a Docker volume.

**Use when:** Self-hosting on a single server, development, evaluation.

**Production note:** Mount a persistent volume and include it in your backup rotation. See [Backup & Restore](../installation/backup-restore.md).

---

### S3-Compatible

Supports Amazon S3, MinIO, Cloudflare R2, Wasabi, and any S3-compatible provider.

**Configuration (Admin → Storage → S3):**

| Field | Description |
|---|---|
| Bucket | S3 bucket name |
| Region | AWS region (e.g., `us-east-1`). Use any value for non-AWS providers. |
| Access Key ID | IAM access key |
| Secret Access Key | IAM secret key |
| Endpoint URL | Leave empty for AWS S3. For MinIO/R2: `https://your-minio-host` |

The IAM user needs: `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`, `s3:GetBucketLocation`.

File URLs are presigned S3 URLs (1-hour expiry, re-generated on each download request).

---

### Azure Blob Storage

**Configuration (Admin → Storage → Azure Blob):**

| Field | Description |
|---|---|
| Account Name | Azure storage account name |
| Account Key | Storage account access key |
| Container Name | Blob container name (must exist, private access) |

File URLs are SAS (Shared Access Signature) URLs with 1-hour expiry.

---

### Google Cloud Storage

**Configuration (Admin → Storage → GCS):**

| Field | Description |
|---|---|
| Bucket Name | GCS bucket name |
| Service Account JSON | Full JSON content of a service account key file |

The service account needs `storage.objects.create`, `storage.objects.get`, `storage.objects.delete` on the bucket.

File URLs are v4 signed URLs with 1-hour expiry.

---

## Switching Backends

1. Go to **Admin → Storage**
2. Configure the new backend credentials
3. Click **Test Connection** — verify the connection succeeds before switching
4. Click **Save & Switch**

The switch is instant. New uploads immediately use the new backend.

**Important:** Existing file URLs point to the old backend and remain valid as long as the old backend is accessible. IRDoc does **not** migrate existing files automatically. If you need to migrate files, copy them manually before switching, or keep the old backend accessible.

SHA-256 hashes in the database are independent of the storage backend — integrity verification always works.
