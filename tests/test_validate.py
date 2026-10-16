import shutil

import pytest

from dora_reporting import validate
from dora_reporting.validate import ChecksumError, validate_report, verify_checksums

FI_SHA256 = {
    "fi/v1/dora_initial_mapping.json": "ab21556bae872c9d786d66ffd60238aa384110d76bbbf4cdd29be4cfa3070539",
    "fi/v1/dora_initial_schema.json": "921e1f8f6805c7a31051dc68bcfe55f4cadda073339bef7b6635db1e6657cbc0",
    "fi/v2/dora_initial_mapping.json": "3f31b338cd8cc6d82c9d6d0d9b39ac145dcbbaca1eb6429e5b526ad9b813aaed",
    "fi/v2/dora_initial_schema.json": "6a8f46567e85c1a02506392f4b46f3a959554e514fb634e37167004a1dfd5db8",
}


@pytest.fixture
def tampered_schemas(tmp_path, monkeypatch):
    copy = tmp_path / "schemas"
    shutil.copytree(validate.SCHEMA_DIR, copy)
    schema = copy / "fi" / "v2" / "dora_initial_schema.json"
    schema.write_bytes(schema.read_bytes().replace(b"DORA_Initial_v2.0", b"DORA_Initial_v2.1"))
    monkeypatch.setattr(validate, "SCHEMA_DIR", copy)
    return copy


@pytest.mark.fi_source("Change process: FI schema files stored unchanged with SHA-256")
def test_checksums_match_sha256sums():
    assert verify_checksums() == FI_SHA256


@pytest.mark.fi_source("Change process: FI schema files stored unchanged with SHA-256")
def test_checksum_mismatch_is_detected(tampered_schemas):
    with pytest.raises(ChecksumError, match="fi/v2/dora_initial_schema.json"):
        verify_checksums()
    with pytest.raises(ChecksumError):
        validate_report({}, "v2")


@pytest.mark.fi_source("v1 schema: detectionDateTime format date-time")
def test_invalid_calendar_date_is_rejected():
    issues = validate_report({"data": {"detectionDateTime": "2026-99-99T06:00:00.0Z"}}, "v1")
    found = [i for i in issues if i.field == "detectionDateTime"]
    assert [(i.path, i.rule, i.value) for i in found] == [
        ("data.detectionDateTime", "format", "2026-99-99T06:00:00.0Z")
    ]


def test_additional_properties_are_split_per_field():
    issues = validate_report({"data": {"foo": "x", "bar": "y"}}, "v1")
    extra = sorted((i.path, i.field) for i in issues if i.rule == "additionalProperties")
    assert extra == [("data.bar", "bar"), ("data.foo", "foo")]


def test_missing_required_field_is_reported_by_name():
    issues = validate_report({"data": {}}, "v1")
    missing = {i.field for i in issues if i.rule == "required"}
    assert {"schemaRef", "reportingDate", "financialEntityCode"} <= missing
