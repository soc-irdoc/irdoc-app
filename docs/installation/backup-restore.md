# Backup & Restore

---

## Automated Backup

Run the backup script manually or schedule it via cron:

```bash
cd docker
bash backup.sh
```

This backs up:
1. **PostgreSQL database** — all incident data, users, reports, configs
2. **Local storage files** — evidence attachments and generated reports (local backend only)

Backups are saved to `docker/backups/` and rotated after 30 days.

### Schedule via cron (recommended: daily at 02:00)

```cron
0 2 * * * /opt/irpdoc/docker/backup.sh >> /var/log/irpdoc-backup.log 2>&1
```

---

## Manual Backup

### Database

```bash
cd docker
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U irp irp | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Storage files (local backend)

```bash
tar -czf storage_$(date +%Y%m%d).tar.gz ./storage/
```

---

## Restore

### Database

```bash
cd docker

# Stop the backend to prevent writes during restore
docker compose -f docker-compose.prod.yml stop backend worker beat

# Restore
zcat backups/db_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db psql -U irp irp

# Restart
docker compose -f docker-compose.prod.yml start backend worker beat
```

### Storage files (local backend)

```bash
tar -xzf backups/storage_YYYYMMDD_HHMMSS.tar.gz -C docker/
```

---

## Verify Integrity After Restore

IRDoc stores SHA-256 hashes for every attachment. After a restore, verify a sample:

```bash
docker compose -f docker-compose.prod.yml exec backend python -c "
from app.services.attachment_service import verify_all_hashes
results = verify_all_hashes(sample_size=100)
print(f'Verified: {results.ok}/{results.total} | Mismatches: {results.mismatches}')
"
```

If mismatches are found, the restore may be incomplete or the storage files may be corrupted.

---

## Cloud Storage Backends

If you use S3, Azure Blob, or GCS as your storage backend, those files are **not** backed up by this script — they are managed by your cloud provider's built-in redundancy and versioning.

Back up only the database in that case. The database contains the `storage_path` and `sha256` for every attachment — sufficient to verify integrity.
