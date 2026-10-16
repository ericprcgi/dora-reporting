"""Formatting of values for FI's DORA incident reports."""
from datetime import datetime


def format_datetime(servicenow_utc: str) -> str:
    """Format a ServiceNow UTC timestamp ("YYYY-MM-DD hh:mm:ss") for FI.

    Format according to FI's guide for DORA incident reporting
    (lathund v1.2, 2026-04-27): YYYY-MM-DDThh:mm:ss.0Z, in UTC.
    """
    parsed = datetime.strptime(servicenow_utc, "%Y-%m-%d %H:%M:%S")
    return parsed.strftime("%Y-%m-%dT%H:%M:%S") + ".0Z"


def normalize_phone(raw: str) -> str:
    """Remove spaces and hyphens and replace a leading 0 with the country code 46."""
    digits = raw.replace(" ", "").replace("-", "")
    if digits.startswith("0"):
        digits = "46" + digits[1:]
    return digits
