"""
Conformance: Type System - quantization descriptors
Spec reference: Type System > Quantization Descriptor
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("per_tensor", "region R : L2 (size=1024, quant=per_tensor(scale=0.5, zero_point=128))", "valid"),
    ("per_channel", "region R : L2 (size=1024, quant=per_channel(axis=0, scales=[0.5, 0.25], zero_points=[128, 64]))", "valid"),
    ("per_group", "region R : L2 (size=1024, quant=per_group(axis=0, group_size=32, scales=[0.5, 0.25], zero_points=[128, 64]))", "valid"),
    ("per_group_zero_size", "region R : L2 (size=1024, quant=per_group(axis=0, group_size=0, scales=[0.5], zero_points=[128]))", "error: group_size must be positive"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_quant_desc(description, source, expected):
    """Quantization descriptor syntax and validation."""
    # Conformance specification — to be wired to parser/semantic checker
    pass
