"""Recorded DFIR IRIS v2.4.27 API responses (synthetic test cases).

iris_2_4_27.json maps "<path>?cid=<case>" (or "/manage/cases/filter?page=<n>")
to the JSON body IRIS returned. Recorded from a local IRIS v2.4.27 seeded
with test data:
- case 2: closed, SOC ID 482913, notes in nested directories, 4 events,
  3 assets, 6 IOCs (one with an unmapped type)
- case 3: closed, SOC ID 482950
- case 4: closed, empty SOC ID
- cases 1 and 5: open
"""
import json
from pathlib import Path

import httpx

FIXTURE = Path(__file__).with_name("iris_2_4_27.json")


def load() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def key_for(request: httpx.Request) -> str:
    path = request.url.path
    if path == "/manage/cases/filter":
        return f"{path}?page={request.url.params.get('page')}"
    cid = request.url.params.get("cid")
    return f"{path}?cid={cid}" if cid else path


def transport(responses: dict | None = None, fail: set[str] | None = None,
              seen: list[str] | None = None) -> httpx.MockTransport:
    """Replay the recorded responses. Paths in `fail` return HTTP 500; requested keys go to `seen`."""
    responses = responses if responses is not None else load()

    def handler(request: httpx.Request) -> httpx.Response:
        key = key_for(request)
        if seen is not None:
            seen.append(key)
        if fail and key in fail:
            return httpx.Response(500, json={"status": "error", "message": "boom", "data": None})
        if key not in responses:
            return httpx.Response(404, json={"status": "error", "message": f"no fixture for {key}", "data": None})
        return httpx.Response(200, json=responses[key])

    return httpx.MockTransport(handler)
