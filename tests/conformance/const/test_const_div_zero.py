"""
Conformance: Constant Declarations - division by zero errors
Spec reference: Constant Declarations
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("division_by_zero", "const X = 10 / 0", "error: division by zero in constant expression"),
    ("modulo_by_zero", "const X = 10 mod 0", "error: division by zero in constant expression"),
    ("indirect_div_zero", "const A = 0\nconst B = 10 / A", "error: division by zero in constant expression"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_const_div_zero(runner, description, source, expected):
    """Division or modulo by zero in constant expressions are errors."""
    result = runner.validate(source)
    if expected == "valid":
        assert result.valid, f"Expected valid but got errors: {result.diagnostics}"
    else:
        assert not result.valid, f"Expected error but got valid"
        error_text = expected.removeprefix("error: ")
        assert any(error_text.lower() in d.lower() for d in result.diagnostics), \
            f"Expected '{error_text}' in diagnostics: {result.diagnostics}"
