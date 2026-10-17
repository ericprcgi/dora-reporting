"""Where incident snapshots come from: ServiceNow, or a saved fixture."""
import json
from pathlib import Path

from dora_reporting import reference_data
from dora_reporting.incident_block import IncidentBlockError, parse_description
from dora_reporting.servicenow_client import ServiceNowClient

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
SOURCES = ("fixture", "servicenow")


class SourceError(Exception):
    """The snapshot could not be loaded."""


def build_snapshot(raw: dict) -> dict:
    """Combine the ServiceNow incident and its affected services with the reference data."""
    incident = raw["incident"]
    try:
        narrative, dora = parse_description(incident.get("description"))
    except IncidentBlockError as exc:
        raise SourceError(f"{incident['number']}: {exc}") from exc
    return {
        "incident": {key: incident.get(key, "") for key in ("number", "short_description", "state")}
        | {"description": narrative},
        "dora": dora,
        "legal_entities": reference_data.legal_entities(),
        "affected_services": sorted(service["name"] for service in raw["affected_services"]),
        "reporting_officer": reference_data.reporting_officer(),
    }


def load_snapshot(incident: str, source: str) -> dict:
    if source == "servicenow":
        return ServiceNowClient.from_env().fetch_snapshot(incident)
    if source == "fixture":
        path = FIXTURE_DIR / f"{incident}.json"
        if not path.is_file():
            raise SourceError(f"no fixture for {incident} in tests/fixtures")
        return json.loads(path.read_text(encoding="utf-8"))
    raise SourceError(f"unknown source: {source}")
