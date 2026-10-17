"""Reviewed copy of the Confluence pages "Legal Entity Register" and "DORA Reporting Contacts".

The files in reference_data/ are updated by a pull request whenever the pages change.
"""
import json
from pathlib import Path

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "reference_data"


def _load(name: str):
    return json.loads((REFERENCE_DIR / name).read_text(encoding="utf-8"))


def legal_entities() -> dict[str, dict]:
    """The group's legal entities by name: entity_type, lei, parent and business_services."""
    return {entity["name"]: entity for entity in _load("legal_entities.json")}


def reporting_officer() -> dict:
    """The DORA reporting officer (primary contact): name, email and phone as stored."""
    return _load("contacts.json")["reporting_officer"]
