import json

from tools import write_summary
from tools.write_summary import group_of, main, validation_table

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="3">
<testcase classname="tests.test_x" name="test_a">
  <properties><property name="fi_source" value="v2 schema: detectionDateTime pattern"/></properties>
</testcase>
<testcase classname="tests.test_x" name="test_b">
  <properties><property name="fi_source" value="FI guidance: field 2.1 not empty"/></properties>
  <failure message="boom"/>
</testcase>
<testcase classname="tests.test_y" name="test_c"/>
</testsuite></testsuites>
"""


def test_group_of_known_and_unknown_fields():
    assert group_of("affectedEntity-LEI") == "Affected entities (1.4–1.6)"
    assert group_of("classificationDateTime") == "Date and time (2.2–2.3)"
    assert group_of("secondaryContact-phone") == "Phone numbers (1.9, 1.12)"
    assert group_of("reportCurrency") == "reportCurrency"


def test_tests_table_reads_fi_source_properties(tmp_path):
    junit = tmp_path / "junit.xml"
    junit.write_text(JUNIT, encoding="utf-8")
    table = write_summary.tests_table(junit)
    assert "| detectionDateTime pattern | v2 schema | test_x::test_a | ✅ passed |" in table
    assert "| field 2.1 not empty | FI guidance | test_x::test_b | ❌ failed |" in table
    assert "test_y::test_c" not in table
    assert "3 tests: 2 passed, 1 failed (1 without an FI source not listed)" in table


def test_validation_table_counts_groups(tmp_path):
    result = tmp_path / "validation-v2.json"
    result.write_text(json.dumps({
        "incident": "INC0010007", "schema_version": "v2",
        "schema_file": "schemas/fi/v2/dora_initial_schema.json", "sha256": "6a8f46567e85c1a0",
        "valid": False,
        "issues": [
            {"path": "data.detectionDateTime", "field": "detectionDateTime", "rule": "pattern",
             "message": "does not match 'a|b'", "value": "2026-03-12T08:10:00.0Z"},
            {"path": "data.classificationDateTime", "field": "classificationDateTime",
             "rule": "pattern", "message": "x", "value": "2026-03-12T11:00:00.0Z"},
            {"path": "data.foo", "field": "foo", "rule": "required", "message": "y", "value": None},
        ],
    }), encoding="utf-8")
    text = validation_table(result)
    assert "validate (v2): ❌ failed – 3 errors in 2 groups" in text
    assert "| Date and time (2.2–2.3) | detectionDateTime, classificationDateTime | pattern |" in text
    assert "does not match 'a\\|b'" in text
    assert "schemas/fi/v2/dora_initial_schema.json" in text


def test_passed_validation_has_no_error_table(tmp_path):
    result = tmp_path / "validation-v1.json"
    result.write_text(json.dumps({
        "incident": "INC0010007", "schema_version": "v1", "schema_file": "s", "sha256": "h",
        "valid": True, "issues": [],
    }), encoding="utf-8")
    text = validation_table(result)
    assert "validate (v1): ✅ passed" in text
    assert "| Group |" not in text


def test_missing_file_is_reported(tmp_path, capsys):
    assert main(["tests", str(tmp_path / "missing.xml")]) == 0
    assert "No test results" in capsys.readouterr().out
