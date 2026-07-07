"""Unit tests for app.core.config.Settings."""
from app.core.config import Settings
from app.main import application, settings


def test_version_defaults_to_dev(monkeypatch):
    monkeypatch.delenv("VERSION", raising=False)
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    s = Settings(_env_file=None)
    assert s.VERSION == "dev"


def test_version_reads_env_override(monkeypatch):
    monkeypatch.setenv("VERSION", "0.1.0-alpha")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    s = Settings(_env_file=None)
    assert s.VERSION == "0.1.0-alpha"


def test_app_version_matches_settings():
    assert application.version == settings.VERSION
