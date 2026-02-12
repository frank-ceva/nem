"""
Conformance: Opcode Signatures - softmax operations
Spec reference: Opcode Signatures > Softmax
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("softmax_basic", "compute C { softmax.async X, out Y (axis=1) }", "valid"),
    ("log_softmax_basic", "compute C { log_softmax.async X, out Y (axis=0) }", "valid"),
    ("softmax_missing_axis", "compute C { softmax.async X, out Y }", "error: axis is required"),
    ("softmax_shape_mismatch", "compute C { softmax.async X, out Y (axis=0) }", "error: shapes must be identical"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_softmax(description, source, expected):
    """Softmax operation opcode signatures."""
    # Conformance specification — to be wired to parser/semantic checker
    pass
