"""Build FI's DORA Initial report from a ServiceNow incident snapshot.

Field sources and transformations are documented in Confluence:
"Data Dictionary – Initial Report".
"""
from dora_reporting import settings
from dora_reporting.formatters import format_datetime, normalize_phone

SCHEMA_REF = "https://schemas.fi.se/esma/dora/v1/dora_initial_schema.json"


class ReportError(Exception):
    """The incident cannot be reported (not major, or data is missing)."""


def _required(incident: dict, field: str) -> str:
    value = (incident.get(field) or "").strip()
    if not value:
        raise ReportError(f"{incident.get('number')}: {field} is empty")
    return value


def _timestamp(incident: dict, field: str) -> str:
    value = _required(incident, field)
    try:
        return format_datetime(value)
    except ValueError as exc:
        raise ReportError(f"{incident.get('number')}: {field} is not a ServiceNow UTC timestamp: {value!r}") from exc


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _affected_entity(snapshot: dict) -> dict:
    """Fields 1.4-1.6: the legal entity set on the incident (one per report)."""
    incident = snapshot["incident"]
    company = snapshot["companies"].get(incident.get("company") or "")
    if company is None:
        raise ReportError(f"{incident['number']}: company is not set")
    return {
        "affectedEntityType": [company["u_dora_entity_type"]],
        "affectedEntity-name": company["name"],
        "affectedEntity-LEI": company["u_lei"],
    }


def _contact(officer: dict, prefix: str) -> dict:
    return {
        f"{prefix}-name": officer["name"],
        f"{prefix}-email": officer["email"],
        f"{prefix}-phone": normalize_phone(officer["phone"]),
    }


def build_initial_report(snapshot: dict) -> dict:
    incident = snapshot["incident"]
    if incident.get("u_dora_major") != "true":
        raise ReportError(f"{incident['number']} is not classified as a major incident")
    detected_at = _timestamp(incident, "u_dora_detected_at")
    classified_at = _timestamp(incident, "u_dora_classified_at")
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
        "classificationCriterion": _split(incident.get("u_dora_criteria") or ""),
        "incidentDiscovery": _required(incident, "u_dora_discovery"),
        "isBusinessContinuityActivated": incident.get("u_dora_bcp_activated") == "true",
    }
    return {
        "schemaRef": SCHEMA_REF,
        "reportingDate": incident["u_dora_classified_at"][:10],
        "financialEntityId": settings.FINANCIAL_ENTITY_ID,
        "data": data,
    }
