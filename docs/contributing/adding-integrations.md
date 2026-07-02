# Adding Integrations

IRDoc uses a plugin system — every integration is a single file. No changes to core code are needed.

---

## Plugin File

Create a new file in `backend/app/plugins/integrations/`:

```python
# backend/app/plugins/integrations/my_tool.py

from ..registry import register_plugin
from ..base import BasePlugin


@register_plugin
class MyToolPlugin(BasePlugin):
    name = "my_tool"                    # unique slug, used in the DB
    display_name = "My Tool"            # shown in the integrations UI
    category = "ti"                     # ti | siem | edr | iam | comms | storage_sync
    config_schema = {
        "api_key": {
            "type": "string",
            "label": "API Key",
            "secret": True,             # masked in UI, Fernet-encrypted in DB
        },
        "base_url": {
            "type": "string",
            "label": "Base URL",
            "placeholder": "https://api.mytool.com",
        },
        "region": {
            "type": "select",
            "label": "Region",
            "options": ["us", "eu", "ap"],
        },
    }

    async def test_connection(self, config: dict) -> bool:
        """Called when admin clicks 'Test Connection'."""
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{config['base_url']}/ping",
                headers={"X-API-Key": config["api_key"]},
                timeout=5,
            )
        return r.status_code == 200

    async def enrich(self, ioc_value: str, ioc_type: str, config: dict) -> dict:
        """
        IOC enrichment (for category='ti' plugins).
        Return a dict that is stored under config['plugin_name'] key in ioc.enrichment JSONB.
        Return {} if this IOC type is not supported.
        """
        if ioc_type not in ("ip", "domain"):
            return {}

        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{config['base_url']}/lookup/{ioc_value}",
                headers={"X-API-Key": config["api_key"]},
                timeout=10,
            )
        if r.status_code != 200:
            return {}
        return r.json()
```

That's it. Restart the backend and your plugin appears in the Integrations admin panel.

---

## Plugin Categories

| Category | Purpose | Key method |
|---|---|---|
| `ti` | Threat intelligence / IOC enrichment | `enrich(ioc_value, ioc_type, config)` |
| `siem` | Query alerts / detections | `query_alerts(incident, config)` |
| `edr` | Endpoint actions | `contain_host(hostname, config)` |
| `iam` | Identity / directory | `get_user(email, config)` |
| `comms` | Notifications | `send_message(text, config)` |
| `storage_sync` | Report delivery | `sync(report_bytes, filename, config)` |

Only implement the methods relevant to your category. The base class provides no-op defaults.

---

## Config Schema Field Types

| Type | UI Control |
|---|---|
| `string` | Text input |
| `secret` | Password input (masked, Fernet-encrypted in DB) |
| `select` | Dropdown (requires `options` list) |
| `boolean` | Toggle switch |
| `number` | Number input |

---

## The `@register_plugin` decorator

The decorator adds the class to the global plugin registry (`app/plugins/registry.py`). The registry is imported once at startup. Plugins are instantiated on-demand — no singleton state.

---

## Credentials

Plugin config values marked `secret: True` in the `config_schema` are Fernet-encrypted before being stored in `org_integrations.config`. They are decrypted transparently by `integration_service` before being passed to plugin methods.

**Never log config values.** Never return them in API responses (the API always redacts `secret` fields).

---

## Testing your plugin

```python
# tests/unit/test_my_tool_plugin.py
import pytest
from unittest.mock import AsyncMock, patch
from app.plugins.integrations.my_tool import MyToolPlugin


@pytest.mark.asyncio
async def test_enrich_ip():
    plugin = MyToolPlugin()
    with patch("httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=AsyncMock(status_code=200, json=lambda: {"score": 90})
        )
        result = await plugin.enrich("1.2.3.4", "ip", {"api_key": "test", "base_url": "https://api.example.com"})
    assert result["score"] == 90
```
