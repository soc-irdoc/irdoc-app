import pytest
import httpx
from unittest.mock import AsyncMock, patch

from installer.core.health import wait_for_health


@pytest.mark.asyncio
async def test_wait_for_health_returns_true_on_200():
    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch("installer.core.health.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.get = AsyncMock(return_value=mock_response)
        MockClient.return_value = instance

        result = await wait_for_health("http://localhost:8000", timeout=5, interval=0)
    assert result is True


@pytest.mark.asyncio
async def test_wait_for_health_returns_false_on_timeout():
    with patch("installer.core.health.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        MockClient.return_value = instance

        result = await wait_for_health("http://localhost:8000", timeout=1, interval=0)
    assert result is False
