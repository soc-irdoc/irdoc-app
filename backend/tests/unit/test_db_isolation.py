"""Guards the test fixtures themselves (#55).

The schema is created once per run and each test's writes are rolled back at
teardown, including ones the test (or app code) committed. If that rollback
ever stops working, these fail instead of later tests silently seeing data
left behind by earlier ones. The two tests run in file order.
"""
from sqlalchemy import func, select

from app.models.organization import Organization


async def test_committed_rows_are_visible_within_the_test(db_session):
    db_session.add(Organization(name="Leak check", slug="leak-check"))
    await db_session.commit()

    count = await db_session.scalar(select(func.count()).select_from(Organization))
    assert count == 1


async def test_committed_rows_do_not_leak_into_the_next_test(db_session):
    count = await db_session.scalar(select(func.count()).select_from(Organization))
    assert count == 0


async def test_rollback_after_commit_keeps_the_committed_rows(db_session):
    """commit() only releases a SAVEPOINT, so a later rollback() must not undo it."""
    db_session.add(Organization(name="Kept", slug="kept"))
    await db_session.commit()
    db_session.add(Organization(name="Dropped", slug="dropped"))
    await db_session.flush()
    await db_session.rollback()

    slugs = (await db_session.scalars(select(Organization.slug))).all()
    assert slugs == ["kept"]
