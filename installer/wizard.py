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
import socket
import threading
import webbrowser
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from installer.core import ssl as ssl_core
from installer.core.config import generate_secrets, read_existing_env
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


def _template_context(**extra) -> dict:
    return {
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


@app.get("/prerequisites")
async def prerequisites(request: Request):
    import subprocess, sys
    checks = []

    def chk(label, ok, level, fix=""):
        checks.append({"label": label, "ok": ok, "level": level, "fix": fix})

    chk("Python ≥ 3.10", sys.version_info >= (3, 10), "block",
        "Install Python 3.10+ from https://python.org")

    try:
        r = subprocess.run(["docker", "--version"], capture_output=True, timeout=5)
        chk("Docker Engine installed", r.returncode == 0, "block",
            "Install Docker from https://docs.docker.com/engine/install/")
    except FileNotFoundError:
        chk("Docker Engine installed", False, "block",
            "Install Docker from https://docs.docker.com/engine/install/")

    try:
        r = subprocess.run(["docker", "compose", "version"], capture_output=True, timeout=5)
        chk("Docker Compose V2", r.returncode == 0, "block",
            "Upgrade Docker to 24+ or install the compose plugin")
    except FileNotFoundError:
        chk("Docker Compose V2", False, "block", "Install Docker Compose V2 plugin")

    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        chk("Docker daemon running", r.returncode == 0, "block",
            "Run: sudo systemctl start docker")
    except Exception:
        chk("Docker daemon running", False, "block", "Run: sudo systemctl start docker")

    chk("docker/ directory found", (DOCKER_DIR).exists(), "block",
        "Run the wizard from the repo root: python3 installer/wizard.py")

    # Port checks (warn only)
    for port, label in [(443, "Port 443"), (80, "Port 80")]:
        import socket as _socket
        with _socket.socket() as s:
            result = s.connect_ex(("127.0.0.1", port))
            chk(f"{label} available", result != 0, "warn",
                f"Something is using port {port}. Check with: sudo lsof -i :{port}")

    hard_blocked = any(c["level"] == "block" and not c["ok"] for c in checks)
    return templates.TemplateResponse(request, "prerequisites.html",
        _template_context(checks=checks, hard_blocked=hard_blocked))


@app.get("/https-mode")
async def https_mode_page(request: Request):
    hostname = socket.getfqdn()
    return templates.TemplateResponse(request, "https_mode.html",
        _template_context(hostname=hostname))


@app.post("/https-mode/set")
async def set_https_mode(mode: str = Form(...)):
    state.https_mode = mode
    if mode == "selfsigned":
        return RedirectResponse("/https-mode/selfsigned", status_code=302)
    # "behind_lb" — no cert needed, go straight to core config
    return RedirectResponse("/core-config", status_code=302)


@app.get("/https-mode/selfsigned")
async def selfsigned_page(request: Request):
    hostname = socket.getfqdn()
    return templates.TemplateResponse(request, "https_mode.html",
        _template_context(hostname=hostname, show_selfsigned=True))


@app.post("/https-mode/generate-selfsigned")
async def generate_selfsigned(
    common_name: str = Form(...),
    san: str = Form(""),
):
    san_list = [s.strip() for s in san.split(",") if s.strip()]
    cert_pem, key_pem = ssl_core.generate_self_signed(common_name, san_list)
    state.https_mode = "selfsigned"
    state.cert_pem = cert_pem
    state.key_pem = key_pem
    state.cert_cn = common_name
    state.san_list = san_list
    return RedirectResponse("/core-config", status_code=302)


@app.post("/https-mode/upload-pfx")
async def upload_pfx(
    request: Request,
    pfx_file: UploadFile = File(...),
    passphrase: str = Form(...),
):
    pfx_bytes = await pfx_file.read()
    hostname = socket.getfqdn()
    try:
        cert_pem, key_pem, cn, expiry = ssl_core.parse_pfx(pfx_bytes, passphrase)
    except ValueError as e:
        return templates.TemplateResponse(request, "https_mode.html",
            _template_context(hostname=hostname, pfx_error=str(e)))
    state.https_mode = "import"
    state.cert_pem = cert_pem
    state.key_pem = key_pem
    state.cert_cn = cn
    state.cert_expiry = expiry
    return RedirectResponse("/core-config", status_code=302)


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
