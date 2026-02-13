"""
Conformance: Constant Declarations - scope restrictions
Spec reference: Constant Declarations
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("const_in_loop_body", "const T = 4\nconst S = 64\nbuffer B : L2 (size=T*S, align=64)\nloop i in [0..T-1]:\n  const X = 42\nendloop", "error: const declaration not permitted inside loop body"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_const_in_loop(runner, description, source, expected):
    """Constant declarations inside loop bodies are errors."""
    result = runner.validate(source)
    if expected == "valid":
        assert result.valid, f"Expected valid but got errors: {result.diagnostics}"
    else:
        assert not result.valid, f"Expected error but got valid"
        error_text = expected.removeprefix("error: ")
        assert any(error_text.lower() in d.lower() for d in result.diagnostics), \
            f"Expected '{error_text}' in diagnostics: {result.diagnostics}"
