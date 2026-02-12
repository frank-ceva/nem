"""
Conformance: Constant Declarations - name conflict errors
Spec reference: Constant Declarations
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("shadows_buffer", "buffer X : L2 (size=64, align=64)\nconst X = 42", "error: name conflict - X already declared as buffer"),
    ("const_then_buffer", "const X = 64\nbuffer X : L2 (size=64, align=64)", "error: name conflict - X already declared as const"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_const_shadowing(description, source, expected):
    """Name conflicts between constants and other declarations are errors."""
    # Conformance specification — to be wired to parser/semantic checker
    pass
