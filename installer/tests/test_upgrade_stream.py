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


async def _run_stream(client, compose, tmp_path, local_conf="server {}\n"):
    """Run the upgrade stream against tmp_path as docker/. local_conf is the
    install's nginx/local/nginx.conf (None: the install has none)."""
    local = tmp_path / "nginx" / "local"
    local.mkdir(parents=True, exist_ok=True)
    if local_conf is not None and not (local / "nginx.conf").exists():
        (local / "nginx.conf").write_text(local_conf)
    wizard.state.version_to = "9.9.9"
    with patch.object(wizard, "run_compose", compose),          patch.object(wizard, "DOCKER_DIR", tmp_path),          patch.object(wizard, "wait_for_health", AsyncMock(return_value=True)),          patch.object(wizard.asyncio, "sleep", AsyncMock()):
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
    # The install's own config lives in nginx/local/ (#114).
    assert f"{tmp_path / 'nginx' / 'local'}:/irdoc-nginx" in commands[migrate]


@pytest.mark.asyncio
async def test_rejected_nginx_config_is_rolled_back(client, tmp_path):
    local = tmp_path / "nginx" / "local"
    local.mkdir(parents=True)
    (local / "nginx.conf").write_text("patched")
    (local / "nginx.conf.bak-20261011-120000").write_text("original")

    def exit_codes(args):
        return 1 if args[:2] == ["exec", "-T"] else 0  # nginx -t always fails

    compose = FakeCompose(exit_codes)
    body = await _run_stream(client, compose, tmp_path)

    assert (local / "nginx.conf").read_text() == "original"
    assert len(compose.find("restart", "frontend")) == 2  # pick up, then restore
    assert not compose.find("reload")
    assert "restored nginx.conf.bak-20261011-120000" in body


@pytest.mark.asyncio
async def test_updated_nginx_config_is_picked_up_then_checked(client, tmp_path):
    # Default exit code 0: the migrate script updated the file, nginx -t passes.
    compose = FakeCompose()
    await _run_stream(client, compose, tmp_path)

    commands = [c[0] for c in compose.calls]
    # The frontend copies its config at start-up, so it must restart (a
    # reload would keep serving the old copy).
    restart = commands.index(["restart", "frontend"])
    check = commands.index(["exec", "-T", "frontend", "nginx", "-t"])
    assert commands.index(["up", "-d", "--remove-orphans"]) < restart < check
    assert not compose.find("reload")


@pytest.mark.asyncio
async def test_unchanged_nginx_config_is_not_checked(client, tmp_path):
    def exit_codes(args):
        return 10 if "irdoc-nginx-migrate" in args else 0

    compose = FakeCompose(exit_codes)
    await _run_stream(client, compose, tmp_path)

    assert not compose.find("nginx", "-t")
    assert not compose.find("restart")


@pytest.mark.asyncio
async def test_without_local_config_nothing_is_migrated(client, tmp_path):
    # No nginx/local/nginx.conf: the image's built-in default is served (#131).
    compose = FakeCompose()
    body = await _run_stream(client, compose, tmp_path, local_conf=None)

    assert not compose.find("--entrypoint", "irdoc-nginx-migrate")
    assert not compose.find("restart")
    assert "__DONE__" in body


@pytest.mark.asyncio
async def test_edited_tracked_config_moves_to_local(client, tmp_path):
    """#114: an install that edited the tracked nginx.conf keeps its edits in
    nginx/local/, where `git pull` can't conflict with them."""
    (tmp_path / "nginx").mkdir()
    (tmp_path / "nginx" / "nginx.conf").write_text("server { listen 443 ssl; }\n")

    def exit_codes(args):
        return 10 if "irdoc-nginx-migrate" in args else 0

    compose = FakeCompose(exit_codes)
    body = await _run_stream(client, compose, tmp_path, local_conf=None)

    local = tmp_path / "nginx" / "local" / "nginx.conf"
    assert local.read_text() == "server { listen 443 ssl; }\n"
    assert compose.find("--entrypoint", "irdoc-nginx-migrate")
    assert compose.find("restart", "frontend")
    assert "Moved your edited nginx/nginx.conf" in body


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
