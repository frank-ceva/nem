"""
Conformance: Constant Declarations - basic literal assignments
Spec reference: Constant Declarations
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("simple_literal", "const X = 42\nbuffer B : L2 (size=X, align=64)", "valid"),
    ("zero_value", "const X = 0", "valid"),
    ("large_value", "const X = 1000000", "valid"),
    ("const_in_buffer_size", "const S = 1024\nbuffer B : L2 (size=S, align=64)", "valid"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_const_basic(runner, description, source, expected):
    """Basic constant declarations with literal values."""
    result = runner.validate(source)
    if expected == "valid":
        assert result.valid, f"Expected valid but got errors: {result.diagnostics}"
    else:
        assert not result.valid, f"Expected error but got valid"
        error_text = expected.removeprefix("error: ")
        assert any(error_text.lower() in d.lower() for d in result.diagnostics), \
            f"Expected '{error_text}' in diagnostics: {result.diagnostics}"
