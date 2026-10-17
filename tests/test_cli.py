import json

import pytest

from dora_reporting.cli import main


def generate(tmp_path, *extra, incident="INC0010007", source="fixture"):
    return main(["generate", "--incident", incident, "--source", source, "--out", str(tmp_path), *extra])


def test_generate_from_fixture_writes_report(tmp_path):
    assert generate(tmp_path) == 0
    report = json.loads((tmp_path / "INC0010007_initial.json").read_text(encoding="utf-8"))
    assert report["data"]["financialEntityCode"] == "INC0010007"
    assert not (tmp_path / "validation-v1.json").exists()


def test_generate_with_schema_writes_validation_result(tmp_path):
    exit_code = generate(tmp_path, "--schema", "v1")
    result = json.loads((tmp_path / "validation-v1.json").read_text(encoding="utf-8"))
    assert set(result) == {"incident", "schema_version", "schema_file", "sha256", "valid", "issues"}
    assert result["incident"] == "INC0010007"
    assert result["schema_file"] == "schemas/fi/v1/dora_initial_schema.json"
    assert result["sha256"] == "921e1f8f6805c7a31051dc68bcfe55f4cadda073339bef7b6635db1e6657cbc0"
    assert result["valid"] is (exit_code == 0)
    assert exit_code in (0, 1)


@pytest.mark.parametrize("incident", ["inc0010007", "INC0010007 ", "INC1", "INC0010007;ls"])
def test_malformed_incident_number_is_rejected(tmp_path, capsys, incident):
    assert generate(tmp_path, incident=incident) == 2
    assert "invalid incident number" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_missing_fixture_gives_clear_error(tmp_path, capsys):
    assert generate(tmp_path, incident="INC0000001") == 2
    err = capsys.readouterr().err
    assert "no fixture for INC0000001" in err
    assert "Traceback" not in err


def test_servicenow_without_credentials_gives_clear_error(tmp_path, capsys, monkeypatch):
    for name in ("SERVICENOW_INSTANCE", "SERVICENOW_USER", "SERVICENOW_PASSWORD"):
        monkeypatch.delenv(name, raising=False)
    assert generate(tmp_path, source="servicenow") == 2
    assert "missing environment variables" in capsys.readouterr().err


def test_checksums_command(capsys):
    assert main(["checksums"]) == 0
    assert "schemas/fi/v2/dora_initial_schema.json" in capsys.readouterr().out
