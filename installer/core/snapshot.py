import asyncio
import hashlib
import json
import os
import shutil
import stat
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


async def take_snapshot(snapshot_dir: Path, version_from: str, version_to: str) -> Path:
    """Create full backup: env + ssl + pg_dump + storage tar. Returns snapshot_dir."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(snapshot_dir, stat.S_IRWXU)  # 0o700

    docker_dir = _REPO_ROOT / "docker"
    files_recorded = []

    # 1. Backup .env
    env_src = docker_dir / ".env"
    if env_src.exists():
        shutil.copy2(env_src, snapshot_dir / "env.bak")
        files_recorded.append("env.bak")

    # 2. Backup ssl/
    ssl_src = docker_dir / "ssl"
    if ssl_src.exists():
        ssl_dst = snapshot_dir / "ssl"
        shutil.copytree(ssl_src, ssl_dst)
        files_recorded.append("ssl/")

    # 3. pg_dump via docker exec
    dump_path = snapshot_dir / "dump.sql"
    proc = await asyncio.create_subprocess_exec(
        "docker", "exec", "irdoc-db",
        "pg_dump", "-U", "irp", "-d", "irp", "--no-password",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {stderr.decode()}")
    dump_path.write_bytes(stdout)
    files_recorded.append("dump.sql")

    # 4. Storage files
    storage_src = _REPO_ROOT / "storage"
    if storage_src.exists():
        tar_path = snapshot_dir / "storage.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(storage_src, arcname="storage")
        files_recorded.append("storage.tar.gz")

    # 5. Write manifest
    checksums = {}
    for fname in ["dump.sql", "storage.tar.gz"]:
        fpath = snapshot_dir / fname
        if fpath.exists():
            checksums[fname] = _sha256(fpath)

    manifest = {
        "version_from": version_from,
        "version_to": version_to,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "files": files_recorded,
        "checksums": checksums,
    }
    (snapshot_dir / "snapshot.json").write_text(json.dumps(manifest, indent=2))

    return snapshot_dir


async def restore_snapshot(snapshot_dir: Path) -> None:
    """Restore from a snapshot directory. Containers must be stopped before calling."""
    docker_dir = _REPO_ROOT / "docker"
    manifest = json.loads((snapshot_dir / "snapshot.json").read_text())

    # Restore .env
    env_bak = snapshot_dir / "env.bak"
    if env_bak.exists():
        shutil.copy2(env_bak, docker_dir / ".env")
        os.chmod(docker_dir / ".env", stat.S_IRUSR | stat.S_IWUSR)

    # Restore ssl/
    ssl_bak = snapshot_dir / "ssl"
    if ssl_bak.exists():
        ssl_dst = docker_dir / "ssl"
        if ssl_dst.exists():
            shutil.rmtree(ssl_dst)
        shutil.copytree(ssl_bak, ssl_dst)

    # Restore database: start a temporary postgres container to restore into
    dump_path = snapshot_dir / "dump.sql"
    if dump_path.exists():
        # Remove existing postgres volume and recreate
        proc_rm = await asyncio.create_subprocess_exec(
            "docker", "volume", "rm", "-f", "irdoc-app_postgres_data",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await proc_rm.wait()  # must complete before the volume is re-mounted below
        proc_wait = await asyncio.create_subprocess_exec(
            "docker", "run", "--rm",
            "-v", "irdoc-app_postgres_data:/var/lib/postgresql/data",
            "-e", "POSTGRES_DB=irp", "-e", "POSTGRES_USER=irp", "-e", "POSTGRES_PASSWORD=restore",
            "postgres:16-alpine",
            "postgres", "-c", "listen_addresses=''",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        # Give postgres a moment to initialise, then restore
        await asyncio.sleep(5)
        proc_wait.kill()
        await proc_wait.wait()  # must exit before psql mounts the same volume

        restore_proc = await asyncio.create_subprocess_exec(
            "docker", "run", "--rm", "-i",
            "-v", "irdoc-app_postgres_data:/var/lib/postgresql/data",
            "-e", "PGPASSWORD=restore",
            "postgres:16-alpine",
            "psql", "-U", "irp", "-d", "irp",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await restore_proc.communicate(input=dump_path.read_bytes())
        if restore_proc.returncode != 0:
            raise RuntimeError(f"Database restore failed: {stderr.decode()}")

    # Restore storage files
    tar_path = snapshot_dir / "storage.tar.gz"
    if tar_path.exists():
        storage_dst = _REPO_ROOT / "storage"
        if storage_dst.exists():
            shutil.rmtree(storage_dst)
        with tarfile.open(tar_path, "r:gz") as tar:
            if sys.version_info >= (3, 12):
                tar.extractall(_REPO_ROOT, filter="data")
            else:
                tar.extractall(_REPO_ROOT)


def list_snapshots(backups_root: Path) -> list[dict]:
    """Return list of snapshot dicts sorted by timestamp ascending."""
    snapshots = []
    if not backups_root.exists():
        return []
    for entry in backups_root.iterdir():
        manifest_path = entry / "snapshot.json"
        if manifest_path.exists():
            try:
                data = json.loads(manifest_path.read_text())
                data["path"] = str(entry)
                snapshots.append(data)
            except Exception:
                continue
    return sorted(snapshots, key=lambda s: s.get("timestamp", ""))
