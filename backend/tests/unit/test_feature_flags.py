"""Unit tests for app.core.feature_flags.

Regression coverage: with an empty LICENSE_KEY (the default core install),
every feature that has actual enforced code behind it must be unlocked.
Only features with no implementation yet may stay gated.
"""
from app.core import feature_flags
from app.core.feature_flags import FEATURE_MAP, check_feature

# Features with real, shipped code paths that must never be blocked
# on a core (no license key) install.
IMPLEMENTED_FEATURES = [
    "timeline",
    "iocs",
    "evidence",
    "tasks",
    "basic_reports",
    "inbound_webhook",
    "local_storage",
    "rest_api",
    "report_template_builder",
    "report_pdf_export",
    "report_docx_export",
    "ai_summaries",
    "sharepoint_sync",
    "cloud_storage",
    "advanced_integrations",
    "integration_siem",
    "integration_edr",
    "integration_iam",
    "sso_oidc",
    "audit_log",
]

# Declared for a future premium tier but not wired into any code path yet.
NOT_YET_IMPLEMENTED = {"multi_tenancy", "custom_branding", "mssp_mode", "rbac_advanced"}


def test_all_feature_map_keys_are_covered_by_the_test():
    assert set(FEATURE_MAP) == set(IMPLEMENTED_FEATURES) | NOT_YET_IMPLEMENTED


def test_implemented_features_are_unlocked_with_empty_license_key(monkeypatch):
    monkeypatch.setattr(feature_flags.settings, "LICENSE_KEY", "")
    for feature in IMPLEMENTED_FEATURES:
        assert check_feature(feature) is True, f"{feature} is blocked on a core install"


def test_unimplemented_features_stay_gated_with_empty_license_key(monkeypatch):
    monkeypatch.setattr(feature_flags.settings, "LICENSE_KEY", "")
    for feature in NOT_YET_IMPLEMENTED:
        assert check_feature(feature) is False


def test_unknown_feature_defaults_to_locked(monkeypatch):
    monkeypatch.setattr(feature_flags.settings, "LICENSE_KEY", "")
    assert check_feature("some_future_feature_nobody_registered") is False
