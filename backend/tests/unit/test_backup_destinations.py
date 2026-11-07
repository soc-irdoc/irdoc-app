"""Backup destinations without a real server (#151)."""
import sys
import types
from datetime import UTC, datetime

import pytest

from app.services.backup_destinations import RemoteBackupError, build_destination, expired_backups
from app.services.backup_destinations.base import backup_timestamp


def test_retention_only_touches_exact_backup_names():
    cutoff = datetime(2026, 6, 1, tzinfo=UTC)
    names = [
        "irdoc_backup_20260101T000000Z.enc",        # old: deleted
        "irdoc_backup_20260701T000000Z.enc",        # new: kept
        "irdoc_backup_20260101T000000Z.enc.part",   # half-written: never touched
        "irdoc_backup_20260101T000000Z.json",
        "irdoc_backup_old.enc",                     # not a real timestamp
        "foo.enc",
        "notes.txt",
        "IRDOC_BACKUP_20260101T000000Z.enc",
    ]
    assert expired_backups(names, cutoff) == ["irdoc_backup_20260101T000000Z.enc"]


def test_timestamp_comes_from_the_name():
    assert backup_timestamp("irdoc_backup_20261107T153000Z.enc") == datetime(2026, 11, 7, 15, 30, tzinfo=UTC)
    assert backup_timestamp("irdoc_backup_x.enc") is None


def test_build_destination_rejects_unknown_kinds_and_missing_fields():
    with pytest.raises(RemoteBackupError):
        build_destination("ftp", {})
    with pytest.raises(RemoteBackupError):
        build_destination("smb", {"share": "backups"})  # no server


@pytest.mark.asyncio
async def test_sftp_never_connects_without_a_pinned_host_key():
    dest = build_destination("sftp", {"host": "nas", "username": "u", "password": "p"}, host_key=None)
    with pytest.raises(RemoteBackupError, match="not pinned"):
        await dest.list_backups()


# ── SMB, with smbclient replaced by a fake ────────────────────────────────────

class _FakeSMB(types.ModuleType):
    def __init__(self, dialect: int):
        super().__init__("smbclient")
        self.dialect = dialect
        self.calls: list = []
        self.files: dict[str, bytes] = {}

    def register_session(self, server, **kw):
        self.calls.append(("register_session", server, kw))
        return types.SimpleNamespace(connection=types.SimpleNamespace(dialect=self.dialect))

    def reset_connection_cache(self, **kw):
        pass

    def listdir(self, path, **kw):
        return ["irdoc_backup_20260101T000000Z.enc", "other.txt"]

    def remove(self, path, **kw):
        self.calls.append(("remove", path))

    def replace(self, src, dst, **kw):
        self.calls.append(("replace", src, dst))

    def open_file(self, path, mode="rb", **kw):
        import io
        fake = self

        class _W(io.BytesIO):
            def __exit__(self, *a):
                fake.files[path] = self.getvalue()
                return super().__exit__(*a)
        self.calls.append(("open_file", path, mode))
        return _W()


@pytest.fixture
def fake_smb(monkeypatch):
    def install(dialect: int):
        fake = _FakeSMB(dialect)
        conn_mod = types.ModuleType("smbprotocol.connection")
        conn_mod.Dialects = types.SimpleNamespace(SMB_3_0_0=0x0300)
        monkeypatch.setitem(sys.modules, "smbclient", fake)
        monkeypatch.setitem(sys.modules, "smbprotocol", types.ModuleType("smbprotocol"))
        monkeypatch.setitem(sys.modules, "smbprotocol.connection", conn_mod)
        return fake
    return install


SMB_CFG = {"server": "nas", "share": "backups", "path": "irdoc/prod", "username": "u", "password": "p"}


@pytest.mark.asyncio
async def test_smb_refuses_dialects_older_than_3(fake_smb):
    fake_smb(0x0210)
    result = await build_destination("smb", SMB_CFG).test()
    assert not result.ok and "SMB 3" in result.error


@pytest.mark.asyncio
async def test_smb_requires_encryption_by_default(fake_smb):
    fake = fake_smb(0x0311)
    assert (await build_destination("smb", SMB_CFG).test()).ok
    assert fake.calls[0][2]["encrypt"] is True

    fake = fake_smb(0x0311)
    await build_destination("smb", {**SMB_CFG, "require_encryption": False}).test()
    assert fake.calls[0][2]["encrypt"] is False


@pytest.mark.asyncio
async def test_smb_upload_writes_part_then_renames(fake_smb, tmp_path):
    fake = fake_smb(0x0311)
    local = tmp_path / "irdoc_backup_20260101T000000Z.enc"
    local.write_bytes(b"encrypted")

    await build_destination("smb", SMB_CFG).upload(local, local.name)

    final = "\\\\nas\\backups\\irdoc\\prod\\irdoc_backup_20260101T000000Z.enc"
    assert fake.files[final + ".part"] == b"encrypted"
    assert ("replace", final + ".part", final) in fake.calls


@pytest.mark.asyncio
async def test_smb_domain_is_prefixed_to_the_user(fake_smb):
    fake = fake_smb(0x0311)
    await build_destination("smb", {**SMB_CFG, "domain": "CORP"}).test()
    assert fake.calls[0][2]["username"] == "CORP\\u"
