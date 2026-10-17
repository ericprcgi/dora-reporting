import json
from pathlib import Path

import pytest

from dora_reporting.sources import build_snapshot

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _record_fi_source(request, record_property):
    """Copy the fi_source marker into the JUnit report for the CI summary."""
    marker = request.node.get_closest_marker("fi_source")
    if marker:
        record_property("fi_source", marker.args[0])


@pytest.fixture
def raw():
    """The closed major incident INC0010007 (March 2026) as the ServiceNow Table API returns it."""
    return json.loads((FIXTURES / "INC0010007.json").read_text(encoding="utf-8"))


@pytest.fixture
def snapshot(raw):
    """INC0010007 combined with the reference data, as the mapper receives it."""
    return build_snapshot(raw)
