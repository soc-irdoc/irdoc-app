"""ClusterFuzzLite / Atheris fuzz harness for the fixed incident report's
HTML-rendering entry point.

Target: render_fixed_report_html() in
backend/app/services/report_renderer/fixed_report.py

Why this function, and not render_incident_pdf() / render_incident_pdf_from_schema()
in engine.py: those two wrap this exact HTML string in a WeasyPrint
HTML(...).write_pdf() call. WeasyPrint's native stack (Pango/Cairo/GDK-pixbuf,
see backend/Dockerfile's apt-get list) is a separate, independently-maintained
C dependency -- fuzzing through it would mostly be fuzzing WeasyPrint's own
libraries rather than this codebase's logic, and it drags a heavy native
toolchain into the fuzz build for no benefit. The actual untrusted-input
boundary that matters for *this* codebase -- attacker-influenced incident
data flowing through Jinja2 into an HTML string -- is fully exercised by
render_fixed_report_html() alone, with WeasyPrint never entering the picture.

Highest-value field -- read this before assuming every fuzzed field is
equally interesting: incident.executive_summary and ai_executive_summary.
Every other field reaching the templates below goes through Jinja2's
default autoescaping (engine.py's _build_jinja_env() sets
autoescape=jinja2.select_autoescape(["html"])). executive_summary and
ai_executive_summary are different: reports/blocks/section.html and
text_block.html render them through the custom `sanitize_html` Jinja filter
(also defined in engine.py), which runs the value through bleach.clean()
(app.services.incident_service._sanitize_html) and then wraps the result in
markupsafe.Markup(...) -- i.e. it deliberately opts back OUT of Jinja2
autoescaping and trusts bleach's tag/attribute/protocol allowlist
completely. That is the Jinja2-level equivalent of `| safe` /
`{% autoescape false %}` that the task brief asked us to grep for. If
bleach's allowlist has a bypass on some adversarial input (bleach has had
real allowlist-bypass CVEs historically), the result is unescaped attacker
HTML/script content landing in the rendered report with no second line of
defense -- a stored-XSS-in-a-PDF/HTML-report bug. That makes
_sanitize_html() (reached lazily, only when one of these two fields is
truthy) the single highest-value thing this harness fuzzes. Every other
field below is fuzzed too (it costs nothing and autoescaping bugs/Jinja2
edge cases are still worth catching), but it is a secondary, lower-risk
surface by comparison.

Local verification without Atheris: Atheris ships no Windows wheel on PyPI,
so it cannot be installed or run in a Windows development environment. The
payload-construction and rendering logic below (build_payload /
render_one_case) has no dependency on atheris or FuzzedDataProvider --
only TestOneInput itself does -- so it can be exercised directly with plain
adversarial Python strings without installing atheris at all. See this
task's report for the exact commands run this way and their output; the
full Atheris/libFuzzer run (TestOneInput driven by real mutation) can only
be confirmed on ClusterFuzzLite's own Linux CI job.
"""
from __future__ import annotations

import datetime
import os
import sys

# app.core.config.Settings (pydantic-settings) raises at construction time if
# SECRET_KEY is unset or shorter than 32 chars (see the require_real_secret
# validator in app/core/config.py) -- refusing to start with the placeholder
# default. This harness's import chain reaches that module lazily, via the
# sanitize_html Jinja filter's `from app.services.incident_service import
# _sanitize_html`, the first time a rendered report has a truthy
# executive_summary/ai_executive_summary. Set a syntactically-valid,
# non-default value up front so that import never blows up mid-fuzz-run for
# a reason that has nothing to do with the code under test. This is not a
# production secret and grants no capability here -- nothing in this
# harness ever authenticates anything.
os.environ.setdefault(
    "SECRET_KEY", "fuzzing-harness-only-placeholder-not-a-real-secret-000000"
)

import atheris

with atheris.instrument_imports():
    from app.services.report_renderer.engine import _build_jinja_env
    from app.services.report_renderer.fixed_report import render_fixed_report_html
    from app.services.report_renderer.payload import ReportPayload


_FIXED_DT = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)

# Built once at import time and reused across every fuzz iteration -- this
# mirrors how the real code path caches a module-level `_jinja_env` in
# engine.py, and avoids re-parsing the Jinja2 template set on every call,
# which would otherwise dominate fuzzing throughput.
_JINJA_ENV = _build_jinja_env()


class _Obj:
    """Minimal attribute bag standing in for an ORM row.

    render_fixed_report_html() and the Jinja2 block partials it drives only
    ever *read* attributes off payload.incident / .analyst / .entries[] /
    .iocs[] / .tasks[] / .attachments[] -- they never touch a database
    session or any SQLAlchemy-specific behaviour. A plain attribute bag
    exercises exactly the same template code paths as the real ORM models
    (app.models.incident.Incident, app.models.user.User, ...) without
    pulling a live DB session into a fuzz harness that has no business
    needing one.
    """

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def build_payload(
    *,
    title: str,
    executive_summary: str,
    ai_executive_summary: str,
    analyst_name: str,
    entry_description: str,
    entry_source: str,
    ioc_value: str,
    task_title: str,
    attachment_name: str,
) -> ReportPayload:
    """Assemble a minimal-but-valid ReportPayload.

    Every field below is a fixed, safe placeholder EXCEPT the nine passed
    in as arguments, which are exactly the free-text fields a real attacker
    controls end-to-end in the app: an incident's title / executive
    summary, a timeline entry an analyst (or, via an ingested alert, an
    external source) types in, an IOC value pasted from a threat feed, a
    task title, an evidence filename an uploader supplies, and the
    display name on an analyst account. Those are the fields Atheris
    mutates; nothing else in this payload is attacker-reachable, so there
    is no point spending fuzzer entropy on it.
    """
    incident = _Obj(
        id="00000000-0000-0000-0000-000000000001",
        incident_ref="INC-2026-0001",
        title=title,
        severity="sev1",
        status="open",
        opened_at=_FIXED_DT,
        contained_at=None,
        closed_at=None,
        executive_summary=executive_summary,
        affected_users=1,
        metadata_={},
    )
    analyst = _Obj(
        id="00000000-0000-0000-0000-000000000002",
        full_name=analyst_name,
        email="analyst@example.com",
    )
    entry = _Obj(
        id="00000000-0000-0000-0000-000000000003",
        entry_type="note",
        occurred_at=_FIXED_DT,
        description=entry_description,
        source=entry_source,
        is_pinned=False,
    )
    ioc = _Obj(
        id="00000000-0000-0000-0000-000000000004",
        ioc_type="ip",
        value=ioc_value,
        description=None,
        confidence=50,
        status="active",
        created_at=_FIXED_DT,
        enrichment={},
    )
    task = _Obj(
        id="00000000-0000-0000-0000-000000000005",
        phase="containment",
        title=task_title,
        status="open",
        priority="medium",
    )
    attachment = _Obj(
        id="00000000-0000-0000-0000-000000000006",
        original_name=attachment_name,
        mime_type="text/plain",
        file_size=1024,
        sha256="0" * 64,
        created_at=_FIXED_DT,
    )

    entries = [entry]
    iocs = [ioc]
    tasks = [task]
    attachments = [attachment]

    return ReportPayload(
        incident=incident,
        entries=entries,
        iocs=iocs,
        tasks=tasks,
        attachments=attachments,
        analyst=analyst,
        generated_at=_FIXED_DT,
        duration_str="1 hour",
        entry_count=len(entries),
        ioc_count=len(iocs),
        task_completion_pct=0,
        tasks_by_phase={"containment": tasks},
        entries_by_type={"note": entries},
        iocs_by_status={"active": iocs},
        iocs_by_type={"ip": iocs},
        severity_label="SEV-1 (Critical)",
        status_label="Open",
        external_refs=[],
        contained_at_str=None,
        closed_at_str=None,
        ai_executive_summary=ai_executive_summary,
        ai_recommendations=None,
        graph_svg=None,
    )


def render_one_case(
    title: str,
    executive_summary: str,
    ai_executive_summary: str,
    analyst_name: str,
    entry_description: str,
    entry_source: str,
    ioc_value: str,
    task_title: str,
    attachment_name: str,
) -> str:
    """Build a payload from the given strings and render it to HTML.

    This is the actual property under test -- for any string values in
    these nine fields, rendering must produce an HTML string and must not
    raise. Kept free of any Atheris / FuzzedDataProvider dependency (see
    module docstring) so it can be called directly with plain strings as a
    stand-in verification path on platforms where atheris cannot be
    installed (e.g. Windows).
    """
    payload = build_payload(
        title=title,
        executive_summary=executive_summary,
        ai_executive_summary=ai_executive_summary,
        analyst_name=analyst_name,
        entry_description=entry_description,
        entry_source=entry_source,
        ioc_value=ioc_value,
        task_title=task_title,
        attachment_name=attachment_name,
    )
    return render_fixed_report_html(
        payload=payload,
        classification="CONFIDENTIAL",
        env=_JINJA_ENV,
    )


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    render_one_case(
        title=fdp.ConsumeUnicodeNoSurrogates(300),
        # Highest-value field -- see module docstring: reaches
        # bleach.clean() + markupsafe.Markup() via the sanitize_html filter,
        # deliberately opting out of Jinja2 autoescaping.
        executive_summary=fdp.ConsumeUnicodeNoSurrogates(6000),
        # Same sanitize_html / Markup path as executive_summary above.
        ai_executive_summary=fdp.ConsumeUnicodeNoSurrogates(4000),
        analyst_name=fdp.ConsumeUnicodeNoSurrogates(150),
        entry_description=fdp.ConsumeUnicodeNoSurrogates(800),
        entry_source=fdp.ConsumeUnicodeNoSurrogates(100),
        ioc_value=fdp.ConsumeUnicodeNoSurrogates(400),
        task_title=fdp.ConsumeUnicodeNoSurrogates(200),
        attachment_name=fdp.ConsumeUnicodeNoSurrogates(260),
    )
    # Deliberately no try/except here: an unhandled exception on
    # well-formed-but-hostile string input IS the bug this harness exists to
    # catch (e.g. a bleach allowlist edge case raising, or a template
    # assumption breaking on certain unicode). render_fixed_report_html has
    # no legitimate reason to raise on any str input to these nine fields --
    # if it does, that's a real finding for Atheris to report, not noise to
    # be filtered out.


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
