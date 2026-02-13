"""
Conformance: Constant Declarations - operators in expressions
Spec reference: Constant Declarations
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("addition", "const X = 10 + 5", "valid"),
    ("subtraction", "const X = 10 - 3", "valid"),
    ("multiplication", "const X = 4 * 8", "valid"),
    ("division", "const X = 20 / 3", "valid"),  # truncates to 6
    ("modulo", "const X = 17 mod 5", "valid"),  # equals 2
    ("parentheses", "const X = (2 + 3) * 4", "valid"),
    ("mixed_operators", "const X = 10\nconst Y = (X + 3) * 2 - 1", "valid"),
    ("nested_parens", "const X = ((2 + 3) * (4 - 1))", "valid"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_const_operators(runner, description, source, expected):
    """Constant expressions using arithmetic operators."""
    result = runner.validate(source)
    if expected == "valid":
        assert result.valid, f"Expected valid but got errors: {result.diagnostics}"
    else:
        assert not result.valid, f"Expected error but got valid"
        error_text = expected.removeprefix("error: ")
        assert any(error_text.lower() in d.lower() for d in result.diagnostics), \
            f"Expected '{error_text}' in diagnostics: {result.diagnostics}"
