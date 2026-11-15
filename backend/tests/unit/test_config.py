"""Unit tests for app.core.config.Settings."""
from app.core.config import Settings
from app.main import application, settings


def test_version_defaults_to_dev(monkeypatch):
    monkeypatch.delenv("VERSION", raising=False)
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    s = Settings(_env_file=None)
    assert s.VERSION == "dev"


def test_version_reads_env_override(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.setenv("VERSION", "0.1.0-alpha")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    s = Settings(_env_file=None)
    assert s.VERSION == "0.1.0-alpha"


def test_baked_app_version_wins_over_image_tag(monkeypatch):
    # Compose sets VERSION to the image tag ("latest"); the version baked into
    # the image at build time is what is actually running.
    monkeypatch.setenv("VERSION", "latest")
    monkeypatch.setenv("APP_VERSION", "0.1.4-alpha")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    s = Settings(_env_file=None)
    assert s.VERSION == "0.1.4-alpha"


def test_empty_app_version_falls_back_to_version(monkeypatch):
    monkeypatch.setenv("VERSION", "0.1.0-alpha")
    monkeypatch.setenv("APP_VERSION", "")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    s = Settings(_env_file=None)
    assert s.VERSION == "0.1.0-alpha"


def test_app_version_matches_settings():
    assert application.version == settings.VERSION


def test_cors_origins_defaults_to_base_url_plus_localhost(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("BASE_URL", "https://irdoc.internal.example.com")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    s = Settings(_env_file=None)
    origins = s.get_cors_origins()
    assert "https://irdoc.internal.example.com" in origins
    assert "https://localhost" in origins
    assert "https://127.0.0.1" in origins


def test_cors_origins_localhost_variant_keeps_base_url_port(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("BASE_URL", "http://irdoc-host:3000")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    s = Settings(_env_file=None)
    origins = s.get_cors_origins()
    assert "http://irdoc-host:3000" in origins
    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:3000" in origins


def test_cors_origins_no_duplicate_when_base_url_is_already_localhost(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("BASE_URL", "http://localhost:3000")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    s = Settings(_env_file=None)
    origins = s.get_cors_origins()
    assert origins.count("http://localhost:3000") == 1


def test_explicit_cors_origins_override_disables_localhost_widening(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("BASE_URL", "https://irdoc.example.com")
    monkeypatch.setenv("CORS_ORIGINS", "https://irdoc.example.com,https://reports.example.com")
    s = Settings(_env_file=None)
    origins = s.get_cors_origins()
    assert origins == ["https://irdoc.example.com", "https://reports.example.com"]


# ─── COOKIE_SECURE (#157) ────────────────────────────────────────────────────

def _settings(monkeypatch, base_url: str, cookie_secure: str | None):
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("BASE_URL", base_url)
    if cookie_secure is None:
        monkeypatch.delenv("COOKIE_SECURE", raising=False)
    else:
        monkeypatch.setenv("COOKIE_SECURE", cookie_secure)
    return Settings(_env_file=None)


def test_cookie_secure_follows_https_base_url(monkeypatch):
    assert _settings(monkeypatch, "https://irdoc.example.com", None).COOKIE_SECURE is True


def test_cookie_secure_off_for_http_base_url(monkeypatch):
    assert _settings(monkeypatch, "http://localhost:3000", None).COOKIE_SECURE is False


def test_empty_cookie_secure_means_derive(monkeypatch):
    # prod compose always injects the key; empty must not crash or force False
    assert _settings(monkeypatch, "https://irdoc.example.com", "").COOKIE_SECURE is True


def test_explicit_cookie_secure_wins(monkeypatch):
    assert _settings(monkeypatch, "https://irdoc.example.com", "false").COOKIE_SECURE is False
    assert _settings(monkeypatch, "http://localhost:3000", "true").COOKIE_SECURE is True
