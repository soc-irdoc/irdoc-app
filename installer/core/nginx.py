"""Keep an install's host nginx.conf in step with the frontend image (#57).

The security headers ship in the frontend image as a snippet. Old installs
have them written inline in docker/nginx/nginx.conf instead, which upgrades
never touched. During an upgrade the wizard runs the image's own
`irdoc-nginx-migrate` script against that file (see
frontend/nginx/irdoc-nginx-migrate.sh); docker/upgrade.sh does the same.
"""
import os
import shutil
from pathlib import Path

MIGRATE_UPDATED = 0
MIGRATE_UNCHANGED = 10

_MOUNT = "/irdoc-nginx"


def migrate_args(nginx_dir: Path) -> list[str]:
    """`docker compose` args that run the target image's migrate script on nginx_dir/nginx.conf."""
    args = ["run", "--rm", "--no-deps", "-v", f"{nginx_dir}:{_MOUNT}"]
    # Run as the host user so the backup file isn't left owned by root.
    if hasattr(os, "getuid"):
        args += ["--user", f"{os.getuid()}:{os.getgid()}"]
    return args + ["--entrypoint", "irdoc-nginx-migrate", "frontend", f"{_MOUNT}/nginx.conf"]


def latest_backup(nginx_dir: Path) -> Path | None:
    """The newest nginx.conf.bak-<timestamp> the migrate script wrote, if any."""
    backups = sorted(nginx_dir.glob("nginx.conf.bak-*"))
    return backups[-1] if backups else None


def restore_backup(nginx_dir: Path) -> Path | None:
    """Put the newest backup back over nginx.conf, in place (it is bind-mounted as a file)."""
    backup = latest_backup(nginx_dir)
    if backup is None:
        return None
    with open(backup, "rb") as src, open(nginx_dir / "nginx.conf", "wb") as dst:
        shutil.copyfileobj(src, dst)
    return backup
