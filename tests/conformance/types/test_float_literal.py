"""
Conformance: Formal Language Definition - FLOAT literals
Spec reference: Formal Language Definition > Grammar
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("simple_float", "compute C { layernorm.async X, out Y (axis=0, epsilon=1.0) }", "valid"),
    ("scientific_notation", "compute C { layernorm.async X, out Y (axis=0, epsilon=1.0e-5) }", "valid"),
    ("scientific_positive_exp", "compute C { layernorm.async X, out Y (axis=0, epsilon=2.5e+3) }", "valid"),
    ("float_in_buffer_size", "buffer B : L2 (size=1.5, align=64)", "error: buffer sizes must be integer"),
    ("float_in_const", "const X = 1.5", "error: const declarations must be integer"),
    ("float_in_loop_bound", "loop i in [0..1.5] { }", "error: loop bounds must be integer"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_float_literal(description, source, expected):
    """FLOAT literal syntax and validation."""
    # Conformance specification — to be wired to parser/semantic checker
    pass
