"""Link IOCs to the timeline entries they were seen in (Refs #152)."""
import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from tests.integration.test_evidence import (  # noqa: F401
    _entry,
    _incident,
    _upload,
    _user,
    local_storage,
)


async def _ioc(client, headers, iid, value="evil.example.com", ioc_type="domain") -> str:
    r = await client.post(f"/api/v1/incidents/{iid}/iocs", json={"ioc_type": ioc_type, "value": value},
                          headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


def _link_url(iid, ioc_id, entry_id):
    return f"/api/v1/incidents/{iid}/iocs/{ioc_id}/links/{entry_id}"


@pytest.mark.asyncio
async def test_link_and_unlink(client, auth_headers):
    iid = await _incident(client, auth_headers)
    eid = await _entry(client, auth_headers, iid)
    ioc = await _ioc(client, auth_headers, iid)

    r = await client.post(_link_url(iid, ioc, eid), headers=auth_headers)
    assert r.status_code == 201, r.text
    links = (await client.get(f"/api/v1/incidents/{iid}/ioc-links", headers=auth_headers)).json()["data"]
    assert links == [{"ioc_id": ioc, "timeline_entry_id": eid}]

    # Linking again is harmless
    assert (await client.post(_link_url(iid, ioc, eid), headers=auth_headers)).status_code == 201
    links = (await client.get(f"/api/v1/incidents/{iid}/ioc-links", headers=auth_headers)).json()["data"]
    assert len(links) == 1

    assert (await client.delete(_link_url(iid, ioc, eid), headers=auth_headers)).status_code == 204
    links = (await client.get(f"/api/v1/incidents/{iid}/ioc-links", headers=auth_headers)).json()["data"]
    assert links == []


@pytest.mark.asyncio
async def test_link_changes_are_audited_once(client, auth_headers, db_session):
    iid = await _incident(client, auth_headers)
    eid = await _entry(client, auth_headers, iid)
    ioc = await _ioc(client, auth_headers, iid)

    await client.post(_link_url(iid, ioc, eid), headers=auth_headers)
    await client.post(_link_url(iid, ioc, eid), headers=auth_headers)  # no-op, not audited
    await client.delete(_link_url(iid, ioc, eid), headers=auth_headers)
    await client.delete(_link_url(iid, ioc, eid), headers=auth_headers)  # no-op

    actions = [a for (a,) in (await db_session.execute(
        select(AuditLog.action).where(AuditLog.action.in_(["ioc.linked", "ioc.unlinked"])).order_by(AuditLog.id)
    )).all()]
    assert actions == ["ioc.linked", "ioc.unlinked"]
    row = (await db_session.execute(select(AuditLog).where(AuditLog.action == "ioc.linked"))).scalar_one()
    assert row.diff["timeline_entry_id"] == eid
    assert row.entity_label == "domain: evil.example.com"


@pytest.mark.asyncio
async def test_ioc_and_entry_must_belong_to_the_incident(client, auth_headers):
    a = await _incident(client, auth_headers)
    b = await _incident(client, auth_headers)
    entry_a = await _entry(client, auth_headers, a)
    entry_b = await _entry(client, auth_headers, b)
    ioc_a = await _ioc(client, auth_headers, a)
    ioc_b = await _ioc(client, auth_headers, b)

    # Mixing incidents is a 404, never a link across incidents
    assert (await client.post(_link_url(a, ioc_a, entry_b), headers=auth_headers)).status_code == 404
    assert (await client.post(_link_url(a, ioc_b, entry_a), headers=auth_headers)).status_code == 404
    assert (await client.post(_link_url(b, ioc_a, entry_a), headers=auth_headers)).status_code == 404


@pytest.mark.asyncio
async def test_viewers_can_read_links_but_not_change_them(client, auth_headers, admin_user, db_session):
    iid = await _incident(client, auth_headers)
    eid = await _entry(client, auth_headers, iid)
    ioc = await _ioc(client, auth_headers, iid)
    viewer = await _user(db_session, admin_user[1].id, "viewer")

    assert (await client.post(_link_url(iid, ioc, eid), headers=viewer)).status_code == 403
    assert (await client.get(f"/api/v1/incidents/{iid}/ioc-links", headers=viewer)).status_code == 200


@pytest.mark.asyncio
async def test_evidence_shows_links_both_ways(client, auth_headers):
    iid = await _incident(client, auth_headers)
    eid = await _entry(client, auth_headers, iid)
    await _upload(client, auth_headers, iid, "mail.eml", b"From: x", entry_id=eid)
    await _upload(client, auth_headers, iid, "unrelated.txt", b"nothing")
    ioc = await _ioc(client, auth_headers, iid)
    await client.post(_link_url(iid, ioc, eid), headers=auth_headers)

    iocs = (await client.get(f"/api/v1/incidents/{iid}/evidence/iocs", headers=auth_headers)).json()["data"]
    assert [e["entry_id"] for e in iocs[0]["linked_entries"]] == [eid]
    assert iocs[0]["file_count"] == 1

    files = (await client.get(f"/api/v1/incidents/{iid}/evidence", headers=auth_headers)).json()["data"]
    by_name = {f["original_name"]: f for f in files}
    assert [i["value"] for i in by_name["mail.eml"]["linked_iocs"]] == ["evil.example.com"]
    assert by_name["unrelated.txt"]["linked_iocs"] == []


@pytest.mark.asyncio
async def test_evidence_hides_linked_iocs_without_ioc_permission(client, auth_headers, admin_user, db_session,
                                                                monkeypatch):
    from app.core import permissions
    monkeypatch.setitem(permissions.PERMISSIONS, "iocs.read", "admin")
    iid = await _incident(client, auth_headers)
    eid = await _entry(client, auth_headers, iid)
    await _upload(client, auth_headers, iid, "mail.eml", b"From: x", entry_id=eid)
    viewer = await _user(db_session, admin_user[1].id, "viewer")

    files = (await client.get(f"/api/v1/incidents/{iid}/evidence", headers=viewer)).json()["data"]
    assert files[0]["linked_iocs"] is None
