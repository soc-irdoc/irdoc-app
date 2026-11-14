"""docker/upgrade.sh against a fixture install: it uses the git-ignored
docker-compose.local.yml, warns about local edits to tracked files, and leaves
the operator's own files alone (Refs #162).

A stub `docker` on PATH records every call and succeeds, so no Docker is
needed; git is real.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
UPGRADE_SH = REPO / "docker" / "upgrade.sh"

BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="needs bash")

ENV = """DB_PASSWORD=keep-me
REDIS_PASSWORD=keep-me-too
SECRET_KEY=custom-secret
BASE_URL=https://irdoc.corp.example
VERSION=0.1.11-alpha
CUSTOM_SETTING=untouched
"""
NGINX = "# my own nginx config\nserver { listen 8443; }\n"
CERT = "-----BEGIN CERTIFICATE-----\nmine\n-----END CERTIFICATE-----\n"
LOCAL_COMPOSE = "services:\n  backend:\n    mem_limit: 2g\n"


def _install(tmp_path: Path, local_compose: bool = True) -> Path:
    root = tmp_path / "install"
    docker = root / "docker"
    (docker / "nginx" / "local").mkdir(parents=True)
    (docker / "ssl").mkdir()
    shutil.copy(UPGRADE_SH, docker / "upgrade.sh")
    (docker / "docker-compose.prod.yml").write_text("services: {}\n", newline="\n")
    (docker / ".env").write_text(ENV, newline="\n")
    (docker / "nginx" / "local" / "nginx.conf").write_text(NGINX, newline="\n")
    (docker / "ssl" / "cert.pem").write_text(CERT, newline="\n")
    if local_compose:
        (docker / "docker-compose.local.yml").write_text(LOCAL_COMPOSE, newline="\n")
    (root / "VERSION").write_text("0.2.0-alpha\n")
    return root


def _fake_docker(tmp_path: Path) -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "docker.log"
    stub = bin_dir / "docker"
    stub.write_text(f'#!/bin/bash\necho "$*" >> "{log.as_posix()}"\nexit 0\n', newline="\n")
    stub.chmod(0o755)
    return bin_dir, log


def _run(root: Path, bin_dir: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        [BASH, "docker/upgrade.sh", "0.2.0-alpha"], cwd=root, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


def test_every_compose_call_includes_the_local_file(tmp_path):
    root = _install(tmp_path)
    bin_dir, log = _fake_docker(tmp_path)
    result = _run(root, bin_dir)
    assert result.returncode == 0, result.stderr
    assert "Using your docker-compose.local.yml" in result.stdout

    compose_calls = [line for line in log.read_text().splitlines() if line.startswith("compose ")]
    assert compose_calls, "upgrade.sh made no compose calls"
    for call in compose_calls:
        assert "docker-compose.local.yml" in call, call


def test_without_a_local_file_only_the_prod_file_is_used(tmp_path):
    root = _install(tmp_path, local_compose=False)
    bin_dir, log = _fake_docker(tmp_path)
    assert _run(root, bin_dir).returncode == 0
    assert "docker-compose.local.yml" not in log.read_text()


def test_operator_files_survive_the_upgrade(tmp_path):
    root = _install(tmp_path)
    bin_dir, _ = _fake_docker(tmp_path)
    assert _run(root, bin_dir).returncode == 0
    docker = root / "docker"

    env = (docker / ".env").read_text()
    for line in ENV.splitlines():
        if not line.startswith("VERSION="):
            assert line in env, line  # nothing of the operator's is lost
    assert "VERSION=0.2.0-alpha" in env  # only the version moves
    assert (docker / "nginx" / "local" / "nginx.conf").read_text() == NGINX
    assert (docker / "ssl" / "cert.pem").read_text() == CERT
    assert (docker / "docker-compose.local.yml").read_text() == LOCAL_COMPOSE


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_warns_about_local_edits_to_tracked_files(tmp_path):
    root = _install(tmp_path)
    _git(root, "init", "-q")
    _git(root, "add", "docker/docker-compose.prod.yml", "docker/upgrade.sh")
    _git(root, "commit", "-q", "-m", "fixture")
    (root / "docker" / "docker-compose.prod.yml").write_text("services: {edited: {}}\n", newline="\n")

    bin_dir, _ = _fake_docker(tmp_path)
    result = _run(root, bin_dir)
    assert result.returncode == 0, result.stderr
    assert "have local changes" in result.stderr
    assert "docker-compose.prod.yml" in result.stderr
    assert "docker-compose.local.yml" in result.stderr


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_no_warning_on_a_clean_checkout(tmp_path):
    root = _install(tmp_path)
    _git(root, "init", "-q")
    _git(root, "add", "docker/docker-compose.prod.yml", "docker/upgrade.sh")
    _git(root, "commit", "-q", "-m", "fixture")
    bin_dir, _ = _fake_docker(tmp_path)
    assert "have local changes" not in _run(root, bin_dir).stderr
