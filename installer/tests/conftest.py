import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from installer.wizard import app

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def _no_wizard_exit(monkeypatch):
    """/success and /upgrade/success SIGTERM the wizard 2s later. In a test run
    that killed pytest itself once the suite outlasted the 2s."""
    import installer.wizard as wiz
    monkeypatch.setattr(wiz, "_schedule_exit", lambda: None)
