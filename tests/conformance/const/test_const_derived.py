"""
Conformance: Constant Declarations - derived constants
Spec reference: Constant Declarations
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("derived_from_const", "const A = 10\nconst B = A * 2", "valid"),
    ("chain_of_three", "const A = 2\nconst B = A * 3\nconst C = B + 1", "valid"),
    ("complex_derivation", "const TiH = 16\nconst TiW = 16\nconst Cin = 64\nconst tileX_bytes = TiH * TiW * Cin", "valid"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_const_derived(description, source, expected):
    """Constants derived from other constants."""
    # Conformance specification — to be wired to parser/semantic checker
    pass
