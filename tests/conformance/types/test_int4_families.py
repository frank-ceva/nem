"""
Conformance: Type Family Conformance - INT4 mixed-precision families
Spec reference: Appendix: Type Family Definitions
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("gemm_int4_no_bias", "compute C { gemm.async A, W, out Y (accum_type=i32) }", "valid"),
    ("gemm_int4_with_bias", "compute C { gemm.async A, W, bias, out Y (accum_type=i32) }", "valid"),
    ("conv2d_int4_no_bias", "compute C { conv2d.async X, W, out Y (accum_type=i32, stride=[1,1]) }", "valid"),
    ("conv2d_int4_wrong_accum", "compute C { gemm.async A, W, out Y (accum_type=i16) }", "error: accum_type must equal i32"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_int4_families(description, source, expected):
    """INT4 mixed-precision type family validation."""
    # Conformance specification — to be wired to parser/semantic checker
    pass
