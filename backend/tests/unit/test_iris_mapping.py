"""Value mappings for the IRIS importer (app/cli/iris_import/mapping.py)."""
from pathlib import Path

import pytest

from app.cli.iris_import import mapping as mapping_module
from app.cli.iris_import.mapping import DEFAULT_MAPPING, MappingError, load_mapping


def test_default_mapping_is_valid_and_covers_every_section():
    mapping = load_mapping()
    assert set(DEFAULT_MAPPING) == {
        "severity", "disposition", "source", "timeline_entry_type", "asset_type", "asset_status", "ioc_type", "tlp",
    }
    assert mapping.get("severity", "High") == "high"


def test_keys_are_normalised():
    mapping = load_mapping()
    # /manage/cases/filter gives snake_case, the case details page gives Title Case.
    assert mapping.get("disposition", "true_positive_with_impact") == "tp_remediated"
    assert mapping.get("disposition", "True Positive With Impact") == "tp_remediated"
    assert mapping.get("asset_type", "Windows  -  Computer") == "workstation"
    assert mapping.get("asset_status", 1) == "confirmed"


def test_unmapped_values_use_the_default_and_are_recorded():
    mapping = load_mapping()
    assert mapping.get("asset_type", "Toaster") == "other"
    assert mapping.get("severity", None) == "low"
    assert ("asset_type", "Toaster") in mapping.unmapped
    assert ("severity", "(empty)") in mapping.unmapped


def test_unmapped_ioc_type_has_no_default():
    mapping = load_mapping()
    assert mapping.get("ioc_type", "mutex") is None
    assert ("ioc_type", "mutex") in mapping.unmapped


def test_tlp_values_irdoc_lacks_are_mapped():
    mapping = load_mapping()
    assert mapping.get("tlp", "amber+strict") == "amber"
    assert mapping.get("tlp", "clear") == "white"


def test_yaml_overrides_merge_over_defaults(tmp_path):
    f = tmp_path / "m.yaml"
    f.write_text(
        "source:\n  fraud:phishing: email_security\n  _default: siem_alert\n"
        "ioc_type:\n  mutex: file\n  md5: null\n",
        encoding="utf-8",
    )
    mapping = load_mapping(f)
    assert mapping.get("source", "fraud:phishing") == "email_security"
    assert mapping.get("source", "other:other") == "siem_alert"
    assert mapping.get("ioc_type", "mutex") == "file"
    assert mapping.get("ioc_type", "md5") is None  # sent to the notes on purpose
    assert mapping.get("ioc_type", "sha256") == "hash"  # defaults kept


def test_shipped_example_mapping_is_valid():
    example = Path(mapping_module.__file__).with_name("mapping.example.yaml")
    mapping = load_mapping(example)
    assert mapping.get("source", "fraud:phishing") == "email_security"


@pytest.mark.parametrize("content, message", [
    ("severity:\n  High: urgent\n", "not an IRDoc value"),
    ("colour:\n  red: blue\n", "unknown mapping section"),
    ("severity: high\n", "must be a mapping"),
    ("- a\n- b\n", "must contain a YAML mapping"),
    ("ioc_type:\n  _default: null\n", "not an IRDoc value"),
    ("severity: [\n", "cannot read"),
])
def test_invalid_mapping_files_are_rejected(tmp_path, content, message):
    f = tmp_path / "m.yaml"
    f.write_text(content, encoding="utf-8")
    with pytest.raises(MappingError, match=message):
        load_mapping(f)
