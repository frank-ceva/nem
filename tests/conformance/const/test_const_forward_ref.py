"""
Conformance: Constant Declarations - forward reference errors
Spec reference: Constant Declarations
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("forward_reference", "const A = B + 1\nconst B = 10", "error: forward reference to undeclared constant B"),
    ("self_reference", "const A = A + 1", "error: forward reference to undeclared constant A"),
    ("mutual_reference", "const A = B\nconst B = A", "error: forward reference to undeclared constant B"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_const_forward_ref(description, source, expected):
    """Forward references in constant expressions are errors."""
    # Conformance specification — to be wired to parser/semantic checker
    pass
