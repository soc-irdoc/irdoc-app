import pytest

@pytest.mark.asyncio
async def test_root_redirects_to_prerequisites(client):
    resp = await client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "/prerequisites" in resp.headers["location"]
