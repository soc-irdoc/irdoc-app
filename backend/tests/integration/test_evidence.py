"""Evidence register (#150): read-only list of an incident's files and IOCs."""
import csv
import hashlib
import io
import uuid

import pytest

from app.core import permissions
from app.core.security import create_access_token, hash_password
from app.models.asset import Asset, AssetTimelineLink
from app.models.attachment import Attachment
from app.models.user import User
from app.services import attachment_service
from app.services.storage.local import LocalStorageBackend

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


@pytest.fixture(autouse=True)
def local_storage(tmp_path, monkeypatch):
    backend = LocalStorageBackend(str(tmp_path))
    monkeypatch.setattr(attachment_service, "get_storage_backend", lambda: backend)
    # No Celery broker in tests.
    from app.workers import tasks
    monkeypatch.setattr(tasks.verify_file_hash, "delay", lambda *a, **k: None)
    return backend


async def _incident(client, headers) -> str:
    r = await client.post(
        "/api/v1/incidents", json={"title": "Evidence", "source": "siem_alert"}, headers=headers
    )
    return r.json()["data"]["id"]


async def _entry(client, headers, iid, description="<p>Found <b>dropper</b> on WS-01</p>") -> str:
    r = await client.post(
        f"/api/v1/incidents/{iid}/timeline",
        json={"entry_type": "evidence", "description": description, "occurred_at": "2026-11-01T10:00:00Z"},
        headers=headers,
    )
    return r.json()["data"]["id"]


async def _upload(client, headers, iid, name, data, entry_id=None) -> dict:
    form = {"timeline_entry_id": entry_id} if entry_id else {}
    r = await client.post(
        f"/api/v1/incidents/{iid}/attachments", files={"file": (name, data)}, data=form, headers=headers
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def _user(db_session, org_id, role: str) -> dict:
    user = User(
        id=uuid.uuid4(), org_id=org_id, email=f"{role}-{uuid.uuid4().hex[:6]}@test.com",
        full_name=f"Test {role}", password_hash=hash_password("Pass123!"), role=role,
        is_active=True, must_reset_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    return {"Authorization": f"Bearer {create_access_token(str(user.id), str(user.org_id))}"}


@pytest.mark.asyncio
async def test_lists_timeline_and_incident_level_files_with_their_source(client, auth_headers, db_session):
    iid = await _incident(client, auth_headers)
    eid = await _entry(client, auth_headers, iid)
    await _upload(client, auth_headers, iid, "notes.txt", b"hello", entry_id=eid)
    db_session.add(Attachment(
        incident_id=uuid.UUID(iid), original_name="memo.pdf", stored_path="attachments/x/memo.pdf",
        mime_type="application/pdf", file_size=3, sha256="0" * 64, storage_backend="local",
    ))
    await db_session.flush()

    r = await client.get(f"/api/v1/incidents/{iid}/evidence?sort=name&order=asc", headers=auth_headers)

    assert r.status_code == 200
    body = r.json()
    assert body["meta"] == {"page": 1, "per_page": 50, "total": 2}
    memo, notes = body["data"]
    assert memo["original_name"] == "memo.pdf" and memo["kind"] == "incident" and memo["source"] is None
    assert notes["kind"] == "timeline"
    assert notes["source"]["entry_id"] == eid
    assert notes["source"]["excerpt"] == "Found dropper on WS-01"
    assert notes["uploaded_by_name"]


@pytest.mark.asyncio
async def test_filters_search_and_paging(client, auth_headers):
    iid = await _incident(client, auth_headers)
    eid = await _entry(client, auth_headers, iid)
    await _upload(client, auth_headers, iid, "shot.png", _PNG, entry_id=eid)
    txt = await _upload(client, auth_headers, iid, "log.txt", b"line", entry_id=eid)

    async def names(qs):
        r = await client.get(f"/api/v1/incidents/{iid}/evidence?{qs}", headers=auth_headers)
        return [f["original_name"] for f in r.json()["data"]]

    assert await names("hide_screenshots=true") == ["log.txt"]
    assert await names("mime=image/") == ["shot.png"]
    assert await names(f"q={txt['sha256'][:12]}") == ["log.txt"]
    assert await names("q=SHOT") == ["shot.png"]
    assert await names("kind=incident") == []
    page2 = await client.get(f"/api/v1/incidents/{iid}/evidence?per_page=1&page=2", headers=auth_headers)
    assert page2.json()["meta"]["total"] == 2 and len(page2.json()["data"]) == 1


@pytest.mark.asyncio
async def test_hash_ioc_match_is_case_insensitive(client, auth_headers):
    iid = await _incident(client, auth_headers)
    eid = await _entry(client, auth_headers, iid)
    data = b"malware sample"
    await _upload(client, auth_headers, iid, "sample.bin", data, entry_id=eid)
    sha = hashlib.sha256(data).hexdigest()
    await client.post(
        f"/api/v1/incidents/{iid}/iocs", json={"ioc_type": "hash", "value": sha.upper()}, headers=auth_headers
    )

    files = (await client.get(f"/api/v1/incidents/{iid}/evidence", headers=auth_headers)).json()["data"]
    iocs = (await client.get(f"/api/v1/incidents/{iid}/evidence/iocs", headers=auth_headers)).json()["data"]

    assert [m["value"] for m in files[0]["ioc_matches"]] == [sha.upper()]
    assert iocs[0]["matching_files"] == [files[0]["id"]]
    assert iocs[0]["linked_entries"] == [] and iocs[0]["file_count"] == 0


@pytest.mark.asyncio
async def test_asset_chips_come_from_the_entry(client, auth_headers, db_session):
    iid = await _incident(client, auth_headers)
    eid = await _entry(client, auth_headers, iid)
    await _upload(client, auth_headers, iid, "a.txt", b"a", entry_id=eid)
    asset = Asset(incident_id=uuid.UUID(iid), asset_type="workstation", name="WS-01")
    db_session.add(asset)
    await db_session.flush()
    db_session.add(AssetTimelineLink(asset_id=asset.id, timeline_entry_id=uuid.UUID(eid)))
    await db_session.flush()

    files = (await client.get(f"/api/v1/incidents/{iid}/evidence", headers=auth_headers)).json()["data"]

    assert [a["name"] for a in files[0]["assets"]] == ["WS-01"]


@pytest.mark.asyncio
async def test_chips_hidden_without_asset_and_ioc_read(client, auth_headers, admin_user, db_session, monkeypatch):
    iid = await _incident(client, auth_headers)
    await _upload(client, auth_headers, iid, "a.txt", b"a", entry_id=await _entry(client, auth_headers, iid))
    viewer = await _user(db_session, admin_user[0].org_id, "viewer")
    monkeypatch.setitem(permissions.PERMISSIONS, "assets.read", "analyst")
    monkeypatch.setitem(permissions.PERMISSIONS, "iocs.read", "analyst")

    r = await client.get(f"/api/v1/incidents/{iid}/evidence", headers=viewer)
    iocs = await client.get(f"/api/v1/incidents/{iid}/evidence/iocs", headers=viewer)

    assert r.status_code == 200
    assert r.json()["data"][0]["assets"] is None and r.json()["data"][0]["ioc_matches"] is None
    assert iocs.status_code == 403


@pytest.mark.asyncio
async def test_needs_attachments_read(client, auth_headers, admin_user, db_session, monkeypatch):
    iid = await _incident(client, auth_headers)
    viewer = await _user(db_session, admin_user[0].org_id, "viewer")
    monkeypatch.setitem(permissions.PERMISSIONS, "attachments.read", "analyst")

    r = await client.get(f"/api/v1/incidents/{iid}/evidence", headers=viewer)
    csv_r = await client.get(f"/api/v1/incidents/{iid}/evidence/export.csv", headers=viewer)

    assert r.status_code == 403 and csv_r.status_code == 403


@pytest.mark.asyncio
async def test_other_org_gets_404(client, auth_headers, db_session):
    iid = await _incident(client, auth_headers)
    from app.models.organization import Organization
    org = Organization(name="Other", slug=f"other-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    await db_session.flush()
    outsider = await _user(db_session, org.id, "admin")

    r = await client.get(f"/api/v1/incidents/{iid}/evidence", headers=outsider)

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_csv_export_is_a_chain_of_custody_list(client, auth_headers):
    iid = await _incident(client, auth_headers)
    eid = await _entry(client, auth_headers, iid)
    up = await _upload(client, auth_headers, iid, "=HYPERLINK(evil).txt", b"x", entry_id=eid)

    r = await client.get(f"/api/v1/incidents/{iid}/evidence/export.csv", headers=auth_headers)

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert rows[0]["sha256"] == up["sha256"]
    assert rows[0]["source_entry_id"] == eid
    assert rows[0]["file_name"] == "'=HYPERLINK(evil).txt"  # formula neutralised


# ── Text preview & MIME detection ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_text_files_are_detected_and_previewed_as_text(client, auth_headers):
    iid = await _incident(client, auth_headers)
    up = await _upload(client, auth_headers, iid, "notes.txt", b"<script>alert(1)</script>")

    assert up["mime_type"] == "text/plain"
    r = await client.get(f"/api/v1/incidents/{iid}/attachments/{up['id']}/text", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["data"] == {"text": "<script>alert(1)</script>", "truncated": False}


@pytest.mark.asyncio
async def test_binary_with_a_text_extension_is_not_text(client, auth_headers):
    iid = await _incident(client, auth_headers)
    up = await _upload(client, auth_headers, iid, "fake.txt", b"\x01\x02\x00\xffbinary")

    assert up["mime_type"] == "application/octet-stream"
    r = await client.get(f"/api/v1/incidents/{iid}/attachments/{up['id']}/text", headers=auth_headers)
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_html_and_svg_are_never_previewed(client, auth_headers, db_session):
    iid = await _incident(client, auth_headers)
    for mime in ("text/html", "image/svg+xml"):
        att = Attachment(
            incident_id=uuid.UUID(iid), original_name="x", stored_path="attachments/x/x",
            mime_type=mime, file_size=1, sha256="1" * 64, storage_backend="local",
        )
        db_session.add(att)
        await db_session.flush()
        r = await client.get(f"/api/v1/incidents/{iid}/attachments/{att.id}/text", headers=auth_headers)
        assert r.status_code == 415, mime


@pytest.mark.asyncio
async def test_text_preview_is_truncated_at_1mb(client, auth_headers):
    iid = await _incident(client, auth_headers)
    big = b"a" * (attachment_service.TEXT_PREVIEW_MAX_BYTES + 10)
    up = await _upload(client, auth_headers, iid, "big.log", big)

    data = (await client.get(
        f"/api/v1/incidents/{iid}/attachments/{up['id']}/text", headers=auth_headers
    )).json()["data"]

    assert data["truncated"] is True
    assert len(data["text"]) == attachment_service.TEXT_PREVIEW_MAX_BYTES
