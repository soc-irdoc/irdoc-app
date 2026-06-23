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
