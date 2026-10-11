"""Incident severity levels.

Severities were stored as sev1-sev4 until migration 024 renamed them. The API
and the external webhook still accept the old values as input, so senders
written against older versions keep working.
"""
from typing import Annotated, Literal

from pydantic import BeforeValidator

SEVERITIES = ("critical", "high", "medium", "low")

LEGACY_SEVERITIES = {
    "sev1": "critical",
    "sev2": "high",
    "sev3": "medium",
    "sev4": "low",
}

SEVERITY_LABELS = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}


def normalize_severity(value):
    """Map a legacy sev1-sev4 value to its new name; pass anything else through."""
    if isinstance(value, str):
        value = value.strip().lower()
        return LEGACY_SEVERITIES.get(value, value)
    return value


Severity = Annotated[
    Literal["critical", "high", "medium", "low"],
    BeforeValidator(normalize_severity),
]
