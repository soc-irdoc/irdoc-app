"""Regression tests for #57: upgrades bring an old host nginx.conf over to the
security-headers snippet shipped in the frontend image.

Runs the real frontend/nginx/irdoc-nginx-migrate.sh (the script both upgrade
paths run inside the frontend image) against nginx configs from past releases.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from installer.core import nginx as nginx_core
from installer.core.ssl import SECURITY_HEADERS_SNIPPET, generate_nginx_conf

REPO_ROOT = Path(__file__).parent.parent.parent
SCRIPT = REPO_ROOT / "frontend" / "nginx" / "irdoc-nginx-migrate.sh"
SNIPPET = REPO_ROOT / "frontend" / "nginx" / "irdoc-security-headers.conf"
SELECT_SCRIPT = REPO_ROOT / "frontend" / "nginx" / "90-irdoc-select-conf.sh"
FIXTURES = Path(__file__).parent / "fixtures" / "nginx"

INCLUDE = f"include {SECURITY_HEADERS_SNIPPET};"
MOVED_HEADERS = re.compile(
    r"^\s*add_header\s+(Content-Security-Policy|X-Frame-Options|X-Content-Type-Options"
    r"|Referrer-Policy|Permissions-Policy)\s",
    re.MULTILINE,
)

# Configs real installs may have, oldest first.
OLD_CONFIGS = [
    "demo-https-pre-0.1.2.conf",  # the demo VPS config from the issue (no img-src)
    "demo-https-0.1.5.conf",
    "behind-lb-0.1.5.conf",       # wizard output, behind a load balancer
    "default-http-0.1.5.conf",    # tracked default (plain HTTP, three headers)
]

needs_sh = pytest.mark.skipif(
    not (shutil.which("sh") and shutil.which("awk")), reason="needs sh and awk"
)


def _migrate(conf: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["sh", str(SCRIPT), str(conf)], capture_output=True, text=True)


def _server_blocks(conf: str) -> list[str]:
    return re.split(r"^\s*server\s*\{", conf, flags=re.MULTILINE)[1:]


@needs_sh
@pytest.mark.parametrize("fixture", OLD_CONFIGS)
def test_old_config_is_switched_to_the_snippet(tmp_path, fixture):
    original = (FIXTURES / fixture).read_text(encoding="utf-8")
    conf = tmp_path / "nginx.conf"
    conf.write_text(original, encoding="utf-8", newline="\n")

    result = _migrate(conf)

    assert result.returncode == nginx_core.MIGRATE_UPDATED, result.stderr
    patched = conf.read_text(encoding="utf-8")
    assert not MOVED_HEADERS.search(patched)
    assert "CSP relaxations" not in patched  # the generated comment goes with them
    # Every server block that serves content includes the snippet exactly once;
    # an HTTP->HTTPS redirect block is left alone.
    for block in _server_blocks(patched):
        expected = 0 if "return 301" in block else 1
        assert block.count(INCLUDE) == expected, block
    # Everything else is kept: HSTS, certs, proxying.
    for keep in ("Strict-Transport-Security", "ssl_certificate", "location /api/", "proxy_pass"):
        assert patched.count(keep) == original.count(keep)
    # The original is backed up, byte for byte.
    backup = nginx_core.latest_backup(tmp_path)
    assert backup is not None
    assert backup.read_text(encoding="utf-8") == original


@needs_sh
def test_up_to_date_config_is_left_untouched(tmp_path):
    conf = tmp_path / "nginx.conf"
    conf.write_text(generate_nginx_conf("import"), encoding="utf-8", newline="\n")
    before = conf.read_bytes()

    result = _migrate(conf)

    assert result.returncode == nginx_core.MIGRATE_UNCHANGED
    assert conf.read_bytes() == before
    assert nginx_core.latest_backup(tmp_path) is None


@needs_sh
def test_running_twice_changes_nothing_the_second_time(tmp_path):
    conf = tmp_path / "nginx.conf"
    shutil.copy(FIXTURES / "demo-https-pre-0.1.2.conf", conf)
    assert _migrate(conf).returncode == nginx_core.MIGRATE_UPDATED
    once = conf.read_bytes()

    assert _migrate(conf).returncode == nginx_core.MIGRATE_UNCHANGED
    assert conf.read_bytes() == once


@needs_sh
def test_block_without_any_headers_gets_the_include(tmp_path):
    conf = tmp_path / "nginx.conf"
    conf.write_text("server {\n    listen 80;\n    server_name _;\n    root /x;\n}\n", newline="\n")

    assert _migrate(conf).returncode == nginx_core.MIGRATE_UPDATED
    assert conf.read_text() == (
        f"server {{\n    listen 80;\n    server_name _;\n    {INCLUDE}\n    root /x;\n}}\n"
    )


@needs_sh
def test_missing_file_is_an_error(tmp_path):
    assert _migrate(tmp_path / "nginx.conf").returncode == 1


def test_snippet_csp_allows_what_the_spa_needs():
    """The CSP the issue was about: data:/blob: images must be allowed, while
    the parts that matter stay locked down."""
    csp = _snippet_csps()[0]
    assert "img-src 'self' data: blob:" in csp  # logo / pasted image previews (#57)
    assert "style-src 'self' 'unsafe-inline'" in csp  # TipTap injects a <style> tag
    assert "font-src 'self'" in csp  # fonts are self-hosted
    assert "script-src 'self';" in csp
    assert "'unsafe-eval'" not in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    # No third-party origins - installs are frequently air-gapped.
    assert "http://" not in csp and "https://" not in csp


def _snippet_csps():
    """[app CSP, /api/v1/files/ CSP] - both set into $irdoc_csp (#137)."""
    return [line.strip() for line in SNIPPET.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("set $irdoc_csp ")]


def test_snippet_lets_only_the_app_frame_stored_files():
    """The PDF preview frames /api/v1/files/ (#137); the rest stays DENY."""
    text = SNIPPET.read_text(encoding="utf-8")
    app_csp, files_csp = _snippet_csps()
    assert "frame-ancestors 'none'" in app_csp
    assert "frame-ancestors 'self'" in files_csp
    assert "default-src 'none'" in files_csp  # no scripts in served files
    assert "script-src" not in files_csp
    assert "if ($uri ~ ^/api/v1/files/)" in text
    assert "add_header Content-Security-Policy $irdoc_csp always;" in text
    assert "add_header X-Frame-Options $irdoc_frame_options always;" in text

    # Must match the backend, or the browser enforces the stricter copy
    main_py = (REPO_ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    block = main_py[main_py.index("_FILES_CSP = ("):]
    backend_csp = "".join(re.findall(r'"([^"]*)"', block[:block.index(")")]))
    assert f'"{backend_csp}"' in files_csp


def test_snippet_has_no_hsts():
    # HSTS depends on the HTTPS mode, so it must stay in the host config.
    assert "Strict-Transport-Security" not in SNIPPET.read_text(encoding="utf-8")


def test_frontend_image_ships_snippet_and_script():
    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    assert f"nginx/irdoc-security-headers.conf {SECURITY_HEADERS_SNIPPET}" in dockerfile
    assert "nginx/irdoc-nginx-migrate.sh /usr/local/bin/irdoc-nginx-migrate" in dockerfile


def test_frontend_image_ships_default_config_and_selector():
    """#131: the default config comes from the image, so it always matches the
    snippet that image ships."""
    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    assert "nginx/default.conf /etc/nginx/irdoc/default.conf" in dockerfile
    assert "nginx/90-irdoc-select-conf.sh /docker-entrypoint.d/90-irdoc-select-conf.sh" in dockerfile


def test_prod_compose_mounts_the_local_dir_not_a_tracked_file():
    """#114: nothing tracked in git is the live nginx config any more."""
    compose = (REPO_ROOT / "docker" / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "./nginx/local:/etc/nginx/irdoc-local:ro" in compose
    assert "./nginx/nginx.conf:" not in compose


@pytest.mark.parametrize("path", [
    "docker/nginx/nginx.conf",
    "docker/nginx/examples/demo-https.conf",
    "frontend/nginx/default.conf",
])
def test_tracked_configs_use_the_snippet(path):
    conf = (REPO_ROOT / path).read_text(encoding="utf-8")
    assert INCLUDE in conf
    assert not MOVED_HEADERS.search(conf)


def test_tracked_nginx_conf_is_frozen():
    """docker/nginx/nginx.conf is no longer used, but installs from before
    #114 may have edited it. Changing it upstream would make their `git pull`
    fail again, so it must stay one of the shipped versions."""
    assert nginx_core.is_shipped_default(REPO_ROOT / "docker" / "nginx" / "nginx.conf")


def test_upgrade_sh_knows_the_same_shipped_configs():
    script = (REPO_ROOT / "docker" / "upgrade.sh").read_text(encoding="utf-8")
    listed = re.search(r'^SHIPPED_NGINX_SHA256="([^"]*)"', script, re.MULTILINE).group(1)
    assert set(listed.split()) == nginx_core.SHIPPED_NGINX_CONF_SHA256


def test_edited_tracked_conf_is_adopted(tmp_path):
    (tmp_path / "nginx.conf").write_text("server { listen 443 ssl; }\n")

    assert nginx_core.adopt_edited_conf(tmp_path) is True
    assert (tmp_path / "local" / "nginx.conf").read_text() == "server { listen 443 ssl; }\n"


def test_shipped_tracked_conf_is_not_adopted(tmp_path):
    # CRLF, as a Windows checkout may have it: still the shipped file.
    shipped = (REPO_ROOT / "docker" / "nginx" / "nginx.conf").read_bytes().replace(b"\r", b"")
    (tmp_path / "nginx.conf").write_bytes(shipped.replace(b"\n", b"\r\n"))

    assert nginx_core.adopt_edited_conf(tmp_path) is False
    assert not (tmp_path / "local" / "nginx.conf").exists()


def test_existing_local_conf_is_never_overwritten(tmp_path):
    (tmp_path / "nginx.conf").write_text("edited")
    (tmp_path / "local").mkdir()
    (tmp_path / "local" / "nginx.conf").write_text("mine")

    assert nginx_core.adopt_edited_conf(tmp_path) is False
    assert (tmp_path / "local" / "nginx.conf").read_text() == "mine"


def _select(tmp_path, with_local: bool) -> subprocess.CompletedProcess:
    (tmp_path / "default.conf").write_text("default")
    if with_local:
        (tmp_path / "local.conf").write_text("local")
    env = {
        "PATH": os.environ.get("PATH", ""),
        "IRDOC_NGINX_LOCAL": str(tmp_path / "local.conf"),
        "IRDOC_NGINX_DEFAULT": str(tmp_path / "default.conf"),
        "IRDOC_NGINX_TARGET": str(tmp_path / "target.conf"),
    }
    return subprocess.run(["sh", str(SELECT_SCRIPT)], capture_output=True, text=True, env=env)


@needs_sh
@pytest.mark.parametrize("with_local, served", [(True, "local"), (False, "default")])
def test_entrypoint_serves_local_config_else_the_default(tmp_path, with_local, served):
    result = _select(tmp_path, with_local)

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "target.conf").read_text() == served


def test_migrate_args_mount_the_nginx_dir(tmp_path):
    args = nginx_core.migrate_args(tmp_path)
    assert args[:3] == ["run", "--rm", "--no-deps"]
    assert f"{tmp_path}:/irdoc-nginx" in args
    assert args[args.index("--entrypoint") + 1] == "irdoc-nginx-migrate"
    assert args[-2:] == ["frontend", "/irdoc-nginx/nginx.conf"]


def test_restore_backup_puts_newest_backup_back(tmp_path):
    conf = tmp_path / "nginx.conf"
    conf.write_text("patched")
    (tmp_path / "nginx.conf.bak-20260101-000000").write_text("older")
    (tmp_path / "nginx.conf.bak-20261011-120000").write_text("original")

    restored = nginx_core.restore_backup(tmp_path)

    assert restored.name == "nginx.conf.bak-20261011-120000"
    assert conf.read_text() == "original"


def test_restore_backup_without_backup_does_nothing(tmp_path):
    conf = tmp_path / "nginx.conf"
    conf.write_text("patched")
    assert nginx_core.restore_backup(tmp_path) is None
    assert conf.read_text() == "patched"
