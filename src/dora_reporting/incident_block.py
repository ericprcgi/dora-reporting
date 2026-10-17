"""Read the DORA classification block in a ServiceNow incident description.

The incident manager keeps the DORA data at the end of the description:

    <what happened>

    DORA classification
    Classification: major ICT-related incident
    Legal entity: Swedish Bank Payments AB
    Detected (UTC): 2026-03-12 08:10
    ...

Field meanings are documented in Confluence: "Data Dictionary – Initial Report".
"""
import re

HEADING = "DORA classification"
MAJOR = "major ICT-related incident"
REQUIRED = ("Classification", "Legal entity", "Detected (UTC)", "Classified as major (UTC)", "Criteria",
            "Discovered via", "Business continuity plan activated")
TIME = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}")


class IncidentBlockError(Exception):
    """The DORA classification block is missing or incomplete."""


def _time(lines: dict, key: str) -> str:
    value = lines[key]
    if not TIME.fullmatch(value):
        raise IncidentBlockError(f"{key}: expected YYYY-MM-DD hh:mm, got {value!r}")
    return value + ":00"


def _flag(lines: dict, key: str) -> bool:
    value = lines[key].lower()
    if value not in ("yes", "no"):
        raise IncidentBlockError(f"{key}: expected yes or no, got {lines[key]!r}")
    return value == "yes"


def _list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_description(description: str | None) -> tuple[str, dict]:
    """Return the narrative (the text before the block) and the block's values."""
    rows = (description or "").splitlines()
    try:
        start = next(i for i, row in enumerate(rows) if row.strip() == HEADING)
    except StopIteration:
        raise IncidentBlockError("DORA classification block missing") from None
    lines = {}
    for row in rows[start + 1:]:
        key, colon, value = row.partition(":")
        if colon:
            lines[key.strip()] = value.strip()
    missing = [key for key in REQUIRED if not lines.get(key)]
    if missing:
        raise IncidentBlockError("DORA classification block lacks: " + ", ".join(missing))
    narrative = "\n".join(rows[:start]).strip()
    return narrative, {
        "major": lines["Classification"] == MAJOR,
        "legal_entity": lines["Legal entity"],
        "detected_at": _time(lines, "Detected (UTC)"),
        "classified_at": _time(lines, "Classified as major (UTC)"),
        "criteria": _list(lines["Criteria"]),
        "discovery": lines["Discovered via"],
        "bcp_activated": _flag(lines, "Business continuity plan activated"),
        "confirmed_entities": _list(lines.get("Confirmed affected entities", "")),
        "confirmed_by": lines.get("Confirmed by", ""),
    }
