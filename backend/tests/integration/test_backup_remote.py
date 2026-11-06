"""SFTP / SMB backup destinations: API and backup flow (#151)."""
import pytest

from app.models.backup import BackupConfig, BackupRecord
from app.services import backup_destinations, backup_service
from app.services.backup_destinations import TestResult

URL = "/api/v1/admin/backup/remote"
SFTP = {"host": "sftp.example.com", "port": 22, "username": "irdoc", "remote_dir": "/backups",
        "auth": "password", "password": "s3cret"}
HOST_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl"


@pytest.mark.asyncio
async def test_secrets_are_never_returned(client, auth_headers):
    put = await client.put(f"{URL}/sftp", json=SFTP, headers=auth_headers)
    get = await client.get(f"{URL}/sftp", headers=auth_headers)

    for r in (put, get):
        assert r.status_code == 200
        data = r.json()["data"]
        assert "password" not in data and "s3cret" not in r.text
        assert data["password_set"] is True and data["host"] == "sftp.example.com"


@pytest.mark.asyncio
async def test_empty_secret_keeps_the_stored_one(client, auth_headers, db_session):
    await client.put(f"{URL}/sftp", json=SFTP, headers=auth_headers)
    await client.put(f"{URL}/sftp", json={**SFTP, "password": "", "remote_dir": "/other"}, headers=auth_headers)

    row = await backup_destinations.get_remote_config(db_session, "sftp")
    from app.services.integration_service import decrypt_config
    cfg = decrypt_config(row.config)
    assert cfg["password"] == "s3cret" and cfg["remote_dir"] == "/other"
    assert row.config["password"] != "s3cret"  # stored encrypted


@pytest.mark.asyncio
async def test_pinning_and_changing_the_host_drops_the_pin(client, auth_headers):
    pinned = await client.put(f"{URL}/sftp", json={**SFTP, "host_key": HOST_KEY}, headers=auth_headers)
    assert pinned.json()["data"]["host_key_pinned"] is True
    assert pinned.json()["data"]["host_key_fingerprint"].startswith("SHA256:")

    same = await client.put(f"{URL}/sftp", json={**SFTP, "remote_dir": "/x"}, headers=auth_headers)
    assert same.json()["data"]["host_key_pinned"] is True

    moved = await client.put(f"{URL}/sftp", json={**SFTP, "host": "evil.example.com"}, headers=auth_headers)
    assert moved.json()["data"]["host_key_pinned"] is False


@pytest.mark.asyncio
async def test_first_sftp_test_asks_to_confirm_the_host_key(client, auth_headers, monkeypatch):
    from app.services.backup_destinations import sftp

    async def fake_fetch(host, port):
        return HOST_KEY, "SHA256:abc"
    monkeypatch.setattr(sftp, "fetch_host_key", fake_fetch)

    r = await client.post(f"{URL}/sftp/test", json=SFTP, headers=auth_headers)

    data = r.json()["data"]
    assert data["ok"] is False and data["needs_host_key_confirmation"] is True
    assert data["host_key"] == HOST_KEY and data["host_key_fingerprint"] == "SHA256:abc"


@pytest.mark.asyncio
async def test_test_connection_reports_the_error_verbatim(client, auth_headers, monkeypatch):
    class Failing:
        async def test(self):
            return TestResult(ok=False, error="Permission denied (publickey)")
    monkeypatch.setattr(backup_destinations, "build_destination", lambda *a, **k: Failing())

    r = await client.post(f"{URL}/smb/test", json={"server": "nas", "share": "b"}, headers=auth_headers)

    assert r.json()["data"] == {
        "ok": False, "error": "Permission denied (publickey)", "needs_host_key_confirmation": False,
        "host_key": None, "host_key_fingerprint": None,
    }


@pytest.mark.asyncio
async def test_sftp_cannot_be_selected_until_configured_and_pinned(client, auth_headers):
    url = "/api/v1/admin/backup/config"
    assert (await client.put(url, json={"destination": "sftp"}, headers=auth_headers)).status_code == 422
    await client.put(f"{URL}/sftp", json=SFTP, headers=auth_headers)
    assert (await client.put(url, json={"destination": "sftp"}, headers=auth_headers)).status_code == 422
    await client.put(f"{URL}/sftp", json={**SFTP, "host_key": HOST_KEY}, headers=auth_headers)
    assert (await client.put(url, json={"destination": "sftp"}, headers=auth_headers)).status_code == 200


@pytest.mark.asyncio
async def test_smb_validation(client, auth_headers):
    r = await client.put(f"{URL}/smb", json={"server": "bad host", "share": "b"}, headers=auth_headers)
    assert r.status_code == 422


# ── Backup flow ──────────────────────────────────────────────────────────────

class FakeDest:
    kind = "sftp"

    def __init__(self, fail=False, names=None):
        self.fail, self.uploaded, self.deleted = fail, [], []
        self.names = names or []

    async def upload(self, path, name):
        if self.fail:
            raise backup_destinations.RemoteBackupError("Connection refused")
        self.uploaded.append((name, path.read_bytes()))

    async def list_backups(self):
        return self.names

    async def delete(self, name):
        self.deleted.append(name)


@pytest.fixture
def backup_env(tmp_path, monkeypatch, db_session):
    monkeypatch.setattr(backup_service, "BACKUP_DIR", tmp_path)

    async def fake_dump():
        return b"-- sql"
    monkeypatch.setattr(backup_service, "_dump_database", fake_dump)
    monkeypatch.setattr(backup_service, "_archive_storage", lambda: b"")

    def use(dest):
        async def resolve(db, kind):
            return dest
        monkeypatch.setattr(backup_destinations, "resolve_destination", resolve)
    return tmp_path, use


async def _sftp_config(db_session):
    cfg = await backup_service.get_or_create_config(db_session)
    cfg.destination = "sftp"
    await db_session.commit()
    return cfg


@pytest.mark.asyncio
async def test_backup_uploads_after_writing_the_local_copy(db_session, backup_env):
    tmp, use = backup_env
    dest = FakeDest()
    use(dest)
    await _sftp_config(db_session)

    record = await backup_service.run_backup(db_session)

    assert record.status == "success" and record.destination == "sftp"
    assert (tmp / record.filename).is_file()
    assert dest.uploaded[0][0] == record.filename
    assert dest.uploaded[0][1] == (tmp / record.filename).read_bytes()
    assert not list(tmp.glob("*.part"))


@pytest.mark.asyncio
async def test_failed_upload_marks_the_backup_failed_and_keeps_the_local_copy(db_session, backup_env):
    tmp, use = backup_env
    use(FakeDest(fail=True))
    await _sftp_config(db_session)

    with pytest.raises(backup_service.RemoteUploadError):
        await backup_service.run_backup(db_session)

    from sqlalchemy import select
    record = (await db_session.execute(select(BackupRecord))).scalars().one()
    config = (await db_session.execute(select(BackupConfig))).scalars().one()
    assert record.status == "failed"
    assert "Remote upload (sftp) failed: Connection refused" in record.error
    assert config.last_backup_status == "failed" and "Connection refused" in config.last_backup_error
    assert (tmp / record.filename).is_file() and record.size_bytes


@pytest.mark.asyncio
async def test_remote_retention_deletes_only_expired_backups(db_session, backup_env):
    _, use = backup_env
    dest = FakeDest(names=["irdoc_backup_20200101T000000Z.enc", "irdoc_backup_20991231T000000Z.enc",
                           "irdoc_backup_20200101T000000Z.enc.part", "keep-me.enc"])
    use(dest)
    cfg = await _sftp_config(db_session)

    await backup_service._run_retention(db_session, cfg)

    assert dest.deleted == ["irdoc_backup_20200101T000000Z.enc"]


@pytest.mark.asyncio
async def test_cloud_destination_fails_loudly_without_cloud_storage(db_session):
    from app.services.backup_destinations.cloud import load_cloud_backend
    with pytest.raises(backup_destinations.RemoteBackupError, match="no cloud storage"):
        await load_cloud_backend(db_session)


@pytest.mark.asyncio
async def test_stored_secret_is_not_sent_to_a_different_host(client, auth_headers, monkeypatch):
    """Security: re-pointing the settings must not reuse the saved password."""
    await client.put(f"{URL}/sftp", json={**SFTP, "host_key": HOST_KEY}, headers=auth_headers)
    seen = []

    class Recorder:
        async def test(self):
            return TestResult(ok=True)

    def build(kind, cfg, host_key=None):
        seen.append(cfg)
        return Recorder()
    monkeypatch.setattr(backup_destinations, "build_destination", build)

    for change in ({"host": "attacker.example.com"}, {"port": 2222}, {"username": "root"}):
        await client.post(f"{URL}/sftp/test", json={**SFTP, "password": "", **change}, headers=auth_headers)
    await client.post(f"{URL}/sftp/test", json={**SFTP, "password": ""}, headers=auth_headers)

    assert [c["password"] or None for c in seen] == [None, None, None, "s3cret"]


@pytest.mark.asyncio
async def test_saving_a_new_host_without_a_password_drops_the_old_one(client, auth_headers, db_session):
    await client.put(f"{URL}/smb", json={"server": "nas", "share": "b", "username": "u", "password": "pw"},
                     headers=auth_headers)
    r = await client.put(f"{URL}/smb", json={"server": "other", "share": "b", "username": "u"}, headers=auth_headers)
    assert r.json()["data"]["password_set"] is False
