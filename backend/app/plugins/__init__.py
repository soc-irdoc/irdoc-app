"""
Plugin registry. Import this package to load all integration plugins.
"""
from app.plugins.registry import PLUGINS, register_plugin  # noqa: F401

# Auto-import all integration plugins so they self-register via @register_plugin
from app.plugins.integrations import (  # noqa: F401
    virustotal,
    abuseipdb,
    shodan,
    sentinel,
    crowdstrike,
    azuread,
    slack,
    teams,
    sharepoint,
    proofpoint,
)
