"""
Conformance: Opcode Signatures - gelu and silu activations
Spec reference: Opcode Signatures > Elementwise > Unary Operations
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("gelu_basic", "compute C { gelu.async X, out Y }", "valid"),
    ("silu_basic", "compute C { silu.async X, out Y }", "valid"),
    ("gelu_shape_mismatch", "compute C { gelu.async X, out Y }", "error: shapes must be identical"),
    ("gelu_type_mismatch", "compute C { gelu.async X, out Y }", "error: element types must match"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_activations(description, source, expected):
    """Activation function opcode signatures."""
    # Conformance specification — to be wired to parser/semantic checker
    pass
