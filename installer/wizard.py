#!/usr/bin/env python3
"""
IrDoc Installation & Upgrade Wizard
Run: python3 installer/wizard.py
"""
import sys
from pathlib import Path as _Path
if __name__ == "__main__":
    sys.path.insert(0, str(_Path(__file__).parent.parent))

import asyncio
import httpx
import os
import shutil
import signal
import socket
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from installer.core import ssl as ssl_core
from installer.core.config import assemble_env, generate_secrets, read_existing_env, write_env
from installer.core.docker import detect_mode, run_compose, COMPOSE_FILE
from installer.core.health import wait_for_health
from installer.core.snapshot import take_snapshot, list_snapshots
from installer.core.ssl import write_certs, generate_nginx_conf

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


@app.get("/core-config")
async def core_config_page(request: Request):
    if not state.db_password:
        secrets = generate_secrets()
        state.db_password = secrets["db_password"]
        state.redis_password = secrets["redis_password"]
        state.secret_key = secrets["secret_key"]
    if not state.base_url:
        prefix = "http" if state.https_mode == "behind_lb" else "https"
        state.base_url = f"{prefix}://{socket.getfqdn()}"
    return templates.TemplateResponse(request, "core_config.html", _template_context())


@app.get("/api/generate-secrets")
async def generate_secrets_api():
    return JSONResponse(generate_secrets())


@app.post("/core-config")
async def save_core_config(
    base_url: str = Form(...),
    db_password: str = Form(...),
    redis_password: str = Form(...),
    secret_key: str = Form(...),
    access_token_expire_minutes: int = Form(15),
    refresh_token_expire_days: int = Form(30),
    license_key: str = Form(""),
):
    state.base_url = base_url.rstrip("/")
    state.db_password = db_password
    state.redis_password = redis_password
    state.secret_key = secret_key
    state.access_token_expire_minutes = access_token_expire_minutes
    state.refresh_token_expire_days = refresh_token_expire_days
    state.license_key = license_key
    return RedirectResponse("/admin-user", status_code=302)


@app.get("/admin-user")
async def admin_user_page(request: Request):
    return templates.TemplateResponse(request, "admin_user.html", _template_context())


@app.post("/admin-user")
async def save_admin_user(
    request: Request,
    admin_name: str = Form(...),
    admin_email: str = Form(...),
    admin_password: str = Form(...),
    admin_password_confirm: str = Form(...),
):
    errors = {}
    if len(admin_password) < 12:
        errors["admin_password"] = "Password must be at least 12 characters."
    if admin_password != admin_password_confirm:
        errors["admin_password_confirm"] = "Passwords do not match."
    if errors:
        return templates.TemplateResponse(
            request, "admin_user.html",
            _template_context(errors=errors, admin_name=admin_name, admin_email=admin_email),
            status_code=422,
        )
    state.admin_name = admin_name
    state.admin_email = admin_email
    state.admin_password = admin_password
    return RedirectResponse("/review", status_code=302)


_deploy_log: list[str] = []
_deploy_done: bool = False
_deploy_success: bool = False


@app.get("/review")
async def review_page(request: Request):
    return templates.TemplateResponse(request, "review.html", _template_context())


@app.post("/review/confirm")
async def review_confirm():
    # Write docker/.env
    env_content = assemble_env({
        "db_password": state.db_password,
        "redis_password": state.redis_password,
        "secret_key": state.secret_key,
        "base_url": state.base_url,
        "access_token_expire_minutes": state.access_token_expire_minutes,
        "refresh_token_expire_days": state.refresh_token_expire_days,
        "license_key": state.license_key,
    })
    write_env(DOCKER_DIR / ".env", env_content)

    # Write nginx.conf
    nginx_conf = generate_nginx_conf(state.https_mode or "behind_lb")
    nginx_path = DOCKER_DIR / "nginx" / "nginx.conf"
    nginx_path.write_text(nginx_conf)

    # Write SSL certs if applicable
    if state.cert_pem and state.key_pem:
        write_certs(DOCKER_DIR / "ssl", state.cert_pem, state.key_pem)

    return RedirectResponse("/deploy", status_code=302)


@app.get("/deploy")
async def deploy_page(request: Request):
    return templates.TemplateResponse(request, "deploy.html", _template_context())


@app.get("/deploy/stream")
async def deploy_stream():
    async def event_generator():
        global _deploy_log, _deploy_done, _deploy_success
        _deploy_log = []
        _deploy_done = False
        _deploy_success = False

        try:
            # Step: Pull images
            yield "data: __STEP__Pulling images\n\n"
            async for line in run_compose(["pull"]):
                yield line
                if "__EXIT__0" in line:
                    pass
                elif "__EXIT__" in line:
                    yield "data: __FAIL__Image pull failed\n\n"
                    _deploy_done = True
                    return

            # Step: Start containers
            yield "data: __STEP__Starting containers\n\n"
            async for line in run_compose(["up", "-d", "--remove-orphans"]):
                yield line
                if "__EXIT__" in line and "__EXIT__0" not in line:
                    yield "data: __FAIL__Container start failed\n\n"
                    _deploy_done = True
                    return

            # Step: Health check
            yield "data: __STEP__Waiting for health check\n\n"
            healthy = await wait_for_health(state.base_url or "http://localhost")
            if not healthy:
                yield "data: __FAIL__Health check timed out\n\n"
                _deploy_done = True
                return
            yield "data: Health check passed\n\n"

            # Step: Seed admin
            yield "data: __STEP__Creating admin account\n\n"
            # verify=False is intentional: the wizard may have just generated a
            # self-signed cert; no CA bundle can validate it yet.
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:  # noqa: S501
                resp = await client.post(
                    f"{state.base_url}/api/v1/auth/setup",
                    json={
                        "email": state.admin_email,
                        "full_name": state.admin_name,
                        "password": state.admin_password,
                        "org_name": "Default Organization",
                    },
                )
                if resp.status_code not in (200, 201, 409):
                    yield f"data: __FAIL__Admin creation failed: {resp.status_code}\n\n"
                    _deploy_done = True
                    return
            yield "data: Admin account ready\n\n"

            yield "data: __DONE__\n\n"
            _deploy_success = True

        except Exception as e:
            yield f"data: __FAIL__{e}\n\n"
        finally:
            _deploy_done = True

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/success")
async def success_page(request: Request):
    def _exit():
        import time
        time.sleep(2.0)
        os.kill(os.getpid(), signal.SIGTERM)
    threading.Thread(target=_exit, daemon=True).start()
    return templates.TemplateResponse(request, "success.html", _template_context())


@app.get("/upgrade/welcome")
async def upgrade_welcome(request: Request):
    import subprocess, json
    container_statuses = []
    try:
        r = subprocess.run(
            ["docker", "compose", "-f", COMPOSE_FILE, "ps", "--format", "json"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0 and r.stdout.strip():
            for line in r.stdout.strip().splitlines():
                try:
                    container_statuses.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass

    disk = shutil.disk_usage(".")
    disk_free_gb = disk.free / (1024 ** 3)

    storage_dir = REPO_ROOT / "storage"
    storage_size = "unknown"
    if storage_dir.exists():
        try:
            r2 = subprocess.run(["du", "-sh", str(storage_dir)], capture_output=True, text=True)
            storage_size = r2.stdout.split()[0] if r2.returncode == 0 else "unknown"
        except Exception:
            pass

    return templates.TemplateResponse(request, "upgrade_welcome.html", _template_context(
        containers=container_statuses,
        disk_free_gb=round(disk_free_gb, 1),
        storage_size=storage_size,
    ))


@app.post("/upgrade/start")
async def upgrade_start():
    return RedirectResponse("/upgrade/snapshot", status_code=302)


@app.get("/upgrade/snapshot")
async def upgrade_snapshot_page(request: Request):
    return templates.TemplateResponse(request, "snapshot.html", _template_context())


@app.get("/upgrade/snapshot/stream")
async def upgrade_snapshot_stream():
    async def generator():
        try:
            ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
            snapshot_dir = BACKUPS_DIR / f"pre-upgrade-{ts}"
            yield "data: __TASK__Backing up configuration\n\n"
            yield "data: __TASK__Backing up database\n\n"
            yield "data: __TASK__Backing up storage files\n\n"
            result_dir = await take_snapshot(
                snapshot_dir,
                version_from=state.version_from or "unknown",
                version_to=state.version_to or "unknown",
            )
            state.snapshot_dir = str(result_dir)
            yield "data: __TASK__Writing snapshot manifest\n\n"
            yield "data: __DONE__\n\n"
        except Exception as e:
            yield f"data: __FAIL__{e}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/upgrade/progress")
async def upgrade_progress_page(request: Request):
    return templates.TemplateResponse(request, "upgrade_progress.html", _template_context())


@app.get("/upgrade/progress/stream")
async def upgrade_progress_stream():
    async def generator():
        try:
            # Step: Pull new images
            yield "data: __STEP__Pulling new images\n\n"
            async for line in run_compose(["pull"]):
                yield line
                if "__EXIT__" in line and "__EXIT__0" not in line:
                    yield "data: __FAIL__Image pull failed\n\n"
                    return

            # Step: Stop containers
            yield "data: __STEP__Stopping containers\n\n"
            async for line in run_compose(["stop"]):
                yield line

            # Step: Run migrations
            yield "data: __STEP__Running database migrations\n\n"
            async for line in run_compose(
                ["run", "--rm", "irdoc-backend", "alembic", "upgrade", "head"]
            ):
                yield line
                if "__EXIT__" in line and "__EXIT__0" not in line:
                    state.upgrade_failed_at = "migration"
                    yield "data: __FAIL__Migration failed\n\n"
                    return

            # Step: Start containers
            yield "data: __STEP__Starting containers\n\n"
            async for line in run_compose(["up", "-d", "--remove-orphans"]):
                yield line

            # Step: Health check
            yield "data: __STEP__Health check\n\n"
            base = state.base_url or "http://localhost"
            healthy = await wait_for_health(base)
            if not healthy:
                state.upgrade_failed_at = "health"
                yield "data: __FAIL__Health check timed out\n\n"
                return

            yield "data: __DONE__\n\n"

        except Exception as e:
            yield f"data: __FAIL__{e}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/upgrade/success")
async def upgrade_success(request: Request):
    def _exit():
        import time
        time.sleep(2.0)
        os.kill(os.getpid(), signal.SIGTERM)
    threading.Thread(target=_exit, daemon=True).start()
    return templates.TemplateResponse(request, "upgrade_success.html", _template_context())


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
