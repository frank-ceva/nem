"""Tests for NEM parser Step 2 features: storage declarations and memory model.

Covers:
- Buffer declarations (DDR, L2, L1, L1[expr])
- Let declarations (simple values)
- Region declarations
- Type attributes (elem, shape, layout/strides, quant)
- Quantization descriptors (per_tensor, per_channel, per_group)
- Decorators on buffers and regions
- Value parsing (strings, arrays, nested arrays)
- Multi-line continuation
- Mixed programs
- Error cases
"""

from __future__ import annotations

import pytest

from nemlib.core.expressions import (
    BinaryOp,
    FloatLiteral,
    Identifier,
    IntLiteral,
)
from nemlib.parser import ProgramNode, parse
from nemlib.parser.ast_nodes import (
    ArrayLiteral,
    BufferDeclNode,
    ConstDeclNode,
    LetDeclNode,
    PerChannelQuantNode,
    PerGroupQuantNode,
    PerTensorQuantNode,
    RegionDeclNode,
    StringLiteral,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_ok(source: str) -> ProgramNode:
    """Parse source and assert no errors."""
    ast, diag = parse(source, "<test>")
    assert not diag.has_errors(), diag.format_all()
    return ast


# ---------------------------------------------------------------------------
# Buffer Declarations
# ---------------------------------------------------------------------------


class TestBufferDecl:
    def test_buffer_ddr_with_size_and_align(self) -> None:
        ast = parse_ok("buffer X_DDR : DDR (size=1024, align=64)")
        assert len(ast.statements) == 1
        buf = ast.statements[0]
        assert isinstance(buf, BufferDeclNode)
        assert buf.name == "X_DDR"
        assert buf.mem_level == "DDR"
        assert isinstance(buf.size, IntLiteral) and buf.size.value == 1024
        assert isinstance(buf.align, IntLiteral) and buf.align.value == 64
        assert buf.l1_index is None
        assert buf.decorators == ()

    def test_buffer_l2_with_expression_size(self) -> None:
        src = "buffer X_L2 : L2 (size=T * tileX_bytes, align=64)"
        ast = parse_ok(src)
        buf = ast.statements[0]
        assert isinstance(buf, BufferDeclNode)
        assert buf.name == "X_L2"
        assert buf.mem_level == "L2"
        assert isinstance(buf.size, BinaryOp) and buf.size.op == "*"
        assert isinstance(buf.align, IntLiteral) and buf.align.value == 64

    def test_buffer_l1_without_index(self) -> None:
        ast = parse_ok("buffer X_L1 : L1 (size=512)")
        buf = ast.statements[0]
        assert isinstance(buf, BufferDeclNode)
        assert buf.name == "X_L1"
        assert buf.mem_level == "L1"
        assert buf.l1_index is None
        assert isinstance(buf.size, IntLiteral) and buf.size.value == 512

    def test_buffer_l1_with_index(self) -> None:
        ast = parse_ok("buffer X_L1 : L1[0] (size=2*tileX_bytes, align=64)")
        buf = ast.statements[0]
        assert isinstance(buf, BufferDeclNode)
        assert buf.name == "X_L1"
        assert buf.mem_level == "L1"
        assert isinstance(buf.l1_index, IntLiteral) and buf.l1_index.value == 0
        assert isinstance(buf.size, BinaryOp)
        assert isinstance(buf.align, IntLiteral) and buf.align.value == 64

    def test_buffer_l1_with_expression_index(self) -> None:
        ast = parse_ok("buffer X_L1 : L1[i + 1] (size=256)")
        buf = ast.statements[0]
        assert isinstance(buf, BufferDeclNode)
        assert buf.mem_level == "L1"
        assert isinstance(buf.l1_index, BinaryOp)
        assert buf.l1_index.op == "+"

    def test_buffer_with_size_only(self) -> None:
        ast = parse_ok("buffer X : DDR (size=100)")
        buf = ast.statements[0]
        assert isinstance(buf, BufferDeclNode)
        assert isinstance(buf.size, IntLiteral)
        assert buf.align is None

    def test_buffer_with_align_only(self) -> None:
        ast = parse_ok("buffer X : DDR (align=32)")
        buf = ast.statements[0]
        assert isinstance(buf, BufferDeclNode)
        assert buf.size is None
        assert isinstance(buf.align, IntLiteral) and buf.align.value == 32

    def test_buffer_with_simple_decorator(self) -> None:
        ast = parse_ok("buffer X : L2 (size=1024) @materialized")
        buf = ast.statements[0]
        assert isinstance(buf, BufferDeclNode)
        assert len(buf.decorators) == 1
        assert buf.decorators[0].name == "materialized"
        assert buf.decorators[0].args is None

    def test_buffer_with_decorator_with_args(self) -> None:
        ast = parse_ok("buffer X : L2 (size=1024) @max_in_flight(2)")
        buf = ast.statements[0]
        assert isinstance(buf, BufferDeclNode)
        assert len(buf.decorators) == 1
        deco = buf.decorators[0]
        assert deco.name == "max_in_flight"
        assert deco.args is not None
        assert len(deco.args) == 1
        assert isinstance(deco.args[0], IntLiteral) and deco.args[0].value == 2

    def test_buffer_with_resource_decorator(self) -> None:
        ast = parse_ok("buffer X : L1[0] (size=512) @resource(DMA[0])")
        buf = ast.statements[0]
        assert isinstance(buf, BufferDeclNode)
        assert len(buf.decorators) == 1
        # The decorator args parser will handle DMA[0] as an expression

    def test_buffer_with_multiple_decorators(self) -> None:
        src = "buffer X : L2 (size=1024) @readonly @materialized"
        ast = parse_ok(src)
        buf = ast.statements[0]
        assert isinstance(buf, BufferDeclNode)
        assert len(buf.decorators) == 2
        assert buf.decorators[0].name == "readonly"
        assert buf.decorators[1].name == "materialized"

    def test_buffer_decorator_on_continuation_line(self) -> None:
        src = """buffer X : L2 (size=1024)
@materialized"""
        ast = parse_ok(src)
        buf = ast.statements[0]
        assert isinstance(buf, BufferDeclNode)
        assert len(buf.decorators) == 1
        assert buf.decorators[0].name == "materialized"

    def test_multiple_buffers(self) -> None:
        src = """buffer A : DDR (size=1024)
buffer B : L2 (size=512)
buffer C : L1[0] (size=256)"""
        ast = parse_ok(src)
        assert len(ast.statements) == 3
        assert all(isinstance(s, BufferDeclNode) for s in ast.statements)
        names = [s.name for s in ast.statements]
        assert names == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# Let Declarations (simple)
# ---------------------------------------------------------------------------


class TestLetDecl:
    def test_let_with_int_value(self) -> None:
        ast = parse_ok("let x = 42")
        assert len(ast.statements) == 1
        let = ast.statements[0]
        assert isinstance(let, LetDeclNode)
        assert let.name == "x"
        assert isinstance(let.value, IntLiteral) and let.value.value == 42

    def test_let_with_float_value(self) -> None:
        ast = parse_ok("let pi = 3.14")
        let = ast.statements[0]
        assert isinstance(let, LetDeclNode)
        assert let.name == "pi"
        assert isinstance(let.value, FloatLiteral)
        assert let.value.value == pytest.approx(3.14)

    def test_let_with_expression_value(self) -> None:
        ast = parse_ok("let y = A + B")
        let = ast.statements[0]
        assert isinstance(let, LetDeclNode)
        assert let.name == "y"
        assert isinstance(let.value, BinaryOp) and let.value.op == "+"

    def test_let_with_string_value(self) -> None:
        ast = parse_ok('let s = "hello"')
        let = ast.statements[0]
        assert isinstance(let, LetDeclNode)
        assert let.name == "s"
        assert isinstance(let.value, StringLiteral)
        assert let.value.value == "hello"

    def test_let_with_array_value(self) -> None:
        ast = parse_ok("let arr = [1, 2, 3]")
        let = ast.statements[0]
        assert isinstance(let, LetDeclNode)
        assert let.name == "arr"
        assert isinstance(let.value, ArrayLiteral)
        assert len(let.value.elements) == 3
        assert all(isinstance(e, IntLiteral) for e in let.value.elements)

    def test_let_with_string_array(self) -> None:
        ast = parse_ok('let strs = ["a", "b", "c"]')
        let = ast.statements[0]
        assert isinstance(let, LetDeclNode)
        assert isinstance(let.value, ArrayLiteral)
        assert len(let.value.elements) == 3
        assert all(isinstance(e, StringLiteral) for e in let.value.elements)

    def test_let_with_nested_array(self) -> None:
        ast = parse_ok("let mat = [[1, 2], [3, 4]]")
        let = ast.statements[0]
        assert isinstance(let, LetDeclNode)
        assert isinstance(let.value, ArrayLiteral)
        assert len(let.value.elements) == 2
        assert all(isinstance(e, ArrayLiteral) for e in let.value.elements)

    def test_let_with_trailing_comma(self) -> None:
        ast = parse_ok("let arr = [1, 2, 3,]")
        let = ast.statements[0]
        assert isinstance(let, LetDeclNode)
        assert isinstance(let.value, ArrayLiteral)
        assert len(let.value.elements) == 3


# ---------------------------------------------------------------------------
# Region Declarations
# ---------------------------------------------------------------------------


class TestRegionDecl:
    def test_basic_region(self) -> None:
        ast = parse_ok("let X = region(X_L2, i * bytes, bytes)")
        assert len(ast.statements) == 1
        region = ast.statements[0]
        assert isinstance(region, RegionDeclNode)
        assert region.name == "X"
        assert region.buffer_name == "X_L2"
        assert isinstance(region.offset, BinaryOp)
        assert isinstance(region.extent, Identifier) and region.extent.name == "bytes"
        assert region.type_attrs is None
        assert region.decorators == ()

    def test_region_with_literal_offset_extent(self) -> None:
        ast = parse_ok("let X = region(X_L2, 0, 100)")
        region = ast.statements[0]
        assert isinstance(region, RegionDeclNode)
        assert isinstance(region.offset, IntLiteral) and region.offset.value == 0
        assert isinstance(region.extent, IntLiteral) and region.extent.value == 100

    def test_region_with_type_attrs(self) -> None:
        src = """let X = region(X_L2, 0, 100)
elem=i8, shape=[1,2,3], layout=NHWC"""
        ast = parse_ok(src)
        region = ast.statements[0]
        assert isinstance(region, RegionDeclNode)
        assert region.type_attrs is not None
        attrs = region.type_attrs
        assert attrs.elem == "i8"
        assert len(attrs.shape) == 3
        assert attrs.layout == "NHWC"
        assert attrs.strides is None

    def test_region_with_decorators(self) -> None:
        src = """let X = region(X_L2, 0, 100)
@materialized"""
        ast = parse_ok(src)
        region = ast.statements[0]
        assert isinstance(region, RegionDeclNode)
        assert len(region.decorators) == 1
        assert region.decorators[0].name == "materialized"

    def test_region_with_type_attrs_and_decorators(self) -> None:
        src = """let X = region(X_L2, 0, 100)
elem=i8, shape=[1,2,3], layout=NHWC
@materialized
@readonly"""
        ast = parse_ok(src)
        region = ast.statements[0]
        assert isinstance(region, RegionDeclNode)
        assert region.type_attrs is not None
        assert len(region.decorators) == 2
        assert region.decorators[0].name == "materialized"
        assert region.decorators[1].name == "readonly"

    def test_multiple_regions(self) -> None:
        src = """let A = region(A_L2, 0, 100)
let B = region(B_L2, 100, 200)
let C = region(C_L2, 300, 400)"""
        ast = parse_ok(src)
        assert len(ast.statements) == 3
        assert all(isinstance(s, RegionDeclNode) for s in ast.statements)
        names = [s.name for s in ast.statements]
        assert names == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# Type Attributes
# ---------------------------------------------------------------------------


class TestTypeAttrs:
    def test_type_attrs_with_layout(self) -> None:
        src = """let X = region(X_L2, 0, 100)
elem=i8, shape=[1,2,3], layout=NHWC"""
        ast = parse_ok(src)
        region = ast.statements[0]
        assert isinstance(region, RegionDeclNode)
        attrs = region.type_attrs
        assert attrs is not None
        assert attrs.elem == "i8"
        assert len(attrs.shape) == 3
        assert attrs.layout == "NHWC"
        assert attrs.strides is None

    def test_type_attrs_with_strides(self) -> None:
        src = """let X = region(X_L2, 0, 100)
elem=f32, shape=[M,N], strides=[S0, S1]"""
        ast = parse_ok(src)
        region = ast.statements[0]
        attrs = region.type_attrs
        assert attrs is not None
        assert attrs.elem == "f32"
        assert len(attrs.shape) == 2
        assert attrs.layout is None
        assert attrs.strides is not None
        assert len(attrs.strides) == 2

    def test_type_attrs_all_elem_types(self) -> None:
        elem_types = [
            "i4",
            "i8",
            "i16",
            "i32",
            "u8",
            "u16",
            "u32",
            "f16",
            "bf16",
            "tf32",
            "f32",
            "f64",
            "bool",
        ]
        for elem_type in elem_types:
            src = f"""let X = region(X_L2, 0, 100)
elem={elem_type}, shape=[1]"""
            ast = parse_ok(src)
            region = ast.statements[0]
            assert isinstance(region, RegionDeclNode)
            assert region.type_attrs is not None
            assert region.type_attrs.elem == elem_type

    def test_type_attrs_with_expression_shape(self) -> None:
        src = """let X = region(X_L2, 0, 100)
elem=i8, shape=[1, TiH, TiW, Cin]"""
        ast = parse_ok(src)
        region = ast.statements[0]
        attrs = region.type_attrs
        assert attrs is not None
        assert len(attrs.shape) == 4
        assert isinstance(attrs.shape[0], IntLiteral)
        assert isinstance(attrs.shape[1], Identifier)
        assert attrs.shape[1].name == "TiH"

    def test_type_attrs_minimal(self) -> None:
        """Type attrs with elem and shape only (no layout/strides)."""
        src = """let X = region(X_L2, 0, 100)
elem=i8, shape=[1,2,3]"""
        ast = parse_ok(src)
        region = ast.statements[0]
        attrs = region.type_attrs
        assert attrs is not None
        assert attrs.elem == "i8"
        assert len(attrs.shape) == 3
        assert attrs.layout is None
        assert attrs.strides is None


# ---------------------------------------------------------------------------
# Quantization Descriptors
# ---------------------------------------------------------------------------


class TestQuantDescriptors:
    def test_per_tensor_quant(self) -> None:
        src = """let X = region(X_L2, 0, 100)
elem=i8, shape=[1,2,3], layout=NHWC, quant=per_tensor(scale=0.5, zero_point=0)"""
        ast = parse_ok(src)
        region = ast.statements[0]
        assert isinstance(region, RegionDeclNode)
        attrs = region.type_attrs
        assert attrs is not None
        assert attrs.quant is not None
        assert isinstance(attrs.quant, PerTensorQuantNode)
        assert isinstance(attrs.quant.scale, FloatLiteral)
        assert attrs.quant.scale.value == pytest.approx(0.5)
        assert isinstance(attrs.quant.zero_point, IntLiteral)
        assert attrs.quant.zero_point.value == 0

    def test_per_channel_quant(self) -> None:
        src = (
            "let X = region(X_L2, 0, 100)\n"
            "elem=i8, shape=[1,2,3], layout=NHWC, "
            "quant=per_channel(axis=0, scales=[0.5, 0.6], zero_points=[0, 1])"
        )
        ast = parse_ok(src)
        region = ast.statements[0]
        attrs = region.type_attrs
        assert attrs is not None
        assert attrs.quant is not None
        assert isinstance(attrs.quant, PerChannelQuantNode)
        assert isinstance(attrs.quant.axis, IntLiteral)
        assert attrs.quant.axis.value == 0
        assert len(attrs.quant.scales) == 2
        assert len(attrs.quant.zero_points) == 2

    def test_per_group_quant(self) -> None:
        src = (
            "let X = region(X_L2, 0, 100)\n"
            "elem=i8, shape=[1,2,3], layout=NHWC, "
            "quant=per_group(axis=0, group_size=4, "
            "scales=[0.5, 0.6], zero_points=[0, 1])"
        )
        ast = parse_ok(src)
        region = ast.statements[0]
        attrs = region.type_attrs
        assert attrs is not None
        assert attrs.quant is not None
        assert isinstance(attrs.quant, PerGroupQuantNode)
        assert isinstance(attrs.quant.axis, IntLiteral)
        assert attrs.quant.axis.value == 0
        assert isinstance(attrs.quant.group_size, IntLiteral)
        assert attrs.quant.group_size.value == 4
        assert len(attrs.quant.scales) == 2
        assert len(attrs.quant.zero_points) == 2


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------


class TestDecorators:
    def test_simple_decorator(self) -> None:
        ast = parse_ok("buffer X : L2 (size=1024) @materialized")
        buf = ast.statements[0]
        assert isinstance(buf, BufferDeclNode)
        assert len(buf.decorators) == 1
        deco = buf.decorators[0]
        assert deco.name == "materialized"
        assert deco.args is None

    def test_decorator_with_int_arg(self) -> None:
        ast = parse_ok("buffer X : L2 (size=1024) @max_in_flight(2)")
        buf = ast.statements[0]
        deco = buf.decorators[0]
        assert deco.name == "max_in_flight"
        assert deco.args is not None
        assert len(deco.args) == 1
        assert isinstance(deco.args[0], IntLiteral)

    def test_decorator_with_multiple_args(self) -> None:
        ast = parse_ok('buffer X : L2 (size=1024) @config(1, "mode")')
        buf = ast.statements[0]
        deco = buf.decorators[0]
        assert deco.name == "config"
        assert deco.args is not None
        assert len(deco.args) == 2

    def test_multiple_decorators_same_line(self) -> None:
        src = "buffer X : L2 (size=1024) @readonly @materialized"
        ast = parse_ok(src)
        buf = ast.statements[0]
        assert len(buf.decorators) == 2
        assert buf.decorators[0].name == "readonly"
        assert buf.decorators[1].name == "materialized"

    def test_decorators_on_continuation_lines(self) -> None:
        src = """buffer X : L2 (size=1024)
@readonly
@materialized"""
        ast = parse_ok(src)
        buf = ast.statements[0]
        assert len(buf.decorators) == 2

    def test_decorators_on_region(self) -> None:
        src = """let X = region(X_L2, 0, 100)
@materialized
@readonly"""
        ast = parse_ok(src)
        region = ast.statements[0]
        assert isinstance(region, RegionDeclNode)
        assert len(region.decorators) == 2
        assert region.decorators[0].name == "materialized"
        assert region.decorators[1].name == "readonly"


# ---------------------------------------------------------------------------
# Value Parsing
# ---------------------------------------------------------------------------


class TestValueParsing:
    def test_string_literal(self) -> None:
        ast = parse_ok('let s = "hello world"')
        let = ast.statements[0]
        assert isinstance(let, LetDeclNode)
        assert isinstance(let.value, StringLiteral)
        assert let.value.value == "hello world"

    def test_empty_string(self) -> None:
        ast = parse_ok('let s = ""')
        let = ast.statements[0]
        assert isinstance(let.value, StringLiteral)
        assert let.value.value == ""

    def test_empty_array(self) -> None:
        ast = parse_ok("let arr = []")
        let = ast.statements[0]
        assert isinstance(let.value, ArrayLiteral)
        assert len(let.value.elements) == 0

    def test_array_with_trailing_comma(self) -> None:
        ast = parse_ok("let arr = [1, 2, 3,]")
        let = ast.statements[0]
        assert isinstance(let.value, ArrayLiteral)
        assert len(let.value.elements) == 3

    def test_nested_array(self) -> None:
        ast = parse_ok("let mat = [[1, 2], [3, 4]]")
        let = ast.statements[0]
        arr = let.value
        assert isinstance(arr, ArrayLiteral)
        assert len(arr.elements) == 2
        assert isinstance(arr.elements[0], ArrayLiteral)
        assert isinstance(arr.elements[1], ArrayLiteral)
        assert len(arr.elements[0].elements) == 2
        assert len(arr.elements[1].elements) == 2

    def test_deeply_nested_array(self) -> None:
        ast = parse_ok("let tensor = [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]")
        let = ast.statements[0]
        arr = let.value
        assert isinstance(arr, ArrayLiteral)
        assert len(arr.elements) == 2

    def test_mixed_array(self) -> None:
        ast = parse_ok('let mixed = [1, "hello", 3.14]')
        let = ast.statements[0]
        arr = let.value
        assert isinstance(arr, ArrayLiteral)
        assert len(arr.elements) == 3
        assert isinstance(arr.elements[0], IntLiteral)
        assert isinstance(arr.elements[1], StringLiteral)
        assert isinstance(arr.elements[2], FloatLiteral)


# ---------------------------------------------------------------------------
# Mixed Programs
# ---------------------------------------------------------------------------


class TestMixedPrograms:
    def test_const_and_buffer(self) -> None:
        src = """const SIZE = 1024
buffer X : DDR (size=SIZE)"""
        ast = parse_ok(src)
        assert len(ast.statements) == 2
        assert isinstance(ast.statements[0], ConstDeclNode)
        assert isinstance(ast.statements[1], BufferDeclNode)

    def test_buffer_and_region(self) -> None:
        src = """buffer X_L2 : L2 (size=1024)
let X = region(X_L2, 0, 100)"""
        ast = parse_ok(src)
        assert len(ast.statements) == 2
        assert isinstance(ast.statements[0], BufferDeclNode)
        assert isinstance(ast.statements[1], RegionDeclNode)

    def test_all_statement_types_interleaved(self) -> None:
        src = """const SIZE = 1024
buffer X_L2 : L2 (size=SIZE)
let offset = 0
let X = region(X_L2, offset, 100)
const ALIGN = 64"""
        ast = parse_ok(src)
        assert len(ast.statements) == 5
        assert isinstance(ast.statements[0], ConstDeclNode)
        assert isinstance(ast.statements[1], BufferDeclNode)
        assert isinstance(ast.statements[2], LetDeclNode)
        assert isinstance(ast.statements[3], RegionDeclNode)
        assert isinstance(ast.statements[4], ConstDeclNode)

    def test_full_program_with_headers(self) -> None:
        src = """device "matmul.cfg"
program MatMul:

const M = 128
const N = 256

buffer A_L2 : L2 (size=M * N, align=64) @materialized
buffer B_L1 : L1[0] (size=256, align=64)

let A_tile = region(A_L2, 0, M * N)
elem=f32, shape=[M, N], layout=RowMajor

let offset = 0
"""
        ast = parse_ok(src)
        assert ast.device_ref == "matmul.cfg"
        assert ast.name == "MatMul"
        assert len(ast.statements) == 6
        assert isinstance(ast.statements[0], ConstDeclNode)
        assert isinstance(ast.statements[1], ConstDeclNode)
        assert isinstance(ast.statements[2], BufferDeclNode)
        assert isinstance(ast.statements[3], BufferDeclNode)
        assert isinstance(ast.statements[4], RegionDeclNode)
        assert isinstance(ast.statements[5], LetDeclNode)


# ---------------------------------------------------------------------------
# Multi-line Continuation
# ---------------------------------------------------------------------------


class TestMultiLineContinuation:
    def test_type_attrs_on_continuation_line(self) -> None:
        src = """let X = region(X_L2, 0, 100)
elem=i8, shape=[1,2,3], layout=NHWC"""
        ast = parse_ok(src)
        region = ast.statements[0]
        assert isinstance(region, RegionDeclNode)
        assert region.type_attrs is not None

    def test_decorators_on_continuation_line(self) -> None:
        src = """buffer X : L2 (size=1024)
@materialized"""
        ast = parse_ok(src)
        buf = ast.statements[0]
        assert isinstance(buf, BufferDeclNode)
        assert len(buf.decorators) == 1

    def test_type_attrs_and_decorators_on_separate_lines(self) -> None:
        src = """let X = region(X_L2, 0, 100)
elem=i8, shape=[1,2,3], layout=NHWC
@materialized
@readonly"""
        ast = parse_ok(src)
        region = ast.statements[0]
        assert isinstance(region, RegionDeclNode)
        assert region.type_attrs is not None
        assert len(region.decorators) == 2

    def test_multiple_continuation_lines(self) -> None:
        src = """let X = region(X_L2, 0, 100)
elem=i8, shape=[1,2,3], layout=NHWC, quant=per_tensor(scale=0.5, zero_point=0)
@materialized
@readonly
@max_in_flight(2)"""
        ast = parse_ok(src)
        region = ast.statements[0]
        assert isinstance(region, RegionDeclNode)
        assert region.type_attrs is not None
        assert region.type_attrs.quant is not None
        assert len(region.decorators) == 3


# ---------------------------------------------------------------------------
# Error Cases
# ---------------------------------------------------------------------------


class TestErrorCases:
    def test_buffer_missing_colon(self) -> None:
        _, diag = parse("buffer X DDR (size=1024)")
        assert diag.has_errors()

    def test_buffer_invalid_memory_level(self) -> None:
        _, diag = parse("buffer X : L3 (size=1024)")
        assert diag.has_errors()

    def test_buffer_missing_lparen(self) -> None:
        _, diag = parse("buffer X : DDR size=1024)")
        assert diag.has_errors()

    def test_region_missing_buffer_name(self) -> None:
        _, diag = parse("let X = region(, 0, 100)")
        assert diag.has_errors()

    def test_region_missing_comma_after_buffer(self) -> None:
        _, diag = parse("let X = region(X_L2 0 100)")
        assert diag.has_errors()

    def test_type_attrs_invalid_elem_type(self) -> None:
        src = """let X = region(X_L2, 0, 100)
elem=int32, shape=[1,2,3]"""
        _, diag = parse(src)
        assert diag.has_errors()

    def test_type_attrs_missing_equals_after_elem(self) -> None:
        src = """let X = region(X_L2, 0, 100)
elem i8, shape=[1,2,3]"""
        _, diag = parse(src)
        assert diag.has_errors()

    def test_quant_unknown_descriptor_kind(self) -> None:
        src = """let X = region(X_L2, 0, 100)
elem=i8, shape=[1,2,3], layout=NHWC, quant=per_block(scale=0.5)"""
        _, diag = parse(src)
        assert diag.has_errors()

    def test_decorator_missing_name(self) -> None:
        _, diag = parse("buffer X : L2 (size=1024) @")
        assert diag.has_errors()

    def test_buffer_unclosed_paren(self) -> None:
        _, diag = parse("buffer X : DDR (size=1024")
        assert diag.has_errors()

    def test_region_unclosed_paren(self) -> None:
        _, diag = parse("let X = region(X_L2, 0, 100")
        assert diag.has_errors()

    def test_array_unclosed_bracket(self) -> None:
        _, diag = parse("let arr = [1, 2, 3")
        assert diag.has_errors()

    def test_error_recovery_continues_to_next_statement(self) -> None:
        """After an error, the parser should recover and parse subsequent statements."""
        src = """buffer BAD DDR (size=1024)
buffer GOOD : L2 (size=512)"""
        ast, diag = parse(src)
        assert diag.has_errors()
        # Should recover and parse GOOD
        names = [s.name for s in ast.statements if isinstance(s, BufferDeclNode)]
        assert "GOOD" in names


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_realistic_matmul_program(self) -> None:
        src = """device "matmul_device.cfg"
program MatMul:

# Matrix dimensions
const M = 128
const N = 256
const K = 64

# Tile sizes
const TILE_M = 32
const TILE_N = 64

# Compute buffer sizes
const A_SIZE = M * K
const B_SIZE = K * N
const C_SIZE = M * N

# DDR buffers
buffer A_DDR : DDR (size=A_SIZE * 4, align=64) @readonly
buffer B_DDR : DDR (size=B_SIZE * 4, align=64) @readonly
buffer C_DDR : DDR (size=C_SIZE * 4, align=64)

# L2 buffers
buffer A_L2 : L2 (size=TILE_M * K * 4, align=64)
buffer B_L2 : L2 (size=K * TILE_N * 4, align=64)
buffer C_L2 : L2 (size=TILE_M * TILE_N * 4, align=64)

# L1 buffers
buffer A_L1 : L1[0] (size=TILE_M * K * 4, align=64) @resource(DMA[0])
buffer B_L1 : L1[1] (size=K * TILE_N * 4, align=64) @resource(DMA[1])

# Regions
let A_tile = region(A_L2, 0, TILE_M * K * 4)
elem=f32, shape=[TILE_M, K], layout=RowMajor

let B_tile = region(B_L2, 0, K * TILE_N * 4)
elem=f32, shape=[K, TILE_N], layout=RowMajor

let C_tile = region(C_L2, 0, TILE_M * TILE_N * 4)
elem=f32, shape=[TILE_M, TILE_N], layout=RowMajor
@materialized

# Simple lets
let offset = 0
let stride = TILE_M * 4
"""
        ast = parse_ok(src)
        assert ast.device_ref == "matmul_device.cfg"
        assert ast.name == "MatMul"

        # Count statement types
        const_count = sum(1 for s in ast.statements if isinstance(s, ConstDeclNode))
        buffer_count = sum(1 for s in ast.statements if isinstance(s, BufferDeclNode))
        region_count = sum(1 for s in ast.statements if isinstance(s, RegionDeclNode))
        let_count = sum(1 for s in ast.statements if isinstance(s, LetDeclNode))

        assert const_count == 8  # 8 const declarations
        assert buffer_count == 8  # 8 buffer declarations
        assert region_count == 3  # 3 region declarations
        assert let_count == 2  # 2 simple let declarations

    def test_quantized_conv_program(self) -> None:
        src = """program QuantizedConv:

const IH = 56
const IW = 56
const IC = 64
const OC = 128

buffer Input_L2 : L2 (size=IH * IW * IC, align=64)
buffer Weight_L2 : L2 (size=3 * 3 * IC * OC, align=64) @readonly
buffer Output_L2 : L2 (size=IH * IW * OC, align=64)

let Input = region(Input_L2, 0, IH * IW * IC)
elem=i8, shape=[1, IH, IW, IC], layout=NHWC, quant=per_tensor(scale=0.5, zero_point=128)

let Weight = region(Weight_L2, 0, 3 * 3 * IC * OC)
elem=i8, shape=[OC, IC], layout=OIHW, quant=per_channel(axis=0, scales=[0.1], zero_points=[0])

let Output = region(Output_L2, 0, IH * IW * OC)
elem=i8, shape=[1, IH, IW, OC], layout=NHWC, quant=per_tensor(scale=0.25, zero_point=0)
@materialized
"""
        ast = parse_ok(src)
        assert ast.name == "QuantizedConv"

        # Verify quantization descriptors are parsed correctly
        regions = [s for s in ast.statements if isinstance(s, RegionDeclNode)]
        assert len(regions) == 3

        # Input has per_tensor quant
        assert regions[0].type_attrs is not None
        assert isinstance(regions[0].type_attrs.quant, PerTensorQuantNode)

        # Weight has per_channel quant
        assert regions[1].type_attrs is not None
        assert isinstance(regions[1].type_attrs.quant, PerChannelQuantNode)

        # Output has per_tensor quant and materialized decorator
        assert regions[2].type_attrs is not None
        assert isinstance(regions[2].type_attrs.quant, PerTensorQuantNode)
        assert len(regions[2].decorators) == 1
        assert regions[2].decorators[0].name == "materialized"
