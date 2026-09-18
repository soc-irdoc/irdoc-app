"""Contract tests for the env docker-compose.prod.yml injects into the backend.

The prod compose enumerates every backend env var explicitly, unlike the dev
compose which just mounts `env_file: .env`. That difference matters: a var
written as `${FOO:-}` is *always* injected, as an empty string, so it overrides
the pydantic default instead of falling back to it. For a Literal-typed setting
an empty string is not a legal value, and `Settings()` raises at import time —
which crash-loops backend, worker and beat together on a fresh install, since
all three run the same entrypoint. `AI_BACKEND: ${AI_BACKEND:-}` did exactly
that.
"""
import re
from pathlib import Path

import yaml

from app.core.config import Settings

COMPOSE = Path(__file__).resolve().parents[3] / "docker" / "docker-compose.prod.yml"

# Matches a whole-value compose interpolation: ${NAME} or ${NAME:-default}
VAR_RE = re.compile(r"^\$\{([A-Z_][A-Z0-9_]*)(?::-(.*))?\}$", re.DOTALL)

# Vars the compose file gives no default for — the wizard always writes these,
# so a realistic "operator changed nothing else" run still has them set.
OPERATOR_SUPPLIED = {
    "DATABASE_URL": "postgresql+asyncpg://irp:pw@irdoc-db/irp",
    "REDIS_URL": "redis://:pw@irdoc-redis:6379/0",
    "SECRET_KEY": "x" * 32,
    "BASE_URL": "https://irdoc.example.com",
}


def resolved_backend_env() -> dict[str, str]:
    """The env prod compose injects when the operator sets only the required secrets."""
    raw = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))["x-backend-env"]
    resolved: dict[str, str] = {}
    for key, value in raw.items():
        match = VAR_RE.match(str(value))
        if match is None:
            resolved[key] = str(value)  # hardcoded literal, e.g. STORAGE_PATH
            continue
        name, default = match.group(1), match.group(2)
        resolved[key] = OPERATOR_SUPPLIED.get(name, default if default is not None else "")
    return resolved


def test_prod_compose_defaults_load_into_settings(monkeypatch):
    """A fresh install that overrides nothing optional must still boot."""
    for key, value in resolved_backend_env().items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    Settings(_env_file=None)  # must not raise


def test_ai_backend_default_is_a_valid_literal():
    """Regression: AI_BACKEND was `${AI_BACKEND:-}`, crash-looping the whole stack."""
    value = resolved_backend_env()["AI_BACKEND"]

    assert value in ("anthropic", "openai", "ollama"), (
        f"docker-compose.prod.yml injects AI_BACKEND={value!r}, which Settings rejects. "
        "Compose defaults for Literal-typed settings must name a real choice."
    )
