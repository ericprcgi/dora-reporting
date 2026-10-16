import pytest


@pytest.fixture(autouse=True)
def _record_fi_source(request, record_property):
    """Copy the fi_source marker into the JUnit report for the CI summary."""
    marker = request.node.get_closest_marker("fi_source")
    if marker:
        record_property("fi_source", marker.args[0])
