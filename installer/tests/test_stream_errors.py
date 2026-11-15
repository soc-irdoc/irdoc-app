"""A step that fails unexpectedly shows a short message in the browser; the
exception text and traceback only go to the wizard's terminal (CodeQL
py/stack-trace-exposure)."""
import logging
from unittest.mock import AsyncMock, patch

import pytest

import installer.wizard as wizard

SECRET_DETAIL = "/root/irdoc/docker/.env: DB_PASSWORD=hunter2"


@pytest.mark.asyncio
async def test_snapshot_failure_hides_the_exception_text(client, tmp_path, caplog):
    boom = AsyncMock(side_effect=PermissionError(SECRET_DETAIL))
    with patch.object(wizard, "take_snapshot", boom), \
         patch.object(wizard, "BACKUPS_DIR", tmp_path), \
         caplog.at_level(logging.ERROR, logger="irdoc.installer"):
        resp = await client.get("/upgrade/snapshot/stream")

    assert "__FAIL__Snapshot failed unexpectedly (PermissionError)" in resp.text
    assert "terminal running the wizard" in resp.text
    assert "hunter2" not in resp.text
    assert "Traceback" not in resp.text
    # The operator still gets the whole error where the wizard runs.
    assert any(SECRET_DETAIL in r.getMessage() or (r.exc_info and SECRET_DETAIL in str(r.exc_info[1]))
               for r in caplog.records)


def test_unexpected_failure_message_names_the_stage_and_type_only():
    msg = wizard._unexpected_failure("Rollback", RuntimeError("docker said: secret"))
    assert msg.startswith("Rollback failed unexpectedly (RuntimeError).")
    assert "secret" not in msg
