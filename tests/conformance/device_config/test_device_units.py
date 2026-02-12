"""
Conformance: Device Configuration - device_units block
Spec reference: Device Configuration, Formal Language Definition
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("sdma_and_wdm", "topology T { device_units { sDMA = 2  WDM = 1 } }", "valid"),
    ("sdma_only", "topology T { device_units { sDMA = 1 } }", "valid"),
    ("wdm_zero", "topology T { device_units { WDM = 0 } }", "valid"),
    ("missing_device_units", "topology T { }", "valid"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_device_units(description, source, expected):
    """Device configuration device_units block declarations."""
    # Conformance specification — to be wired to parser/semantic checker
    pass
