import asyncio
import subprocess
from pathlib import Path
from typing import AsyncGenerator

# Absolute path to the prod compose file, relative to this file's location
_REPO_ROOT = Path(__file__).parent.parent.parent
COMPOSE_FILE = str(_REPO_ROOT / "docker" / "docker-compose.prod.yml")


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

    cmd = ["docker", "compose", "-f", COMPOSE_FILE] + args
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
