"""
Conformance: Device Configuration - memory size declarations
Spec reference: Device Configuration, Schema Rules
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("l2_size", "topology T { l2_size_bytes = 1048576 }", "valid"),
    ("l1_size", "topology T { per_engine { l1_size_bytes = 524288 } }", "valid"),
    ("zero_l2_size", "topology T { l2_size_bytes = 0 }", "error: memory sizes must be > 0"),
    ("zero_l1_size", "topology T { per_engine { l1_size_bytes = 0 } }", "error: memory sizes must be > 0"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_memory_sizes(description, source, expected):
    """Device configuration memory size declarations."""
    # Conformance specification — to be wired to parser/semantic checker
    pass
