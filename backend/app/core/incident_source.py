"""What triggered the investigation (#147).

Required when an incident is created and, for incidents created before
0.1.10, when it is closed. Older incidents have none (NULL), shown as
"Not recorded" until someone sets it.
"""
from typing import Literal

INCIDENT_SOURCES = (
    "user_reported",
    "siem_alert",
    "edr_xdr_alert",
    "threat_hunting",
    "threat_intel",
    "network_alert",
    "email_security",
    "cloud_alert",
    "external_notification",
    "other",
)

INCIDENT_SOURCE_LABELS = {
    "user_reported": "User Reported / Requested",
    "siem_alert": "SIEM Alert",
    "edr_xdr_alert": "EDR / XDR Alert",
    "threat_hunting": "Threat Hunting (IOC / IOA)",
    "threat_intel": "Threat Intelligence",
    "network_alert": "Network Security Alert (IDS/IPS, NDR, Firewall)",
    "email_security": "Email Security / Phishing Report",
    "cloud_alert": "Cloud Security Alert",
    "external_notification": "External Notification",
    "other": "Other",
}

IncidentSource = Literal[
    "user_reported",
    "siem_alert",
    "edr_xdr_alert",
    "threat_hunting",
    "threat_intel",
    "network_alert",
    "email_security",
    "cloud_alert",
    "external_notification",
    "other",
]

# Webhook-created incidents come from automated tooling.
DEFAULT_EXTERNAL_SOURCE: IncidentSource = "siem_alert"
