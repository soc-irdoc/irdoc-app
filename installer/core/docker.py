import asyncio
import subprocess
from pathlib import Path
from typing import AsyncGenerator

# Absolute path to the prod compose file, relative to this file's location
_REPO_ROOT = Path(__file__).parent.parent.parent
COMPOSE_FILE = str(_REPO_ROOT / "docker" / "docker-compose.prod.yml")
# An install's own compose changes, git-ignored so `git pull` never conflicts
# with them (#162). Added on top of the prod file whenever it exists.
LOCAL_COMPOSE_FILE = str(_REPO_ROOT / "docker" / "docker-compose.local.yml")


def compose_base_cmd() -> list[str]:
    """`docker compose -f prod [-f local]`, the same files upgrade.sh uses."""
    cmd = ["docker", "compose", "-f", COMPOSE_FILE]
    if Path(LOCAL_COMPOSE_FILE).exists():
        cmd += ["-f", LOCAL_COMPOSE_FILE]
    return cmd


def local_docker_edits() -> list[str]:
    """Tracked files under docker/ with local changes (git status lines)."""
    try:
        r = subprocess.run(
            ["git", "-C", str(_REPO_ROOT / "docker"), "status", "--porcelain",
             "--untracked-files=no", "--", "."],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0:
        return []
    return [line for line in r.stdout.splitlines() if line.strip()]


async def run_compose(
    args: list[str],
    env_override: dict | None = None,
) -> AsyncGenerator[str, None]:
    """
    Run a docker compose command and yield SSE-formatted lines.
    Yields 'data: <line>' strings. Final yield: 'data: __EXIT__<returncode>'.
    """
    import os
    env = os.environ.copy()
    if env_override:
        env.update(env_override)

    cmd = compose_base_cmd() + args
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )
    async for line in proc.stdout:
        decoded = line.decode(errors="replace").rstrip()
        yield f"data: {decoded}\n\n"
    await proc.wait()
    yield f"data: __EXIT__{proc.returncode}\n\n"


def get_installed_version_sync() -> str | None:
    """Read image tag from the running irdoc-backend container. Returns None if not running."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "irdoc-backend", "--format", "{{.Config.Image}}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        image = result.stdout.strip()
        # image is e.g. "soc-irdoc/irdoc-backend:1.2.0" or "soc-irdoc/irdoc-backend:latest"
        tag = image.split(":")[-1] if ":" in image else None
        return tag if tag and tag != "latest" else None
    except Exception:
        return None


def detect_mode(docker_env_path: Path, repo_version: str) -> str:
    """
    Returns 'install', 'upgrade', or 'reconfigure'.
    - install: no docker/.env found
    - reconfigure: .env found and installed version matches repo_version
    - upgrade: .env found but versions differ (or container not running)
    """
    if not docker_env_path.exists():
        return "install"
    installed = get_installed_version_sync()
    if installed == repo_version:
        return "reconfigure"
    return "upgrade"
