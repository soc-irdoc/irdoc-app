"""
Plugin registry. Import this package to load all integration plugins.
"""
# Auto-import all integration plugins so they self-register via @register_plugin
from app.plugins.integrations import (  # noqa: F401
    abuseipdb,
    azuread,
    crowdstrike,
    proofpoint,
    sentinel,
    sharepoint,
    shodan,
    slack,
    teams,
    virustotal,
)
from app.plugins.registry import PLUGINS, register_plugin  # noqa: F401
