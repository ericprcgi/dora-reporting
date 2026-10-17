import pytest

from dora_reporting.reference_data import legal_entities, reporting_officer
from dora_reporting.sources import SourceError, build_snapshot
from test_incident_block import MARCH


def raw(description=MARCH):
    services = [("b1000000000000000000000000000001", "Payment Hub"),
                ("b1000000000000000000000000000003", "Fund Trading"),
                ("b1000000000000000000000000000002", "Card Payments")]
    return {
        "incident": {"sys_id": "d1000000000000000000000000010042", "number": "INC0010007",
                     "short_description": "Payment Hub outage", "description": description, "state": "7"},
        "affected_services": [{"sys_id": sys_id, "name": name} for sys_id, name in services],
    }


def test_register_has_the_three_group_entities():
    entities = legal_entities()
    assert {n: (e["entity_type"], e["lei"]) for n, e in entities.items()} == {
        "Swedish Bank AB": ("credit_institution", "DEMO00SWEDISHBANK062"),
        "Swedish Bank Payments AB": ("payment_institution", "DEMO00SWBPAYMENTS069"),
        "Swedish Bank Fonder AB": ("management_company", "DEMO00SWBFONDER00089")}
    assert entities["Swedish Bank Payments AB"]["business_services"] == ["Card Payments"]


def test_reporting_officer_phone_is_stored_as_in_confluence():
    assert reporting_officer() == {"name": "Sara Nyberg", "email": "sara.nyberg@swedishbank.example",
                                   "phone": "08-123 456 78"}


def test_snapshot_combines_the_incident_and_the_reference_data():
    snapshot = build_snapshot(raw())
    assert snapshot["affected_services"] == ["Card Payments", "Fund Trading", "Payment Hub"]
    assert snapshot["incident"]["description"].endswith("until the service was restored.")
    assert "DORA classification" not in snapshot["incident"]["description"]
    assert snapshot["dora"]["legal_entity"] == "Swedish Bank Payments AB"
    assert len(snapshot["legal_entities"]) == 3
    assert snapshot["reporting_officer"]["name"] == "Sara Nyberg"


def test_snapshot_without_a_block_is_a_source_error():
    with pytest.raises(SourceError, match="INC0010007: DORA classification block missing"):
        build_snapshot(raw(description=""))
