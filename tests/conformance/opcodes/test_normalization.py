"""
Conformance: Opcode Signatures - normalization operations
Spec reference: Opcode Signatures > Normalization
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("layernorm_basic", "compute C { layernorm.async X, scale, bias, out Y (axis=1, epsilon=1.0e-5) }", "valid"),
    ("layernorm_no_scale_bias", "compute C { layernorm.async X, out Y (axis=0, epsilon=0.00001) }", "valid"),
    ("rmsnorm_basic", "compute C { rmsnorm.async X, scale, out Y (axis=1, epsilon=1.0e-5) }", "valid"),
    ("rmsnorm_no_scale", "compute C { rmsnorm.async X, out Y (axis=0, epsilon=1.0e-5) }", "valid"),
    ("layernorm_missing_epsilon", "compute C { layernorm.async X, out Y (axis=1) }", "error: epsilon is required"),
    ("layernorm_missing_axis", "compute C { layernorm.async X, out Y (epsilon=1.0e-5) }", "error: axis is required"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_normalization(description, source, expected):
    """Normalization operation opcode signatures."""
    # Conformance specification — to be wired to parser/semantic checker
    pass
