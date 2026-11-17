"""Import closed cases from DFIR IRIS (v2.4) into IRDoc.

Run inside the backend container:

    docker compose exec -e IRIS_API_KEY=<key> backend \\
        python -m app.cli.iris_import --iris-url https://iris.example \\
        --import-user analyst@example.com --dry-run

Each closed IRIS case becomes a closed IRDoc incident:

- The reference is INC-<open year>-<SOC ticket ID>.
- The open and close dates, summary, notes, timeline (original timestamps),
  assets and IOCs are kept.

Run with --dry-run first. It does everything except save, and lists IRIS
values the mapping doesn't cover. Re-running is safe: cases already imported
are skipped.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.cli.iris_import.client import IrisClient, IrisError
from app.cli.iris_import.importer import ImportUserError, run_import
from app.cli.iris_import.mapping import MappingError, load_mapping

EXIT_OK, EXIT_FAILED_CASES, EXIT_USAGE = 0, 1, 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli.iris_import", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--iris-url", required=True, help="IRIS base URL, e.g. https://iris.example")
    parser.add_argument("--import-user", required=True, metavar="EMAIL",
                        help="IRDoc user the imported incidents are attributed to (sets the organisation)")
    parser.add_argument("--mapping", type=Path, help="YAML file overriding the default value mappings")
    parser.add_argument("--date-tz", default="UTC",
                        help="timezone of IRIS open/close dates, which have no time (default: UTC)")
    parser.add_argument("--case-id", type=int, action="append", dest="case_ids", metavar="ID",
                        help="only this IRIS case id (repeatable)")
    parser.add_argument("--limit", type=int, help="process at most this many closed cases")
    parser.add_argument("--dry-run", action="store_true", help="do everything except save")
    parser.add_argument("--insecure", action="store_true",
                        help="don't verify IRIS's TLS certificate (self-signed test instances only)")
    return parser


async def _run(args, api_key: str, mapping, tz) -> int:
    from app.core.database import AsyncSessionLocal
    async with IrisClient(args.iris_url, api_key, verify=not args.insecure) as client:
        async with AsyncSessionLocal() as db:
            report = await run_import(db, client, user_email=args.import_user, mapping=mapping, tz=tz,
                                      dry_run=args.dry_run, case_ids=args.case_ids, limit=args.limit,
                                      out=sys.stdout)
    return EXIT_OK if report.ok else EXIT_FAILED_CASES


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    api_key = os.environ.get("IRIS_API_KEY", "").strip()
    if not api_key:
        print("error: set the IRIS API key in the IRIS_API_KEY environment variable", file=sys.stderr)
        return EXIT_USAGE
    try:
        tz = ZoneInfo(args.date_tz)
    except (ZoneInfoNotFoundError, ValueError):
        print(f"error: unknown timezone {args.date_tz!r} (use an IANA name like Europe/Bucharest)",
              file=sys.stderr)
        return EXIT_USAGE
    try:
        mapping = load_mapping(args.mapping)
        return asyncio.run(_run(args, api_key, mapping, tz))
    except (MappingError, ImportUserError, IrisError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
