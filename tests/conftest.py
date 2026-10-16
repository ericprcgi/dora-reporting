import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _record_fi_source(request, record_property):
    """Copy the fi_source marker into the JUnit report for the CI summary."""
    marker = request.node.get_closest_marker("fi_source")
    if marker:
        record_property("fi_source", marker.args[0])


@pytest.fixture
def snapshot():
    """ServiceNow snapshot of the closed major incident INC0009817 (March 2026)."""
    return json.loads((FIXTURES / "INC0009817.json").read_text(encoding="utf-8"))
