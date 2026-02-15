from __future__ import annotations

import pytest

from nemlib.core import ElementType


class TestElementType:
    def test_all_types_exist(self):
        """Test that all 13 element types are defined."""
        assert ElementType.I4
        assert ElementType.I8
        assert ElementType.I16
        assert ElementType.I32
        assert ElementType.U8
        assert ElementType.U16
        assert ElementType.U32
        assert ElementType.F16
        assert ElementType.BF16
        assert ElementType.TF32
        assert ElementType.F32
        assert ElementType.F64
        assert ElementType.BOOL

    @pytest.mark.parametrize(
        "elem_type,expected_bits",
        [
            (ElementType.I4, 4),
            (ElementType.I8, 8),
            (ElementType.I16, 16),
            (ElementType.I32, 32),
            (ElementType.U8, 8),
            (ElementType.U16, 16),
            (ElementType.U32, 32),
            (ElementType.F16, 16),
            (ElementType.BF16, 16),
            (ElementType.TF32, 32),
            (ElementType.F32, 32),
            (ElementType.F64, 64),
            (ElementType.BOOL, 8),
        ],
    )
    def test_bitwidth(self, elem_type, expected_bits):
        """Test that bitwidth() returns correct values."""
        assert elem_type.bitwidth() == expected_bits

    @pytest.mark.parametrize(
        "elem_type,expected",
        [
            (ElementType.I4, True),
            (ElementType.I8, True),
            (ElementType.I16, True),
            (ElementType.I32, True),
            (ElementType.U8, True),
            (ElementType.U16, True),
            (ElementType.U32, True),
            (ElementType.F16, False),
            (ElementType.BF16, False),
            (ElementType.TF32, False),
            (ElementType.F32, False),
            (ElementType.F64, False),
            (ElementType.BOOL, False),
        ],
    )
    def test_is_integer(self, elem_type, expected):
        """Test that is_integer() returns correct values."""
        assert elem_type.is_integer() == expected

    @pytest.mark.parametrize(
        "elem_type,expected",
        [
            (ElementType.I4, False),
            (ElementType.I8, False),
            (ElementType.I16, False),
            (ElementType.I32, False),
            (ElementType.U8, False),
            (ElementType.U16, False),
            (ElementType.U32, False),
            (ElementType.F16, True),
            (ElementType.BF16, True),
            (ElementType.TF32, True),
            (ElementType.F32, True),
            (ElementType.F64, True),
            (ElementType.BOOL, False),
        ],
    )
    def test_is_float(self, elem_type, expected):
        """Test that is_float() returns correct values."""
        assert elem_type.is_float() == expected
