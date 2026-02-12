"""
Conformance: Constant Declarations - usage in various contexts
Spec reference: Constant Declarations
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("in_buffer_size", "const S = 4096\nbuffer B : L2 (size=S, align=64)", "valid"),
    ("in_buffer_size_expr", "const N = 2\nconst S = 4096\nbuffer B : L1 (size=N*S, align=64)", "valid"),
    ("in_region_offset", "const OFF = 1024\nconst EXT = 512\nbuffer B : L2 (size=2048, align=64)\nlet R = region(B, OFF, EXT)\n         elem=i8, shape=[512], layout=C", "valid"),
    ("in_shape_dim", "const H = 16\nconst W = 16\nconst C = 64\nconst S = H * W * C\nbuffer B : L2 (size=S, align=64)\nlet R = region(B, 0, S)\n         elem=i8, shape=[1,H,W,C], layout=NHWC", "valid"),
    ("in_loop_bound", "const T = 8\nconst S = 1024\nbuffer B : L2 (size=T*S, align=64)\nloop i in [0..T-1]:\nendloop", "valid"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_const_in_contexts(description, source, expected):
    """Constants used in buffer sizes, region parameters, loop bounds, and shape dimensions."""
    # Conformance specification — to be wired to parser/semantic checker
    pass
