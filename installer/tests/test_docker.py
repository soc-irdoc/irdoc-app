import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from installer.core.docker import detect_mode, COMPOSE_FILE


def test_detect_mode_install_when_no_env(tmp_path):
    env_path = tmp_path / ".env"  # does not exist
    assert detect_mode(env_path, "1.2.0") == "install"


def test_detect_mode_upgrade_when_versions_differ(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("DB_PASSWORD=x\n")
    with patch("installer.core.docker.get_installed_version_sync", return_value="1.1.0"):
        result = detect_mode(env_path, "1.2.0")
    assert result == "upgrade"


def test_detect_mode_reconfigure_when_same_version(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("DB_PASSWORD=x\n")
    with patch("installer.core.docker.get_installed_version_sync", return_value="1.2.0"):
        result = detect_mode(env_path, "1.2.0")
    assert result == "reconfigure"


def test_detect_mode_upgrade_when_container_not_running(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("DB_PASSWORD=x\n")
    with patch("installer.core.docker.get_installed_version_sync", return_value=None):
        result = detect_mode(env_path, "1.2.0")
    assert result == "upgrade"


def test_compose_file_points_to_prod_compose():
    assert "docker-compose.prod.yml" in COMPOSE_FILE
    assert "docker" in COMPOSE_FILE
