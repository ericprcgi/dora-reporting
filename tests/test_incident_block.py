import re

import pytest

from dora_reporting.incident_block import REQUIRED, IncidentBlockError, parse_description

MARCH = ("Payment Hub stopped processing transactions. Card payments and settlement flows for fund trading "
         "were unavailable until the service was restored.\n\nDORA classification\n"
         "Classification: major ICT-related incident\nLegal entity: Swedish Bank Payments AB\n"
         "Detected (UTC): 2026-03-12 08:10\nClassified as major (UTC): 2026-03-12 11:00\n"
         "Criteria: critical_services_affected, clients_financial_counterparts_and_transactions_affected\n"
         "Discovered via: monitoring_systems\nBusiness continuity plan activated: yes\n"
         "Confirmed affected entities: Swedish Bank Payments AB, Swedish Bank Fonder AB\n"
         "Confirmed by: Maria Lind (incident manager), 2026-03-19 11:00 local time (10:00 UTC)")


def test_block_is_parsed_into_the_snapshot_fields():
    narrative, dora = parse_description(MARCH)
    assert narrative.startswith("Payment Hub stopped") and narrative.endswith("restored.")
    assert dora == {"major": True, "legal_entity": "Swedish Bank Payments AB",
                    "detected_at": "2026-03-12 08:10:00", "classified_at": "2026-03-12 11:00:00",
                    "criteria": ["critical_services_affected",
                                 "clients_financial_counterparts_and_transactions_affected"],
                    "discovery": "monitoring_systems", "bcp_activated": True,
                    "confirmed_entities": ["Swedish Bank Payments AB", "Swedish Bank Fonder AB"],
                    "confirmed_by": "Maria Lind (incident manager), 2026-03-19 11:00 local time (10:00 UTC)"}


def test_windows_line_endings_and_extra_spaces_are_accepted():
    _, dora = parse_description(MARCH.replace("\n", "\r\n").replace("Legal entity: ", "Legal entity :  "))
    assert dora["legal_entity"] == "Swedish Bank Payments AB"


@pytest.mark.parametrize("description", ["", None, "Payment Hub stopped."])
def test_missing_block_is_an_error(description):
    with pytest.raises(IncidentBlockError, match="DORA classification block missing"):
        parse_description(description)


@pytest.mark.parametrize("line", REQUIRED)
def test_missing_required_line_is_named(line):
    text = "\n".join(row for row in MARCH.splitlines() if not row.startswith(line + ":"))
    with pytest.raises(IncidentBlockError, match=re.escape(line)):
        parse_description(text)


def test_without_confirmation_lines_the_confirmed_entities_are_empty():
    text = "\n".join(row for row in MARCH.splitlines() if not row.startswith("Confirmed"))
    _, dora = parse_description(text)
    assert dora["confirmed_entities"] == [] and dora["confirmed_by"] == ""


@pytest.mark.parametrize("bad", ["12/03/2026 08:10", "2026-03-12T08:10:00Z"])
def test_malformed_time_is_an_error(bad):
    with pytest.raises(IncidentBlockError, match="Detected"):
        parse_description(MARCH.replace("2026-03-12 08:10", bad))
