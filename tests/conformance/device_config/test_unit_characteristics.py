"""
Conformance: Device Configuration - unit characteristics
Spec reference: Device Configuration, Inheritance Rules
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("nmu_macs", "topology T { unit_characteristics { NMU { int8_macs = 4096 } } }", "valid"),
    ("seq_tokens", "topology T { unit_characteristics { SEQ { max_active_tokens = 16 } } }", "valid"),
    ("unknown_key", "topology T { unit_characteristics { NMU { future_key = 100 } } }", "valid"),
    ("empty_group", "topology T { unit_characteristics { CSTL { } } }", "valid"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_unit_characteristics(description, source, expected):
    """Device configuration unit characteristics declarations."""
    # Conformance specification — to be wired to parser/semantic checker
    pass
