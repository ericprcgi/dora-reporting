"""Build FI's DORA Initial report from an incident snapshot (see sources.build_snapshot).

Field sources and transformations are documented in Confluence:
"Data Dictionary – Initial Report".
"""
from dora_reporting import settings
from dora_reporting.formatters import format_datetime, normalize_phone

SCHEMA_REF = "https://schemas.fi.se/esma/dora/v1/dora_initial_schema.json"


class ReportError(Exception):
    """The incident cannot be reported (not major, or data is missing)."""


def _required(snapshot: dict, field: str) -> str:
    value = snapshot["dora"].get(field) or ""
    if not value.strip():
        raise ReportError(f"{snapshot['incident']['number']}: {field} is empty")
    return value.strip()


def _timestamp(snapshot: dict, field: str) -> str:
    value = _required(snapshot, field)
    try:
        return format_datetime(value)
    except ValueError as exc:
        raise ReportError(f"{snapshot['incident']['number']}: {field} is not a UTC timestamp: {value!r}") from exc


def _affected_entity(snapshot: dict) -> dict:
    """Fields 1.4-1.6: the legal entity set on the incident (one per report)."""
    name = _required(snapshot, "legal_entity")
    entity = snapshot["legal_entities"].get(name)
    if entity is None:
        raise ReportError(f"{snapshot['incident']['number']}: legal entity {name!r} is not in the "
                          "Legal Entity Register")
    return {
        "affectedEntityType": [entity["entity_type"]],
        "affectedEntity-name": entity["name"],
        "affectedEntity-LEI": entity["lei"],
    }


def _contact(officer: dict, prefix: str) -> dict:
    return {
        f"{prefix}-name": officer["name"],
        f"{prefix}-email": officer["email"],
        f"{prefix}-phone": normalize_phone(officer["phone"]),
    }


def build_initial_report(snapshot: dict) -> dict:
    incident, dora = snapshot["incident"], snapshot["dora"]
    if not dora.get("major"):
        raise ReportError(f"{incident['number']} is not classified as a major incident")
    detected_at = _timestamp(snapshot, "detected_at")
    classified_at = _timestamp(snapshot, "classified_at")
    officer = snapshot["reporting_officer"]

    data = {
        "incidentSubmission": "initial_notification",
        "submittingEntity-name": settings.SUBMITTING_ENTITY_NAME,
        "submittingEntity-LEI": settings.SUBMITTING_ENTITY_LEI,
        **_affected_entity(snapshot),
        **_contact(officer, "primaryContact"),
        # FI requires a secondary contact. No secondary contact is appointed,
        # so the primary contact is repeated.
        **_contact(officer, "secondaryContact"),
        "reportCurrency": settings.REPORT_CURRENCY,
        "financialEntityCode": incident["number"],
        "detectionDateTime": detected_at,
        "classificationDateTime": classified_at,
        "incidentDescription": incident.get("description") or incident["short_description"],
        "classificationCriterion": list(dora["criteria"]),
        "incidentDiscovery": _required(snapshot, "discovery"),
        "isBusinessContinuityActivated": bool(dora.get("bcp_activated")),
    }
    return {
        "schemaRef": SCHEMA_REF,
        "reportingDate": dora["classified_at"][:10],
        "financialEntityId": settings.FINANCIAL_ENTITY_ID,
        "data": data,
    }
