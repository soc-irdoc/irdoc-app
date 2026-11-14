"""Startup wait for PostgreSQL / Redis: tell permanent failures from a slow
start, and never print a password (Refs #159)."""
import asyncio
import socket

import asyncpg
import pytest
import redis

from app.cli import wait_for_services as w

# ─── mask_url ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("postgresql+asyncpg://irp:s3cr3t@db/irp", "postgresql+asyncpg://irp:***@db/irp"),
    ("redis://:pa:ss@word@irdoc-redis:6379/0", "redis://:***@irdoc-redis:6379/0"),
    ("postgresql://irp@db/irp", "postgresql://irp@db/irp"),
    ("not a url", "not a url"),
])
def test_mask_url_hides_the_password(url, expected):
    assert w.mask_url(url) == expected


# ─── PostgreSQL ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("exc", [
    ConnectionRefusedError(111, "Connection refused"),
    socket.gaierror(-2, "Name or service not known"),
    asyncio.TimeoutError(),
    TimeoutError(),
    asyncpg.CannotConnectNowError("the database system is starting up"),
    asyncpg.TooManyConnectionsError("too many clients"),
])
def test_postgres_startup_errors_are_transient(exc):
    fatal, _ = w.classify_postgres_error(exc)
    assert fatal is False


def test_wrong_postgres_password_is_fatal_with_a_hint():
    exc = asyncpg.InvalidPasswordError('password authentication failed for user "irp"')
    fatal, message = w.classify_postgres_error(exc)
    assert fatal is True
    assert 'password authentication failed for user "irp"' in message
    assert "DB_PASSWORD" in message


@pytest.mark.parametrize("exc", [
    asyncpg.InvalidCatalogNameError('database "irpx" does not exist'),
    asyncpg.InvalidAuthorizationSpecificationError('role "nobody" does not exist'),
    asyncpg.ClientConfigurationError("invalid DSN"),
    ValueError("invalid DSN"),
])
def test_other_permanent_postgres_errors_are_fatal(exc):
    fatal, _ = w.classify_postgres_error(exc)
    assert fatal is True


# ─── Redis ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("exc", [
    redis.ConnectionError("Error 111 connecting to irdoc-redis:6379. Connection refused."),
    redis.TimeoutError("Timeout connecting to server"),
    redis.BusyLoadingError("Redis is loading the dataset in memory"),
])
def test_redis_startup_errors_are_transient(exc):
    fatal, _ = w.classify_redis_error(exc)
    assert fatal is False


@pytest.mark.parametrize("exc", [
    redis.AuthenticationError("invalid username-password pair"),
    redis.ResponseError("WRONGPASS invalid username-password pair or user is disabled."),
    redis.ResponseError("NOAUTH Authentication required."),
])
def test_wrong_redis_password_is_fatal_with_a_hint(exc):
    fatal, message = w.classify_redis_error(exc)
    assert fatal is True
    assert "REDIS_PASSWORD" in message


# ─── wait loop ───────────────────────────────────────────────────────────────

def test_wait_retries_transient_then_succeeds(capsys):
    attempts = iter([ConnectionRefusedError(111, "refused"), None])

    def probe():
        exc = next(attempts)
        if exc:
            raise exc

    code = w.wait_for("PostgreSQL", "postgresql://irp:pw@db/irp", probe, w.classify_postgres_error,
                      timeout=5, interval=0, report_every=0)
    assert code == 0
    out = capsys.readouterr()
    assert "refused" in out.err
    assert "pw@" not in out.err + out.out


def test_wait_exits_at_once_on_a_fatal_error(capsys):
    calls = []

    def probe():
        calls.append(1)
        raise asyncpg.InvalidPasswordError('password authentication failed for user "irp"')

    code = w.wait_for("PostgreSQL", "postgresql://irp:s3cr3t@db/irp", probe, w.classify_postgres_error,
                      timeout=60, interval=0, report_every=0)
    assert code == w.EXIT_FATAL
    assert len(calls) == 1
    err = capsys.readouterr().err
    assert "postgresql://irp:***@db/irp" in err
    assert "s3cr3t" not in err


def test_wait_gives_up_after_the_timeout(capsys):
    def probe():
        raise ConnectionRefusedError(111, "Connection refused")

    code = w.wait_for("PostgreSQL", "postgresql://irp:pw@db/irp", probe, w.classify_postgres_error,
                      timeout=0, interval=0, report_every=0)
    assert code == w.EXIT_TIMEOUT
    assert "Connection refused" in capsys.readouterr().err
