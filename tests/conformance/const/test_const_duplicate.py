"""
Conformance: Constant Declarations - duplicate declaration errors
Spec reference: Constant Declarations
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("duplicate_const", "const X = 1\nconst X = 2", "error: duplicate constant declaration X"),
    ("duplicate_different_values", "const X = 10\nconst Y = 20\nconst X = 30", "error: duplicate constant declaration X"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_const_duplicate(runner, description, source, expected):
    """Duplicate constant declarations are errors."""
    result = runner.validate(source)
    if expected == "valid":
        assert result.valid, f"Expected valid but got errors: {result.diagnostics}"
    else:
        assert not result.valid, f"Expected error but got valid"
        error_text = expected.removeprefix("error: ")
        assert any(error_text.lower() in d.lower() for d in result.diagnostics), \
            f"Expected '{error_text}' in diagnostics: {result.diagnostics}"
