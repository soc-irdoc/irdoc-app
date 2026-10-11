"""Regression tests for #57: upgrades bring an old host nginx.conf over to the
security-headers snippet shipped in the frontend image.

Runs the real frontend/nginx/irdoc-nginx-migrate.sh (the script both upgrade
paths run inside the frontend image) against nginx configs from past releases.
"""
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
    csp = next(line for line in SNIPPET.read_text(encoding="utf-8").splitlines()
               if line.startswith("add_header Content-Security-Policy"))
    assert "img-src 'self' data: blob:" in csp  # logo / pasted image previews (#57)
    assert "style-src 'self' 'unsafe-inline'" in csp  # TipTap injects a <style> tag
    assert "font-src 'self'" in csp  # fonts are self-hosted
    assert "script-src 'self';" in csp
    assert "'unsafe-eval'" not in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    # No third-party origins - installs are frequently air-gapped.
    assert "http://" not in csp and "https://" not in csp


def test_snippet_has_no_hsts():
    # HSTS depends on the HTTPS mode, so it must stay in the host config.
    assert "Strict-Transport-Security" not in SNIPPET.read_text(encoding="utf-8")


def test_frontend_image_ships_snippet_and_script():
    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    assert f"nginx/irdoc-security-headers.conf {SECURITY_HEADERS_SNIPPET}" in dockerfile
    assert "nginx/irdoc-nginx-migrate.sh /usr/local/bin/irdoc-nginx-migrate" in dockerfile


@pytest.mark.parametrize("path", [
    "docker/nginx/nginx.conf",
    "docker/nginx/nginx.demo-https.conf",
    "frontend/nginx.conf",
])
def test_tracked_configs_use_the_snippet(path):
    conf = (REPO_ROOT / path).read_text(encoding="utf-8")
    assert INCLUDE in conf
    assert not MOVED_HEADERS.search(conf)


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
