"""Where incident snapshots come from: ServiceNow, or a saved fixture."""
import json
from pathlib import Path

from dora_reporting.servicenow_client import ServiceNowClient

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
SOURCES = ("fixture", "servicenow")


class SourceError(Exception):
    """The snapshot could not be loaded."""


def load_snapshot(incident: str, source: str) -> dict:
    if source == "servicenow":
        return ServiceNowClient.from_env().fetch_snapshot(incident)
    if source == "fixture":
        path = FIXTURE_DIR / f"{incident}.json"
        if not path.is_file():
            raise SourceError(f"no fixture for {incident} in tests/fixtures")
        return json.loads(path.read_text(encoding="utf-8"))
    raise SourceError(f"unknown source: {source}")
