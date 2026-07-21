"""
Regression test for the fresh-install admin takeover bug.

seed.py used to create a hardcoded admin@localhost / ChangeMe123! account on
every fresh install, before the installer wizard's own /auth/setup call could
run. Because the wizard treated 409 ("setup already done") as success, the
operator's chosen credentials were silently discarded and the public,
well-known default account remained the real admin.

seed() must now only ever create org-agnostic system templates — never an
org or a user — so that the first-run setup flow is the sole path that can
create an admin account.
"""
import seed as seed_module
from sqlalchemy import select

from app.models.organization import Organization
from app.models.template import IncidentTemplate, ReportTemplate
from app.models.user import User
from app.services import auth_service


async def test_seed_creates_no_org_or_admin_user(db_session):
    seed_module.AsyncSessionLocal = lambda: db_session
    await seed_module.seed()
    await db_session.commit()

    assert (await db_session.execute(select(User))).scalar_one_or_none() is None
    assert (await db_session.execute(select(Organization))).scalar_one_or_none() is None
    assert not await auth_service.setup_complete(db_session)


async def test_seed_still_creates_system_templates(db_session):
    seed_module.AsyncSessionLocal = lambda: db_session
    await seed_module.seed()
    await db_session.commit()

    incident_templates = (
        await db_session.execute(select(IncidentTemplate).where(IncidentTemplate.is_system.is_(True)))
    ).scalars().all()
    report_templates = (
        await db_session.execute(select(ReportTemplate).where(ReportTemplate.is_system.is_(True)))
    ).scalars().all()

    assert len(incident_templates) == 4
    assert len(report_templates) == 3


async def test_seed_is_idempotent(db_session):
    seed_module.AsyncSessionLocal = lambda: db_session
    await seed_module.seed()
    await db_session.commit()
    await seed_module.seed()  # second run (e.g. container restart) must not duplicate templates
    await db_session.commit()

    incident_templates = (
        await db_session.execute(select(IncidentTemplate).where(IncidentTemplate.is_system.is_(True)))
    ).scalars().all()
    assert len(incident_templates) == 4
