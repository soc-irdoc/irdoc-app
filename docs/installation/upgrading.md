# Upgrading IRDoc

IRDoc uses an automated upgrade script. All database migrations are backward-compatible — rolling upgrades are supported without downtime.

---

## One-Command Upgrade

```bash
cd docker
bash upgrade.sh           # upgrade to latest
bash upgrade.sh 1.1.0     # upgrade to a specific version
```

The script performs these steps in order:

1. **Pull new images** — downloads the new backend and frontend images from Docker Hub
2. **Run migrations** — executes `alembic upgrade head` in a temporary container (safe to run multiple times)
3. **Restart services** — replaces running containers with the new images
4. **Verify** — prints the running version to confirm success

---

## Manual Upgrade

If you prefer to run steps individually:

```bash
cd docker

# 1. Pull images
VERSION=1.1.0 docker compose -f docker-compose.prod.yml pull

# 2. Run migrations (before restarting the app)
VERSION=1.1.0 docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 3. Restart
VERSION=1.1.0 docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

---

## Migration Compatibility Guarantee

Every Alembic migration is written to be backward-compatible with the previous image version:

- No column drops (done in two migrations)
- No `NOT NULL` additions without defaults
- No table renames in a single migration

This means the new migration can run while the old image is still serving traffic, enabling zero-downtime upgrades.

---

## Before Upgrading

1. **Read the CHANGELOG** for the target version — check for any manual steps or config changes.
2. **Take a backup** — always back up before upgrading: `bash backup.sh`
3. **Check disk space** — Docker pulls can require several hundred MB free.

---

## Rollback

If something goes wrong, roll back to the previous version:

```bash
cd docker

# Run down-migration (if needed — check CHANGELOG)
VERSION=1.0.0 docker compose -f docker-compose.prod.yml run --rm backend alembic downgrade -1

# Restart with old version
VERSION=1.0.0 docker compose -f docker-compose.prod.yml up -d
```

Most migrations do not have a destructive downgrade — in that case, simply restarting with the old image is sufficient.
