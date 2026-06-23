#!/usr/bin/env python3
"""
IrDoc Installation & Upgrade Wizard
Run: python3 installer/wizard.py
"""
import sys
from pathlib import Path as _Path
if __name__ == "__main__":
    sys.path.insert(0, str(_Path(__file__).parent.parent))

import os
import threading
import webbrowser
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from installer.core.config import read_existing_env
from installer.core.docker import detect_mode, COMPOSE_FILE

REPO_ROOT = Path(__file__).parent.parent
_INSTALLER_DIR = Path(__file__).parent
DOCKER_DIR = REPO_ROOT / "docker"
BACKUPS_DIR = REPO_ROOT / "backups"


def repo_version() -> str:
    version_file = REPO_ROOT / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "unknown"


class WizardState(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    # Detected wizard mode
    mode: str = "install"          # "install" | "upgrade" | "reconfigure"

    # Step 2 — HTTPS
    https_mode: Optional[str] = None  # "import" | "selfsigned" | "behind_lb"
    cert_pem: Optional[str] = None
    key_pem: Optional[str] = None
    cert_cn: Optional[str] = None
    cert_expiry: Optional[str] = None
    san_list: list[str] = []

    # Step 3 — URL
    base_url: str = ""

    # Step 4 — Secrets
    db_password: str = ""
    redis_password: str = ""
    secret_key: str = ""
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    license_key: str = ""

    # Step 5 — Admin account
    admin_name: Optional[str] = None
    admin_email: Optional[str] = None
    admin_password: Optional[str] = None

    # Upgrade state
    version_from: Optional[str] = None
    version_to: Optional[str] = None
    snapshot_dir: Optional[str] = None
    upgrade_failed_at: Optional[str] = None   # "migration" | "health"

    # Update check result
    update_available: Optional[str] = None    # newer version string or None


# Module-level singleton — single-user wizard
state = WizardState()

app = FastAPI(title="IrDoc Wizard")
app.mount("/static", StaticFiles(directory=str(_INSTALLER_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(_INSTALLER_DIR / "templates"))


def _template_context(request: Request, **extra) -> dict:
    return {
        "request": request,
        "state": state,
        "version": repo_version(),
        **extra,
    }


@app.on_event("startup")
async def on_startup():
    """Detect wizard mode and optionally check for updates on startup."""
    global state
    env_path = DOCKER_DIR / ".env"
    state.mode = detect_mode(env_path, repo_version())
    state.version_to = repo_version()

    if state.mode == "reconfigure":
        # Pre-fill secrets from existing .env
        existing = read_existing_env(env_path)
        state.db_password = existing.get("DB_PASSWORD", "")
        state.redis_password = existing.get("REDIS_PASSWORD", "")
        state.secret_key = existing.get("SECRET_KEY", "")
        state.base_url = existing.get("BASE_URL", "")
        state.license_key = existing.get("LICENSE_KEY", "")

    # Optional update check (skipped if IRDOC_NO_UPDATE_CHECK=1)
    if not os.environ.get("IRDOC_NO_UPDATE_CHECK"):
        try:
            import urllib.request, json as _json
            with urllib.request.urlopen(
                "https://api.github.com/repos/soc-irdoc/irdoc-app/releases/latest",
                timeout=3,
            ) as resp:
                data = _json.loads(resp.read())
                latest = data.get("tag_name", "").lstrip("v")
                if latest and latest != repo_version():
                    state.update_available = latest
        except Exception:
            pass


@app.get("/")
async def root():
    if state.mode in ("upgrade", ):
        return RedirectResponse("/upgrade/welcome")
    return RedirectResponse("/prerequisites")


if __name__ == "__main__":
    def _open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8888")

    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(
        "installer.wizard:app",
        host="127.0.0.1",
        port=8888,
        reload=False,
        log_level="warning",
    )
