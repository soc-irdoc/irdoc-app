"""Wait for PostgreSQL and Redis at container start (#159).

    python -m app.cli.wait_for_services

Used by entrypoint.sh in place of a shell loop that hid every error and
retried forever. This one:

- keeps waiting while the cause is temporary (connection refused, DNS not
  ready yet, "the database system is starting up"), printing the reason at
  most every REPORT_EVERY seconds;
- exits non-zero at once when retrying can't help (wrong password, missing
  database or role, malformed URL), with a message that says what to fix;
- gives up after WAIT_FOR_SERVICES_TIMEOUT seconds (default 300) with the
  last error;
- reads the URLs from the environment and never prints a password.

Exit codes: 0 ready, 1 permanent error, 2 timed out.
"""
import asyncio
import os
import re
import socket
import sys
import time
from collections.abc import Callable

EXIT_OK = 0
EXIT_FATAL = 1
EXIT_TIMEOUT = 2

REPORT_EVERY = 10.0
RETRY_INTERVAL = 2.0

_PG_PASSWORD_HINT = (
    "The password in DATABASE_URL must match DB_PASSWORD. PostgreSQL applies "
    "DB_PASSWORD only when its data volume is first created; to change it "
    "later, run ALTER USER in the database too."
)
_REDIS_PASSWORD_HINT = "The password in REDIS_URL must match REDIS_PASSWORD."


def mask_url(url: str) -> str:
    """Hide the password in scheme://user:password@host URLs."""
    return re.sub(r"^([a-zA-Z][\w+.-]*://[^:/@]*):.*@", r"\1:***@", url)


def _sentence(exc: BaseException) -> str:
    return str(exc).strip().rstrip(".")


def _describe(exc: BaseException) -> str:
    text = str(exc).strip()
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


# ─── Classifiers: (fatal, message) ────────────────────────────────────────────

def classify_postgres_error(exc: BaseException) -> tuple[bool, str]:
    import asyncpg

    if isinstance(exc, asyncpg.InvalidPasswordError):
        return True, f"{_sentence(exc)}. {_PG_PASSWORD_HINT}"
    if isinstance(exc, asyncpg.InvalidCatalogNameError):
        return True, f"{_sentence(exc)}. Check the database name at the end of DATABASE_URL."
    if isinstance(exc, asyncpg.InvalidAuthorizationSpecificationError):
        return True, f"{_sentence(exc)}. Check the user name in DATABASE_URL."
    if isinstance(exc, (asyncpg.ClientConfigurationError, ValueError)):
        return True, f"DATABASE_URL is not a valid PostgreSQL URL ({exc})."
    if isinstance(exc, (asyncpg.CannotConnectNowError, asyncpg.TooManyConnectionsError,
                        OSError, socket.gaierror, TimeoutError, asyncio.TimeoutError)):
        return False, _describe(exc)
    # Unknown: keep trying, the timeout still bounds it.
    return False, _describe(exc)


def classify_redis_error(exc: BaseException) -> tuple[bool, str]:
    import redis

    if isinstance(exc, redis.AuthenticationError):
        return True, f"{_sentence(exc)}. {_REDIS_PASSWORD_HINT}"
    if isinstance(exc, redis.ResponseError):
        text = str(exc)
        if text.startswith(("WRONGPASS", "NOAUTH")):
            return True, f"{text.rstrip('.')}. {_REDIS_PASSWORD_HINT}"
    if isinstance(exc, ValueError):
        return True, f"REDIS_URL is not a valid Redis URL ({exc})."
    return False, _describe(exc)


# ─── Probes ───────────────────────────────────────────────────────────────────

def postgres_probe(url: str) -> Callable[[], None]:
    dsn = url.replace("+asyncpg", "", 1)

    def probe() -> None:
        import asyncpg

        async def check():
            conn = await asyncpg.connect(dsn, timeout=5)
            await conn.close()

        asyncio.run(check())

    return probe


def redis_probe(url: str) -> Callable[[], None]:
    def probe() -> None:
        import redis

        client = redis.Redis.from_url(url, socket_connect_timeout=5, socket_timeout=5)
        try:
            client.ping()
        finally:
            client.close()

    return probe


# ─── Loop ─────────────────────────────────────────────────────────────────────

def wait_for(
    name: str,
    url: str,
    probe: Callable[[], None],
    classify: Callable[[BaseException], tuple[bool, str]],
    *,
    timeout: float,
    interval: float = RETRY_INTERVAL,
    report_every: float = REPORT_EVERY,
) -> int:
    masked = mask_url(url)
    deadline = time.monotonic() + timeout
    last_report = float("-inf")
    while True:
        try:
            probe()
        except Exception as exc:  # noqa: BLE001 - classified below
            fatal, message = classify(exc)
            if fatal:
                print(f"ERROR: {name} rejected the connection ({masked}): {message}", file=sys.stderr)
                return EXIT_FATAL
            now = time.monotonic()
            if now >= deadline:
                print(
                    f"ERROR: {name} not reachable after {int(timeout)}s ({masked}). Last error: {message}",
                    file=sys.stderr,
                )
                return EXIT_TIMEOUT
            if now - last_report >= report_every:
                print(f"Waiting for {name} ({masked}): {message}", file=sys.stderr)
                last_report = now
            time.sleep(interval)
            continue
        print(f"{name} ready.")
        return EXIT_OK


def main() -> int:
    timeout = float(os.environ.get("WAIT_FOR_SERVICES_TIMEOUT", "300"))
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
        return EXIT_FATAL
    code = wait_for("PostgreSQL", database_url, postgres_probe(database_url),
                    classify_postgres_error, timeout=timeout)
    if code != EXIT_OK:
        return code
    redis_url = os.environ.get("REDIS_URL", "")
    if redis_url:
        code = wait_for("Redis", redis_url, redis_probe(redis_url), classify_redis_error, timeout=timeout)
    return code


if __name__ == "__main__":
    sys.exit(main())
