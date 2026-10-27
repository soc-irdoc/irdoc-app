"""Keep an install's own nginx config in step with the frontend image.

Where it lives (#114): the frontend image ships a default config, and an
install that needs its own (HTTPS, custom certs) keeps it in the git-ignored
docker/nginx/local/nginx.conf, which docker-compose.prod.yml mounts. Before
0.1.8 the live config was the tracked docker/nginx/nginx.conf, so server-side
edits blocked `git pull`; `adopt_edited_conf` moves such an edited file over.

Security headers (#57): they ship in the frontend image as a snippet. Old
installs have them written inline in their config instead, which upgrades
never touched. During an upgrade the wizard runs the image's own
`irdoc-nginx-migrate` script against the local file (see
frontend/nginx/irdoc-nginx-migrate.sh); docker/upgrade.sh does the same.
"""
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

MIGRATE_UPDATED = 0
MIGRATE_UNCHANGED = 10

_MOUNT = "/irdoc-nginx"

LOCAL_DIRNAME = "local"
CONF_NAME = "nginx.conf"

# sha256 (LF line endings) of every docker/nginx/nginx.conf IRDoc shipped. A
# file matching one of them was never edited on the server. Keep in step with
# SHIPPED_NGINX_SHA256 in docker/upgrade.sh.
SHIPPED_NGINX_CONF_SHA256 = frozenset({
    "f35bd18cfb20b0bb701f8d822d80dbdfa3b9869dc9a0623c5b296b3b5c3b7d78",
    "3302bf4ddf1e61feccdac26b8a0c8622e9e0d9a11b8481fcbb2d1dceb151105f",
    "832a486050493f5c927c68bdcf2dbc9cff4168e69bf9ee34558da1a03ce1df63",
})


def local_dir(nginx_dir: Path) -> Path:
    """docker/nginx/local: the install's own, git-ignored nginx config lives here."""
    return nginx_dir / LOCAL_DIRNAME


def is_shipped_default(conf: Path) -> bool:
    """True if conf is byte-for-byte (ignoring CR) a tracked nginx.conf IRDoc shipped."""
    digest = hashlib.sha256(conf.read_bytes().replace(b"\r", b"")).hexdigest()
    return digest in SHIPPED_NGINX_CONF_SHA256


def adopt_edited_conf(nginx_dir: Path) -> bool:
    """Move an edited tracked nginx.conf to local/nginx.conf (#114).

    Returns True if it did. The tracked file is put back with `git checkout`
    when it is in a git checkout, so the next `git pull` doesn't conflict.
    """
    tracked = nginx_dir / CONF_NAME
    local = local_dir(nginx_dir) / CONF_NAME
    local.parent.mkdir(parents=True, exist_ok=True)
    if local.exists() or not tracked.exists() or is_shipped_default(tracked):
        return False
    shutil.copy2(tracked, local)
    try:
        in_git = subprocess.run(
            ["git", "-C", str(nginx_dir), "ls-files", "--error-unmatch", CONF_NAME],
            capture_output=True,
        ).returncode == 0
    except FileNotFoundError:  # no git: a ZIP install
        in_git = False
    if in_git:
        subprocess.run(["git", "-C", str(nginx_dir), "checkout", "--", CONF_NAME], check=False)
    return True


def migrate_args(nginx_dir: Path) -> list[str]:
    """`docker compose` args that run the target image's migrate script on nginx_dir/nginx.conf.

    Pass local_dir(...): that is the config the frontend serves.
    """
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
    """Put the newest backup back over nginx.conf (in place, for installs that bind-mount it)."""
    backup = latest_backup(nginx_dir)
    if backup is None:
        return None
    with open(backup, "rb") as src, open(nginx_dir / "nginx.conf", "wb") as dst:
        shutil.copyfileobj(src, dst)
    return backup
