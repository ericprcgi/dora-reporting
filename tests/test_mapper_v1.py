from datetime import UTC, datetime

import pytest

from dora_reporting.mapper_initial import ReportError, build_initial_report


@pytest.mark.fi_source("FI guidance: 1.2 and 1.3a submitting entity identified by LEI")
def test_submitting_entity_is_swedish_bank_with_lei(snapshot):
    data = build_initial_report(snapshot)["data"]
    assert data["submittingEntity-name"] == "Swedish Bank AB"
    assert data["submittingEntity-LEI"] == "DEMO00SWEDISHBANK062"
    assert "submittingEntity-code" not in data


@pytest.mark.fi_source("v1 schema: financialEntityCode (2.1) is the bank's incident reference")
def test_financial_entity_code_is_incident_number(snapshot):
    assert build_initial_report(snapshot)["data"]["financialEntityCode"] == "INC0010007"


@pytest.mark.fi_source("FI guidance: detection and classification times in UTC")
def test_detection_and_classification_times_are_utc(snapshot):
    data = build_initial_report(snapshot)["data"]
    assert datetime.fromisoformat(data["detectionDateTime"]) == datetime(2026, 3, 12, 8, 10, tzinfo=UTC)
    assert datetime.fromisoformat(data["classificationDateTime"]) == datetime(2026, 3, 12, 11, 0, tzinfo=UTC)


@pytest.mark.fi_source("v1 schema: classificationCriterion and incidentDiscovery code lists")
def test_classification_criteria_and_discovery_from_incident(snapshot):
    data = build_initial_report(snapshot)["data"]
    assert data["classificationCriterion"] == [
        "critical_services_affected",
        "clients_financial_counterparts_and_transactions_affected",
    ]
    assert data["incidentDiscovery"] == "monitoring_systems"


@pytest.mark.fi_source("v1 schema: primary contact name and email")
def test_primary_contact_name_and_email_from_reporting_officer(snapshot):
    data = build_initial_report(snapshot)["data"]
    assert data["primaryContact-name"] == "Sara Nyberg"
    assert data["primaryContact-email"] == "sara.nyberg@swedishbank.example"


@pytest.mark.fi_source("v1 schema: isBusinessContinuityActivated and reportCurrency")
def test_business_continuity_flag_and_currency(snapshot):
    snapshot["dora"]["bcp_activated"] = False
    data = build_initial_report(snapshot)["data"]
    assert data["isBusinessContinuityActivated"] is False
    assert data["reportCurrency"] == "SEK"


@pytest.mark.fi_source("DORA Article 19: only major ICT-related incidents are reported")
def test_non_major_incident_is_rejected(snapshot):
    snapshot["dora"]["major"] = False
    with pytest.raises(ReportError, match="not classified as a major incident"):
        build_initial_report(snapshot)


@pytest.mark.fi_source("v1 schema: classificationDateTime is required")
def test_missing_classification_time_is_rejected(snapshot):
    snapshot["dora"]["classified_at"] = ""
    with pytest.raises(ReportError, match="classified_at"):
        build_initial_report(snapshot)


@pytest.mark.fi_source("v1 schema: detectionDateTime format date-time")
def test_malformed_detection_time_is_rejected(snapshot):
    snapshot["dora"]["detected_at"] = "12/03/2026 08:10"
    with pytest.raises(ReportError, match="detected_at"):
        build_initial_report(snapshot)


@pytest.mark.fi_source("v1 schema: affectedEntity-name and affectedEntity-LEI (1.5-1.6) from the Legal Entity Register")
def test_legal_entity_missing_from_the_register_is_named(snapshot):
    snapshot["dora"]["legal_entity"] = "Swedish Bank Paymnets AB"
    with pytest.raises(ReportError, match="Swedish Bank Paymnets AB.*Legal Entity Register"):
        build_initial_report(snapshot)
