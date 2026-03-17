"""
IntegrationPlugin Protocol — all plugins conform to this interface.
Plugins implement only the methods they support.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class IntegrationPlugin(Protocol):
    name: str
    display_name: str
    category: str          # siem | edr | iam | email | ticketing | comms | ti | storage_sync
    is_premium: bool
    config_schema: dict    # JSON schema — frontend renders this as a dynamic form

    async def test_connection(self, config: dict) -> bool:
        """Verify credentials are valid. Return True on success."""
        ...

    async def enrich_ioc(self, ioc: object, config: dict) -> dict:
        """Return enrichment dict for an IOC. Return {} if not applicable."""
        ...

    async def pull_alerts(self, incident_id: str, config: dict) -> list[dict]:
        """Pull alerts/detections. Return list of timeline entry candidates."""
        ...

    async def push_report(self, report_bytes: bytes, filename: str, config: dict) -> str:
        """Upload a rendered report. Return the destination URL."""
        ...

    async def send_notification(self, event: str, payload: dict, config: dict) -> bool:
        """Send a notification event. Return True on success."""
        ...
