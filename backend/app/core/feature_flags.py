"""
Feature flag system.

Core (AGPL) features are always enabled.
Premium features require a valid commercial license key.

The LICENSE_KEY env var is checked at startup. In Phase 5, keys will be
validated against a licensing server. For now, a non-empty key enables pro.
"""
from app.core.config import settings

# Feature groups and their required plan
FEATURE_MAP: dict[str, str] = {
    # Core (AGPL) — always enabled
    "timeline": "core",
    "iocs": "core",
    "evidence": "core",
    "tasks": "core",
    "basic_reports": "core",   # Markdown + HTML export
    "inbound_webhook": "core",
    "local_storage": "core",
    "rest_api": "core",

    # Everything shipped so far is core — nothing currently written is
    # premium. These stay mapped to "core" until a feature that actually
    # requires a commercial license ships.
    "report_template_builder": "core",
    "report_pdf_export": "core",
    "report_docx_export": "core",
    "ai_summaries": "core",  # Ollama is local/free — no license gate
    "sharepoint_sync": "core",
    "cloud_storage": "core",          # S3 / Azure / GCS backends
    "advanced_integrations": "core",  # VT, AbuseIPDB, Sentinel, CrowdStrike
    "integration_siem": "core",       # Sentinel
    "integration_edr": "core",        # CrowdStrike
    "integration_iam": "core",        # Azure AD
    "sso_oidc": "core",
    "audit_log": "core",

    # Not yet implemented — safe to leave gated since no code path uses them.
    "multi_tenancy": "enterprise",
    "custom_branding": "enterprise",
    "mssp_mode": "enterprise",
    "rbac_advanced": "enterprise",
}

PLAN_HIERARCHY = {"core": 0, "pro": 1, "enterprise": 2}


def _get_active_plan() -> str:
    """Derive plan from LICENSE_KEY. Phase 5 will validate against a server."""
    if not settings.LICENSE_KEY:
        return "core"
    # Simple heuristic for now: non-empty key = pro
    # TODO Phase 5: validate key, extract plan from signed payload
    if settings.LICENSE_KEY.startswith("ent_"):
        return "enterprise"
    return "pro"


def check_feature(feature: str) -> bool:
    """Return True if feature is enabled for the current license."""
    required_plan = FEATURE_MAP.get(feature, "enterprise")
    active_plan = _get_active_plan()
    return PLAN_HIERARCHY.get(active_plan, 0) >= PLAN_HIERARCHY.get(required_plan, 99)


def get_all_flags() -> dict[str, bool]:
    """Return the full feature flag map for the current org/license."""
    return {feature: check_feature(feature) for feature in FEATURE_MAP}
