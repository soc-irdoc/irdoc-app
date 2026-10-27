import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import pytest

from installer.core.snapshot import list_snapshots


def test_list_snapshots_empty_when_no_backups(tmp_path):
    assert list_snapshots(tmp_path) == []


def test_list_snapshots_returns_sorted_by_timestamp(tmp_path):
    for name in ["pre-upgrade-2026-01-10-120000", "pre-upgrade-2026-01-11-090000"]:
        d = tmp_path / name
        d.mkdir()
        (d / "snapshot.json").write_text(json.dumps({
            "version_from": "1.0.0", "version_to": "1.1.0",
            "timestamp": f"2026-01-{name[-12:-6].replace('-', '')}T00:00:00Z",
            "files": [],
        }))
    result = list_snapshots(tmp_path)
    assert len(result) == 2
    assert result[0]["version_from"] == "1.0.0"


@pytest.mark.asyncio
async def test_snapshot_saves_and_restores_nginx_conf(tmp_path, monkeypatch):
    """#57: an upgrade may switch nginx.conf to the image's headers snippet,
    which an older image doesn't have, so a rollback must restore it too."""
    import installer.core.snapshot as snapshot

    repo = tmp_path / "repo"
    (repo / "docker" / "nginx").mkdir(parents=True)
    conf = repo / "docker" / "nginx" / "nginx.conf"
    conf.write_text("original")
    monkeypatch.setattr(snapshot, "_REPO_ROOT", repo)

    pg_dump = MagicMock(returncode=0)
    pg_dump.communicate = AsyncMock(return_value=(b"-- dump", b""))
    with patch.object(snapshot.asyncio, "create_subprocess_exec", AsyncMock(return_value=pg_dump)):
        snap = await snapshot.take_snapshot(tmp_path / "snap", "1.0.0", "1.1.0")

    assert (snap / "nginx.conf.bak").read_text() == "original"
    assert "nginx.conf.bak" in json.loads((snap / "snapshot.json").read_text())["files"]

    conf.write_text("patched")
    (snap / "dump.sql").unlink()  # skip the database part of the restore
    await snapshot.restore_snapshot(snap)
    assert conf.read_text() == "original"


@pytest.mark.asyncio
async def test_snapshot_saves_and_restores_local_nginx_conf(tmp_path, monkeypatch):
    """#114: the live config is nginx/local/nginx.conf; a rollback restores it."""
    import installer.core.snapshot as snapshot

    repo = tmp_path / "repo"
    (repo / "docker" / "nginx" / "local").mkdir(parents=True)
    local = repo / "docker" / "nginx" / "local" / "nginx.conf"
    local.write_text("original")
    monkeypatch.setattr(snapshot, "_REPO_ROOT", repo)

    pg_dump = MagicMock(returncode=0)
    pg_dump.communicate = AsyncMock(return_value=(b"-- dump", b""))
    with patch.object(snapshot.asyncio, "create_subprocess_exec", AsyncMock(return_value=pg_dump)):
        snap = await snapshot.take_snapshot(tmp_path / "snap", "1.0.0", "1.1.0")

    assert "nginx.local.conf.bak" in json.loads((snap / "snapshot.json").read_text())["files"]
    local.write_text("patched")
    (snap / "dump.sql").unlink()
    await snapshot.restore_snapshot(snap)
    assert local.read_text() == "original"


@pytest.mark.asyncio
async def test_rollback_drops_local_conf_the_upgrade_created(tmp_path, monkeypatch):
    """An upgrade that moved an edited tracked nginx.conf into local/ is undone:
    the tracked file comes back and the local copy goes."""
    import installer.core.snapshot as snapshot

    repo = tmp_path / "repo"
    nginx = repo / "docker" / "nginx"
    nginx.mkdir(parents=True)
    (nginx / "nginx.conf").write_text("edited")
    monkeypatch.setattr(snapshot, "_REPO_ROOT", repo)

    pg_dump = MagicMock(returncode=0)
    pg_dump.communicate = AsyncMock(return_value=(b"-- dump", b""))
    with patch.object(snapshot.asyncio, "create_subprocess_exec", AsyncMock(return_value=pg_dump)):
        snap = await snapshot.take_snapshot(tmp_path / "snap", "1.0.0", "1.1.0")

    (nginx / "local").mkdir()
    (nginx / "local" / "nginx.conf").write_text("edited")
    (nginx / "nginx.conf").write_text("shipped")
    (snap / "dump.sql").unlink()
    await snapshot.restore_snapshot(snap)
    assert (nginx / "nginx.conf").read_text() == "edited"
    assert not (nginx / "local" / "nginx.conf").exists()
