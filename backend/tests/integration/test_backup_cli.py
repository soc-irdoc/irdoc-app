"""Backup CLI: decrypt, rekey, verify (#149)."""
import hashlib
import io
import json
import os
import secrets
import uuid

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.cli import backup as cli
from app.core.config import settings
from app.models.attachment import Attachment
from app.models.backup import BackupRecord
from app.services import attachment_service
from app.services import backup_crypto as bc
from app.services.storage.local import LocalStorageBackend

KEY = "c" * 64


@pytest.fixture
def dedicated_key(monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_ENCRYPTION_KEY", KEY)
    monkeypatch.setattr(settings, "BACKUP_LEGACY_SECRET_KEYS", [])
    bc.clear_cache()
    yield
    bc.clear_cache()


def write_legacy(dir_, name: str, plaintext: bytes):
    nonce = secrets.token_bytes(12)
    key = bc.derive_secret_key_backup_key(settings.SECRET_KEY)
    path = dir_ / name
    path.write_bytes(nonce + AESGCM(key).encrypt(nonce, plaintext, None))
    path.with_suffix(".json").write_text(json.dumps({"version": "1.0"}))
    return path


def test_decrypt_legacy_and_v2(tmp_path, dedicated_key):
    legacy = write_legacy(tmp_path, "irdoc_backup_20260101T000000Z.enc", b"legacy")
    v2 = tmp_path / "irdoc_backup_20260102T000000Z.enc"
    v2.write_bytes(bc.encrypt(b"current"))
    out = io.StringIO()

    assert cli.decrypt_file(legacy, tmp_path / "a.tar.gz", out) == 0
    assert cli.decrypt_file(v2, tmp_path / "b.tar.gz", out) == 0
    assert (tmp_path / "a.tar.gz").read_bytes() == b"legacy"
    assert (tmp_path / "b.tar.gz").read_bytes() == b"current"


def test_decrypt_with_the_wrong_key_reports_the_fingerprint(tmp_path, dedicated_key):
    other = bytes.fromhex("d" * 64)
    path = tmp_path / "irdoc_backup_x.enc"
    path.write_bytes(bc.encrypt(b"x", key=other))
    out = io.StringIO()

    assert cli.decrypt_file(path, tmp_path / "x.tar.gz", out) == 1
    assert bc.fingerprint(other) in out.getvalue()
    assert not (tmp_path / "x.tar.gz").exists()


@pytest.mark.asyncio
async def test_rekey_legacy_to_v2_then_rerun_is_a_noop(tmp_path, dedicated_key, db_session):
    path = write_legacy(tmp_path, "irdoc_backup_20260101T000000Z.enc", b"bundle")
    db_session.add(BackupRecord(filename=path.name, size_bytes=1, destination="local", status="success"))
    await db_session.flush()

    out = io.StringIO()
    assert await cli.rekey(db_session, tmp_path, out=out) == 0

    header = bc.read_header(path)
    assert header.version == 2 and header.fingerprint == bc.active_fingerprint()
    assert bc.decrypt(path.read_bytes()) == b"bundle"
    assert json.loads(path.with_suffix(".json").read_text())["key_fingerprint"] == bc.active_fingerprint()
    record = (await db_session.execute(
        BackupRecord.__table__.select().where(BackupRecord.filename == path.name)
    )).first()
    assert record.key_fingerprint == bc.active_fingerprint()

    before = path.read_bytes()
    out = io.StringIO()
    assert await cli.rekey(db_session, tmp_path, out=out) == 0
    assert path.read_bytes() == before
    assert "rekeyed 0, already current 1" in out.getvalue()


@pytest.mark.asyncio
async def test_dry_run_changes_nothing(tmp_path, dedicated_key, db_session):
    path = write_legacy(tmp_path, "irdoc_backup_20260101T000000Z.enc", b"bundle")
    before = path.read_bytes()
    out = io.StringIO()

    assert await cli.rekey(db_session, tmp_path, dry_run=True, out=out) == 0
    assert path.read_bytes() == before
    assert "would rekey irdoc_backup_20260101T000000Z.enc" in out.getvalue()


@pytest.mark.asyncio
async def test_interrupted_rekey_leaves_the_original_intact(tmp_path, dedicated_key, db_session, monkeypatch):
    path = write_legacy(tmp_path, "irdoc_backup_20260101T000000Z.enc", b"bundle")
    before = path.read_bytes()

    def crash(*_a, **_k):
        raise OSError("disk full")
    monkeypatch.setattr(os, "replace", crash)

    out = io.StringIO()
    assert await cli.rekey(db_session, tmp_path, out=out) == 1
    assert path.read_bytes() == before
    assert not (tmp_path / (path.name + ".tmp")).exists()
    assert "FAILED" in out.getvalue()


@pytest.mark.asyncio
async def test_rekey_refuses_without_a_dedicated_key(tmp_path, db_session, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_ENCRYPTION_KEY", "")
    bc.clear_cache()
    try:
        assert await cli.rekey(db_session, tmp_path, out=io.StringIO()) == 1
    finally:
        bc.clear_cache()


# ── verify ───────────────────────────────────────────────────────────────────

@pytest.fixture
async def stored_files(tmp_path, monkeypatch, client, auth_headers, db_session):
    storage = LocalStorageBackend(str(tmp_path))
    monkeypatch.setattr(attachment_service, "get_storage_backend", lambda: storage)
    r = await client.post("/api/v1/incidents", json={"title": "V", "source": "other"}, headers=auth_headers)
    iid = uuid.UUID(r.json()["data"]["id"])
    rows = []
    for name, data in (("a.txt", b"alpha"), ("b.txt", b"bravo")):
        path = f"attachments/{iid}/{name}"
        await storage.store(data, path)
        att = Attachment(incident_id=iid, original_name=name, stored_path=path, mime_type="text/plain",
                         file_size=len(data), sha256=hashlib.sha256(data).hexdigest(), storage_backend="local")
        db_session.add(att)
        rows.append(att)
    await db_session.flush()
    return storage, iid, rows


@pytest.mark.asyncio
async def test_verify_all_ok(db_session, stored_files):
    _, iid, _ = stored_files
    out = io.StringIO()
    assert await cli.verify(db_session, str(iid), out=out) == 0
    assert "2 OK, 0 mismatch, 0 missing" in out.getvalue()


@pytest.mark.asyncio
async def test_verify_reports_a_tampered_file(db_session, stored_files):
    storage, iid, rows = stored_files
    await storage.store(b"tampered", rows[0].stored_path)
    out = io.StringIO()

    assert await cli.verify(db_session, str(iid), out=out) == 1
    assert "MISMATCH" in out.getvalue() and "1 OK, 1 mismatch, 0 missing" in out.getvalue()


@pytest.mark.asyncio
async def test_verify_reports_a_missing_file(db_session, stored_files):
    storage, iid, rows = stored_files
    await storage.delete(rows[1].stored_path)
    out = io.StringIO()

    assert await cli.verify(db_session, str(iid), out=out) == 1
    assert "MISSING" in out.getvalue() and "1 OK, 0 mismatch, 1 missing" in out.getvalue()
