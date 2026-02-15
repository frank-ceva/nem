"""NEM element type definitions."""

from __future__ import annotations

from enum import Enum


class ElementType(Enum):
    """All NEM element types from the spec grammar and opcode registry."""

    I4 = "i4"
    I8 = "i8"
    I16 = "i16"
    I32 = "i32"
    U8 = "u8"
    U16 = "u16"
    U32 = "u32"
    F16 = "f16"
    BF16 = "bf16"
    TF32 = "tf32"
    F32 = "f32"
    F64 = "f64"
    BOOL = "bool"

    def bitwidth(self) -> int:
        """Return bitwidth of this element type."""
        table: dict[ElementType, int] = {
            ElementType.I4: 4,
            ElementType.I8: 8,
            ElementType.I16: 16,
            ElementType.I32: 32,
            ElementType.U8: 8,
            ElementType.U16: 16,
            ElementType.U32: 32,
            ElementType.F16: 16,
            ElementType.BF16: 16,
            ElementType.TF32: 32,
            ElementType.F32: 32,
            ElementType.F64: 64,
            ElementType.BOOL: 8,
        }
        return table[self]

    def is_integer(self) -> bool:
        """Return True if this is a signed or unsigned integer type."""
        return self in (
            ElementType.I4,
            ElementType.I8,
            ElementType.I16,
            ElementType.I32,
            ElementType.U8,
            ElementType.U16,
            ElementType.U32,
        )

    def is_float(self) -> bool:
        """Return True if this is a floating-point type."""
        return self in (
            ElementType.F16,
            ElementType.BF16,
            ElementType.TF32,
            ElementType.F32,
            ElementType.F64,
        )
