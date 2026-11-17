"""Value mappings from DFIR IRIS to IRDoc, with YAML overrides.

Each section maps an IRIS value to an IRDoc value. Keys are compared after
normalisation (lower case, "_" read as a space, runs of spaces collapsed), so
"True Positive With Impact", "true_positive_with_impact" and
"true positive with impact" are the same key.

The special key "_default" is used for values a section doesn't list. Values
that fall back to it are collected in `Mapping.unmapped` and printed in the
run summary, so the mapping file can be completed and the import re-run.

`ioc_type` has no default: an IOC whose type isn't mapped can't be stored as an
IRDoc IOC. Those are listed in the incident's notes instead (see transform.py).
Map a type to `null` in the YAML file to send it there on purpose.
"""
import re
from pathlib import Path
from typing import get_args

import yaml

from app.core.disposition import DISPOSITIONS
from app.core.incident_source import INCIDENT_SOURCES
from app.core.severity import SEVERITIES
from app.schemas.asset import ASSET_STATUSES, ASSET_TYPES

IOC_TYPES = ("email", "domain", "ip", "url", "hash", "file", "username")
TLP_LEVELS = ("red", "amber", "green", "white")
TIMELINE_ENTRY_TYPES = ("detection", "analysis", "containment", "evidence", "comms", "note")

DEFAULT = "_default"

# Allowed IRDoc values per section. The API enforces these with pydantic; a
# direct ORM insert doesn't, so the mapping is validated against them instead.
ALLOWED: dict[str, tuple[str, ...]] = {
    "severity": SEVERITIES,
    "disposition": DISPOSITIONS,
    "source": INCIDENT_SOURCES,
    "timeline_entry_type": TIMELINE_ENTRY_TYPES,
    "asset_type": get_args(ASSET_TYPES),
    "asset_status": get_args(ASSET_STATUSES),
    "ioc_type": IOC_TYPES,
    "tlp": TLP_LEVELS,
}

_HASHES = (
    "md5", "sha1", "sha224", "sha256", "sha384", "sha512", "sha512/224", "sha512/256",
    "sha3-224", "sha3-256", "sha3-384", "sha3-512", "ssdeep", "imphash", "impfuzzy", "tlsh",
    "authentihash", "pehash", "vhash", "telfhash", "cdhash",
)

DEFAULT_MAPPING: dict[str, dict[str, str | None]] = {
    # IRIS severity name -> IRDoc severity
    "severity": {
        "critical": "critical", "high": "high", "medium": "medium", "low": "low",
        "informational": "low", "unspecified": "low", DEFAULT: "low",
    },
    # IRIS outcome (case status_name) -> IRDoc disposition
    "disposition": {
        "true positive with impact": "tp_remediated",
        "true positive without impact": "tp_remediated",
        "false positive": "fp_benign",
        "legitimate": "fp_benign",
        "not applicable": "inconclusive",
        "unknown": "inconclusive",
        DEFAULT: "inconclusive",
    },
    # IRIS classification name -> IRDoc source (what triggered the investigation).
    # IRIS classifications describe the incident type, not how it was detected,
    # so only the fallback is set; fill this in to suit your SOC.
    "source": {DEFAULT: "other"},
    # IRIS timeline event category -> IRDoc timeline entry type. All IRIS
    # built-in categories are listed so only custom ones show up as unmapped.
    "timeline_entry_type": {
        "initial access": "detection",
        "remediation": "containment",
        **{c: "analysis" for c in (
            "unspecified", "legitimate", "execution", "persistence", "privilege escalation",
            "defense evasion", "credential access", "discovery", "lateral movement", "collection",
            "command and control", "exfiltration", "impact",
        )},
        DEFAULT: "analysis",
    },
    # IRIS asset type name -> IRDoc asset type
    "asset_type": {
        "account": "account",
        "linux account": "account",
        "windows account - local": "account",
        "windows account - local - admin": "account",
        "windows account - ad": "account",
        "windows account - ad - admin": "account",
        "windows account - ad - krbtgt": "service_account",
        "windows account - ad - service": "service_account",
        "firewall": "network_device",
        "router": "network_device",
        "switch": "network_device",
        "vpn": "network_device",
        "waf": "network_device",
        "linux - server": "server",
        "windows - server": "server",
        "windows - dc": "server",
        "linux - computer": "workstation",
        "windows - computer": "workstation",
        "mac - computer": "workstation",
        "phone - android": "mobile",
        "phone - ios": "mobile",
        DEFAULT: "other",
    },
    # IRIS asset compromise status id -> IRDoc asset status
    "asset_status": {
        "0": "suspected",   # To be determined
        "1": "confirmed",   # Compromised
        "2": "cleared",     # Not compromised
        "3": "suspected",   # Unknown
        DEFAULT: "suspected",
    },
    # IRIS IOC type -> IRDoc IOC type (no default; unmapped types go to the notes)
    "ioc_type": {
        **{h: "hash" for h in _HASHES},
        "ip-src": "ip", "ip-dst": "ip", "ip-any": "ip", "ip-src|port": "ip", "ip-dst|port": "ip",
        "domain": "domain", "hostname": "domain", "domain|ip": "domain", "hostname|port": "domain",
        "url": "url", "uri": "url", "link": "url",
        "email": "email", "email-src": "email", "email-dst": "email", "email-reply-to": "email",
        "target-email": "email", "dns-soa-email": "email", "whois-registrant-email": "email",
        "filename": "file", "file-path": "file", "filename-pattern": "file", "attachment": "file",
        "malware-sample": "file", "email-attachment": "file",
        **{f"filename|{h}": "file" for h in _HASHES},
        "account": "username", "target-user": "username", "github-username": "username",
    },
    # IRIS TLP name -> IRDoc TLP level
    "tlp": {
        "red": "red", "amber": "amber", "amber+strict": "amber", "green": "green",
        "clear": "white", "white": "white", DEFAULT: "amber",
    },
}


class MappingError(ValueError):
    """The mapping file is unreadable or maps to a value IRDoc doesn't accept."""


def normalize_key(value: object) -> str:
    return re.sub(r"[\s_]+", " ", str(value).strip().lower())


class Mapping:
    def __init__(self, sections: dict[str, dict[str, str | None]]):
        self._sections = {
            name: {(k if k == DEFAULT else normalize_key(k)): v for k, v in entries.items()}
            for name, entries in sections.items()
        }
        # (section, IRIS value) pairs that fell back to the default, or had no mapping.
        self.unmapped: set[tuple[str, str]] = set()

    def get(self, section: str, raw: object) -> str | None:
        """The IRDoc value for an IRIS value. None only for unmapped IOC types."""
        entries = self._sections[section]
        key = normalize_key(raw) if raw not in (None, "") else ""
        if key in entries:
            return entries[key]
        self.unmapped.add((section, str(raw) if raw not in (None, "") else "(empty)"))
        return entries.get(DEFAULT)


def _validate(sections: dict[str, dict[str, str | None]]) -> None:
    for name, entries in sections.items():
        allowed = ALLOWED[name]
        for key, value in entries.items():
            if value is None and name == "ioc_type" and key != DEFAULT:
                continue
            if value not in allowed:
                raise MappingError(
                    f"mapping '{name}': '{key}' -> '{value}' is not an IRDoc value "
                    f"(allowed: {', '.join(allowed)})"
                )


def load_mapping(path: Path | None = None) -> Mapping:
    """The default mapping, with the sections in the YAML file at `path` merged over it."""
    sections = {name: dict(entries) for name, entries in DEFAULT_MAPPING.items()}
    if path is not None:
        try:
            override = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise MappingError(f"cannot read mapping file {path}: {exc}") from exc
        if not isinstance(override, dict):
            raise MappingError(f"mapping file {path} must contain a YAML mapping of sections")
        for name, entries in override.items():
            if name not in sections:
                raise MappingError(f"unknown mapping section '{name}' (known: {', '.join(sections)})")
            if not isinstance(entries, dict):
                raise MappingError(f"mapping section '{name}' must be a mapping of IRIS value -> IRDoc value")
            for key, value in entries.items():
                sections[name][str(key)] = value
    _validate(sections)
    return Mapping(sections)
