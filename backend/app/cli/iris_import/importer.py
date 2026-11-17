"""Run a migration: fetch closed IRIS cases, transform, write, report."""
from collections import Counter
from dataclasses import dataclass, field
from typing import TextIO
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli.iris_import.client import IrisClient
from app.cli.iris_import.mapping import Mapping
from app.cli.iris_import.transform import SkipCase, build_case
from app.cli.iris_import.writer import Actor, imported_ref, write_case
from app.models.user import User

SKIP_LABELS = {
    "already_imported": "already imported",
    "ref_taken": "reference already used by another incident",
    "ref_in_run": "same reference as an earlier case in this run",
    "missing_soc_id": "no SOC ticket ID",
    "invalid_soc_id": "SOC ticket ID is not a positive number",
    "missing_open_date": "no open date",
}


class ImportUserError(RuntimeError):
    pass


@dataclass
class Report:
    imported: list[tuple[int, str]] = field(default_factory=list)
    skipped: list[tuple[int, str, str]] = field(default_factory=list)  # (case, reason, detail)
    failed: list[tuple[int, str]] = field(default_factory=list)
    open_cases: int = 0

    @property
    def ok(self) -> bool:
        return not self.failed


async def resolve_user(db: AsyncSession, email: str) -> Actor:
    query = select(User).where(func.lower(User.email) == email.strip().lower())
    user = (await db.execute(query)).scalar_one_or_none()
    if user is None:
        raise ImportUserError(f"no IRDoc user with email {email}")
    if not user.is_active:
        raise ImportUserError(f"IRDoc user {email} is deactivated")
    if user.org_id is None:
        raise ImportUserError(f"IRDoc user {email} belongs to no organisation")
    return Actor(user_id=user.id, org_id=user.org_id, email=user.email)


async def run_import(db: AsyncSession, client: IrisClient, *, user_email: str, mapping: Mapping, tz: ZoneInfo,
                     dry_run: bool = False, case_ids: list[int] | None = None, limit: int | None = None,
                     out: TextIO) -> Report:
    report = Report()
    user = await resolve_user(db, user_email)
    mode = "DRY RUN - nothing will be saved" if dry_run else "importing"
    print(f"IRIS {await client.version()} at {client.base_url}; {mode}; cases attributed to {user.email}",
          file=out)

    cases = await client.list_cases(case_ids)
    closed = [c for c in cases if c.get("close_date")]
    report.open_cases = len(cases) - len(closed)
    if limit is not None:
        closed = closed[:limit]
    print(f"{len(closed)} closed case(s) to process ({report.open_cases} open case(s) ignored)", file=out)

    refs_this_run: dict[str, int] = {}
    for case in closed:
        case_id = case["case_id"]
        label = f"IRIS #{case_id}"
        try:
            # Checked before fetching, so re-runs don't download cases already imported.
            existing = await imported_ref(db, case_id)
            if existing:
                raise SkipCase("already_imported", existing)
            children = await client.fetch_children(case_id)
            bundle = build_case(case, children, mapping, tz, client.base_url)
            ref = bundle.incident.incident_ref
            if ref in refs_this_run:
                raise SkipCase("ref_in_run", f"{ref} (IRIS #{refs_this_run[ref]})")
            refs_this_run[ref] = case_id
            await write_case(db, bundle, user)
        except SkipCase as skip:
            await db.rollback()
            report.skipped.append((case_id, skip.reason, skip.detail))
            detail = f" ({skip.detail})" if skip.detail else ""
            print(f"  skip  {label}: {SKIP_LABELS.get(skip.reason, skip.reason)}{detail}", file=out)
            continue
        except Exception as exc:  # noqa: BLE001 - one bad case (IrisError, bad data) must not stop the run
            await db.rollback()
            report.failed.append((case_id, f"{type(exc).__name__}: {exc}"))
            print(f"  FAIL  {label}: {type(exc).__name__}: {exc}", file=out)
            continue

        if dry_run:
            await db.rollback()
        else:
            await db.commit()
        report.imported.append((case_id, ref))
        extra = f", {len(bundle.unsupported_iocs)} IOC(s) kept in notes" if bundle.unsupported_iocs else ""
        print(f"  {'would import' if dry_run else 'ok'}  {label} -> {ref} "
              f"({len(bundle.timeline)} events, {len(bundle.assets)} assets, {len(bundle.iocs)} IOCs{extra})",
              file=out)

    _print_summary(report, mapping, dry_run, out)
    return report


def _print_summary(report: Report, mapping: Mapping, dry_run: bool, out: TextIO) -> None:
    print("", file=out)
    print(f"{'Would import' if dry_run else 'Imported'}: {len(report.imported)}", file=out)
    for reason, count in sorted(Counter(r for _, r, _ in report.skipped).items()):
        print(f"Skipped ({SKIP_LABELS.get(reason, reason)}): {count}", file=out)
    print(f"Failed: {len(report.failed)}", file=out)
    if mapping.unmapped:
        print("", file=out)
        print("IRIS values with no entry in the mapping (default used, or IOC kept in notes):", file=out)
        for section, value in sorted(mapping.unmapped):
            print(f"  {section}: {value}", file=out)
