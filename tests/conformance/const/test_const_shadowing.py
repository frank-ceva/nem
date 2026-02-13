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
def test_const_shadowing(runner, description, source, expected):
    """Name conflicts between constants and other declarations are errors."""
    result = runner.validate(source)
    if expected == "valid":
        assert result.valid, f"Expected valid but got errors: {result.diagnostics}"
    else:
        assert not result.valid, f"Expected error but got valid"
        error_text = expected.removeprefix("error: ")
        assert any(error_text.lower() in d.lower() for d in result.diagnostics), \
            f"Expected '{error_text}' in diagnostics: {result.diagnostics}"
