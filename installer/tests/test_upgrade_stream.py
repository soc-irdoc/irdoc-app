"""The compose calls /upgrade/progress/stream makes, in order (#105, #57)."""
from unittest.mock import AsyncMock, patch

import pytest

import installer.wizard as wizard


class FakeCompose:
    """Stands in for run_compose: records each call and exits with the code
    chosen by `exit_codes(args)`."""

    def __init__(self, exit_codes=lambda args: 0):
        self.calls: list[tuple[list[str], dict | None]] = []
        self._exit_codes = exit_codes

    def __call__(self, args, env_override=None):
        self.calls.append((args, env_override))
        code = self._exit_codes(args)

        async def gen():
            yield "data: ...\n\n"
            yield f"data: __EXIT__{code}\n\n"

        return gen()

    def find(self, *needle):
        return [c for c in self.calls if all(n in c[0] for n in needle)]


async def _run_stream(client, compose, tmp_path):
    (tmp_path / "nginx").mkdir(exist_ok=True)
    wizard.state.version_to = "9.9.9"
    with patch.object(wizard, "run_compose", compose), \
         patch.object(wizard, "DOCKER_DIR", tmp_path), \
         patch.object(wizard, "wait_for_health", AsyncMock(return_value=True)), \
         patch.object(wizard.asyncio, "sleep", AsyncMock()):
        resp = await client.get("/upgrade/progress/stream")
    return resp.text


@pytest.mark.asyncio
async def test_migrations_run_on_backend_service_with_target_version(client, tmp_path):
    compose = FakeCompose()
    body = await _run_stream(client, compose, tmp_path)

    (args, env), = compose.find("alembic")
    assert args == ["run", "--rm", "backend", "alembic", "upgrade", "head"]
    assert env == {"VERSION": "9.9.9"}
    assert "__DONE__" in body


@pytest.mark.asyncio
async def test_nginx_migrate_runs_with_target_image_before_start(client, tmp_path):
    compose = FakeCompose()
    await _run_stream(client, compose, tmp_path)

    commands = [c[0] for c in compose.calls]
    migrate = next(i for i, a in enumerate(commands) if "irdoc-nginx-migrate" in a)
    up = next(i for i, a in enumerate(commands) if a[:2] == ["up", "-d"])
    alembic = next(i for i, a in enumerate(commands) if "alembic" in a)
    assert alembic < migrate < up
    assert compose.calls[migrate][1] == {"VERSION": "9.9.9"}
    assert f"{tmp_path / 'nginx'}:/irdoc-nginx" in commands[migrate]


@pytest.mark.asyncio
async def test_rejected_nginx_config_is_rolled_back(client, tmp_path):
    nginx_dir = tmp_path / "nginx"
    nginx_dir.mkdir()
    (nginx_dir / "nginx.conf").write_text("patched")
    (nginx_dir / "nginx.conf.bak-20261011-120000").write_text("original")

    def exit_codes(args):
        return 1 if args[:2] == ["exec", "-T"] else 0  # nginx -t always fails

    compose = FakeCompose(exit_codes)
    body = await _run_stream(client, compose, tmp_path)

    assert (nginx_dir / "nginx.conf").read_text() == "original"
    assert compose.find("restart", "frontend")
    assert not compose.find("reload")
    assert "restored nginx.conf.bak-20261011-120000" in body


@pytest.mark.asyncio
async def test_updated_nginx_config_is_checked_then_reloaded(client, tmp_path):
    # Default exit code 0: the migrate script updated the file, nginx -t passes.
    compose = FakeCompose()
    await _run_stream(client, compose, tmp_path)

    commands = [c[0] for c in compose.calls]
    check = commands.index(["exec", "-T", "frontend", "nginx", "-t"])
    reload = commands.index(["exec", "-T", "frontend", "nginx", "-s", "reload"])
    assert commands.index(["up", "-d", "--remove-orphans"]) < check < reload
    assert not compose.find("restart")


@pytest.mark.asyncio
async def test_unchanged_nginx_config_is_not_checked(client, tmp_path):
    def exit_codes(args):
        return 10 if "irdoc-nginx-migrate" in args else 0

    compose = FakeCompose(exit_codes)
    await _run_stream(client, compose, tmp_path)

    assert not compose.find("nginx", "-t")
    assert not compose.find("restart")


@pytest.mark.asyncio
async def test_image_without_migrate_script_keeps_upgrading(client, tmp_path):
    # An older target image has no irdoc-nginx-migrate: docker exits non-zero.
    def exit_codes(args):
        return 127 if "irdoc-nginx-migrate" in args else 0

    compose = FakeCompose(exit_codes)
    body = await _run_stream(client, compose, tmp_path)

    assert "keeping the existing config" in body
    assert compose.find("up", "-d")
    assert "__DONE__" in body
