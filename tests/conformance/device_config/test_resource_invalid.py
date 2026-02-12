"""
Conformance: Decorators - @resource-invalid unit types
Spec reference: Decorators
"""
import pytest


# Each test case is a tuple: (description, nem_source, expected_outcome)
# expected_outcome is either "valid" or "error: <description>"

CASES = [
    ("resource_nmu_valid", "compute C @resource NMU[0] { }", "valid"),
    ("resource_cstl_valid", "compute C @resource CSTL[0] { }", "valid"),
    ("resource_dma_valid", "transfer T @resource DMA[0] { }", "valid"),
    ("resource_vpu_valid", "compute C @resource VPU[0] { }", "valid"),
    ("resource_seq_invalid", "compute C @resource SEQ[0] { }", "error: SEQ is not a valid @resource target"),
    ("resource_sdma_invalid", "transfer T @resource sDMA[0] { }", "error: sDMA is not a valid @resource target"),
    ("resource_wdm_invalid", "transfer T @resource WDM[0] { }", "error: WDM is not a valid @resource target"),
]


@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_resource_invalid(description, source, expected):
    """Decorator @resource-invalid unit type validation."""
    # Conformance specification — to be wired to parser/semantic checker
    pass
