"""SFTP destination against a real (in-process) asyncssh server (#151).

Skipped when asyncssh isn't installed.
"""
import pytest

asyncssh = pytest.importorskip("asyncssh")

from app.services.backup_destinations import RemoteBackupError, build_destination  # noqa: E402
from app.services.backup_destinations.sftp import fetch_host_key  # noqa: E402


class _Server(asyncssh.SSHServer):
    def begin_auth(self, username):
        return True

    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        return username == "irdoc" and password == "pw"


@pytest.fixture
async def sftp_server(tmp_path):
    root = tmp_path / "remote"
    (root / "backups").mkdir(parents=True)
    host_key = asyncssh.generate_private_key("ssh-ed25519")
    server = await asyncssh.listen(
        "127.0.0.1", 0, server_host_keys=[host_key], server_factory=_Server,
        sftp_factory=lambda chan: asyncssh.SFTPServer(chan, chroot=str(root)),
    )
    port = server.sockets[0].getsockname()[1]
    yield {
        "root": root,
        "cfg": {"host": "127.0.0.1", "port": port, "username": "irdoc", "password": "pw", "remote_dir": "/backups"},
        "host_key": host_key.export_public_key("openssh").decode().strip(),
    }
    server.close()
    await server.wait_closed()


@pytest.mark.asyncio
async def test_first_test_returns_the_key_to_confirm(sftp_server):
    key, fp = await fetch_host_key("127.0.0.1", sftp_server["cfg"]["port"])
    result = await build_destination("sftp", sftp_server["cfg"], None).test()

    assert key == sftp_server["host_key"] and fp.startswith("SHA256:")
    assert result.needs_host_key_confirmation and result.host_key == key


@pytest.mark.asyncio
async def test_upload_list_delete_with_the_pinned_key(sftp_server, tmp_path):
    dest = build_destination("sftp", sftp_server["cfg"], sftp_server["host_key"])
    local = tmp_path / "irdoc_backup_20260101T000000Z.enc"
    local.write_bytes(b"encrypted bundle")

    assert (await dest.test()).ok
    await dest.upload(local, local.name)
    remote = sftp_server["root"] / "backups" / local.name
    assert remote.read_bytes() == b"encrypted bundle"
    assert not (sftp_server["root"] / "backups" / (local.name + ".part")).exists()
    assert local.name in await dest.list_backups()

    await dest.delete(local.name)
    assert not remote.exists()


@pytest.mark.asyncio
async def test_a_changed_host_key_is_refused(sftp_server):
    other = asyncssh.generate_private_key("ssh-ed25519").export_public_key("openssh").decode().strip()
    dest = build_destination("sftp", sftp_server["cfg"], other)

    with pytest.raises(RemoteBackupError, match="does not match the pinned key"):
        await dest.list_backups()
    assert not (await dest.test()).ok


@pytest.mark.asyncio
async def test_wrong_password_is_reported(sftp_server):
    dest = build_destination("sftp", {**sftp_server["cfg"], "password": "nope"}, sftp_server["host_key"])
    result = await dest.test()
    assert not result.ok and "failed" in result.error
