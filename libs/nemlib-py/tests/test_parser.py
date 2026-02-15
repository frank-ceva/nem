"""Tests for the NEM parser."""

from __future__ import annotations

import pytest

from nemlib.core.expressions import (
    BinaryOp,
    FloatLiteral,
    Identifier,
    IntLiteral,
    ParenExpr,
    UnaryOp,
)
from nemlib.diagnostics.collector import DiagnosticCollector
from nemlib.parser.ast_nodes import ConstDeclNode, ProgramNode
from nemlib.parser.parser import parse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_ok(source: str) -> ProgramNode:
    """Parse *source* and assert no errors."""
    ast, diag = parse(source, "<test>")
    assert not diag.has_errors(), diag.format_all()
    return ast


def parse_expr(source: str):
    """Parse a single ``const X = <expr>`` and return the expression node."""
    ast = parse_ok(f"const X = {source}")
    assert len(ast.statements) == 1
    return ast.statements[0].value


# ---------------------------------------------------------------------------
# Program headers
# ---------------------------------------------------------------------------


class TestProgramHeaders:
    def test_device_header(self) -> None:
        ast = parse_ok('device "my_device.cfg"')
        assert ast.device_ref == "my_device.cfg"
        assert ast.name is None
        assert ast.statements == ()

    def test_program_header(self) -> None:
        ast = parse_ok("program MatMul:")
        assert ast.device_ref is None
        assert ast.name == "MatMul"
        assert ast.statements == ()

    def test_both_headers(self) -> None:
        src = 'device "hw.cfg"\nprogram MyProg:'
        ast = parse_ok(src)
        assert ast.device_ref == "hw.cfg"
        assert ast.name == "MyProg"

    def test_no_headers(self) -> None:
        ast = parse_ok("const X = 1")
        assert ast.device_ref is None
        assert ast.name is None
        assert len(ast.statements) == 1

    def test_empty_program(self) -> None:
        ast = parse_ok("")
        assert ast.device_ref is None
        assert ast.name is None
        assert ast.statements == ()

    def test_only_comments_and_blank_lines(self) -> None:
        ast = parse_ok("# comment\n\n# another\n")
        assert ast.statements == ()


# ---------------------------------------------------------------------------
# Const declarations
# ---------------------------------------------------------------------------


class TestConstDecl:
    def test_simple_const(self) -> None:
        ast = parse_ok("const WIDTH = 128")
        assert len(ast.statements) == 1
        decl = ast.statements[0]
        assert isinstance(decl, ConstDeclNode)
        assert decl.name == "WIDTH"
        assert isinstance(decl.value, IntLiteral)
        assert decl.value.value == 128

    def test_multiple_consts(self) -> None:
        src = "const A = 1\nconst B = 2\nconst C = 3"
        ast = parse_ok(src)
        assert len(ast.statements) == 3
        names = [s.name for s in ast.statements]
        assert names == ["A", "B", "C"]

    def test_const_with_expression(self) -> None:
        ast = parse_ok("const AREA = W * H")
        decl = ast.statements[0]
        assert isinstance(decl.value, BinaryOp)
        assert decl.value.op == "*"

    def test_const_location(self) -> None:
        ast = parse_ok("const X = 42")
        assert ast.statements[0].location is not None
        assert ast.statements[0].location.line == 1


# ---------------------------------------------------------------------------
# Expression parsing — literals
# ---------------------------------------------------------------------------


class TestExprLiterals:
    def test_int_literal(self) -> None:
        expr = parse_expr("42")
        assert isinstance(expr, IntLiteral)
        assert expr.value == 42

    def test_zero(self) -> None:
        expr = parse_expr("0")
        assert isinstance(expr, IntLiteral)
        assert expr.value == 0

    def test_float_literal(self) -> None:
        expr = parse_expr("3.14")
        assert isinstance(expr, FloatLiteral)
        assert expr.value == pytest.approx(3.14)

    def test_float_with_exponent(self) -> None:
        expr = parse_expr("1.0e-5")
        assert isinstance(expr, FloatLiteral)
        assert expr.value == pytest.approx(1.0e-5)

    def test_identifier(self) -> None:
        expr = parse_expr("WIDTH")
        assert isinstance(expr, Identifier)
        assert expr.name == "WIDTH"


# ---------------------------------------------------------------------------
# Expression parsing — binary operators
# ---------------------------------------------------------------------------


class TestExprBinaryOps:
    def test_addition(self) -> None:
        expr = parse_expr("1 + 2")
        assert isinstance(expr, BinaryOp)
        assert expr.op == "+"
        assert isinstance(expr.left, IntLiteral) and expr.left.value == 1
        assert isinstance(expr.right, IntLiteral) and expr.right.value == 2

    def test_subtraction(self) -> None:
        expr = parse_expr("10 - 3")
        assert isinstance(expr, BinaryOp)
        assert expr.op == "-"

    def test_multiplication(self) -> None:
        expr = parse_expr("4 * 5")
        assert isinstance(expr, BinaryOp)
        assert expr.op == "*"

    def test_division(self) -> None:
        expr = parse_expr("8 / 2")
        assert isinstance(expr, BinaryOp)
        assert expr.op == "/"

    def test_mod(self) -> None:
        expr = parse_expr("7 mod 3")
        assert isinstance(expr, BinaryOp)
        assert expr.op == "mod"

    def test_precedence_mul_over_add(self) -> None:
        """``1 + 2 * 3`` should parse as ``1 + (2 * 3)``."""
        expr = parse_expr("1 + 2 * 3")
        assert isinstance(expr, BinaryOp)
        assert expr.op == "+"
        assert isinstance(expr.left, IntLiteral) and expr.left.value == 1
        assert isinstance(expr.right, BinaryOp) and expr.right.op == "*"

    def test_left_associativity(self) -> None:
        """``1 - 2 - 3`` should parse as ``(1 - 2) - 3``."""
        expr = parse_expr("1 - 2 - 3")
        assert isinstance(expr, BinaryOp)
        assert expr.op == "-"
        assert isinstance(expr.left, BinaryOp)
        assert expr.left.op == "-"
        assert isinstance(expr.right, IntLiteral) and expr.right.value == 3

    def test_complex_expression(self) -> None:
        """``A * B + C * D`` -> ``(A * B) + (C * D)``."""
        expr = parse_expr("A * B + C * D")
        assert isinstance(expr, BinaryOp) and expr.op == "+"
        assert isinstance(expr.left, BinaryOp) and expr.left.op == "*"
        assert isinstance(expr.right, BinaryOp) and expr.right.op == "*"


# ---------------------------------------------------------------------------
# Expression parsing — unary and parentheses
# ---------------------------------------------------------------------------


class TestExprUnaryAndParens:
    def test_unary_minus(self) -> None:
        expr = parse_expr("-5")
        assert isinstance(expr, UnaryOp)
        assert expr.op == "-"
        assert isinstance(expr.operand, IntLiteral) and expr.operand.value == 5

    def test_double_unary(self) -> None:
        expr = parse_expr("--x")
        assert isinstance(expr, UnaryOp)
        assert isinstance(expr.operand, UnaryOp)
        assert isinstance(expr.operand.operand, Identifier)

    def test_parentheses(self) -> None:
        expr = parse_expr("(1 + 2)")
        assert isinstance(expr, ParenExpr)
        assert isinstance(expr.expr, BinaryOp) and expr.expr.op == "+"

    def test_parens_override_precedence(self) -> None:
        """``(1 + 2) * 3`` -> ``(1 + 2) * 3`` not ``1 + (2 * 3)``."""
        expr = parse_expr("(1 + 2) * 3")
        assert isinstance(expr, BinaryOp) and expr.op == "*"
        assert isinstance(expr.left, ParenExpr)

    def test_nested_parens(self) -> None:
        expr = parse_expr("((42))")
        assert isinstance(expr, ParenExpr)
        assert isinstance(expr.expr, ParenExpr)
        assert isinstance(expr.expr.expr, IntLiteral)


# ---------------------------------------------------------------------------
# Skipping unknown statements
# ---------------------------------------------------------------------------


class TestSkipUnknown:
    def test_skip_unknown_stmt(self) -> None:
        """Unknown top-level statements are skipped; known decls still parsed."""
        src = "store A\nconst X = 1\nemit foo\nconst Y = 2"
        ast = parse_ok(src)
        assert len(ast.statements) == 2
        assert ast.statements[0].name == "X"
        assert ast.statements[1].name == "Y"

    def test_skip_all_unknown(self) -> None:
        src = "store x\nemit B"
        ast = parse_ok(src)
        assert ast.statements == ()


# ---------------------------------------------------------------------------
# Full programs
# ---------------------------------------------------------------------------


class TestFullProgram:
    def test_complete_program(self) -> None:
        src = """\
device "matmul_device.cfg"
program MatMul:

# Tensor dimensions
const M = 128
const N = 256
const K = 64

# Derived constants
const TILE_M = M / 4
const TOTAL = M * N
"""
        ast = parse_ok(src)
        assert ast.device_ref == "matmul_device.cfg"
        assert ast.name == "MatMul"
        assert len(ast.statements) == 5
        assert ast.statements[0].name == "M"
        assert ast.statements[4].name == "TOTAL"

    def test_program_without_device(self) -> None:
        src = "program Simple:\nconst A = 10"
        ast = parse_ok(src)
        assert ast.device_ref is None
        assert ast.name == "Simple"
        assert len(ast.statements) == 1

    def test_program_with_mixed_statements(self) -> None:
        """Parser should handle const decls interleaved with unknown stmts."""
        src = """\
const A = 1
store X
const B = A + 1
emit Y
const C = B * 2
"""
        ast = parse_ok(src)
        assert len(ast.statements) == 3
        names = [s.name for s in ast.statements]
        assert names == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestParserErrors:
    def test_missing_equals_in_const(self) -> None:
        _, diag = parse("const X 42")
        assert diag.has_errors()

    def test_missing_expression_in_const(self) -> None:
        _, diag = parse("const X =")
        assert diag.has_errors()

    def test_missing_name_in_const(self) -> None:
        _, diag = parse("const = 42")
        assert diag.has_errors()

    def test_unclosed_paren(self) -> None:
        _, diag = parse("const X = (1 + 2")
        assert diag.has_errors()

    def test_error_recovery_continues(self) -> None:
        """After an error in one const, subsequent consts should still parse."""
        src = "const BAD\nconst GOOD = 42"
        ast, diag = parse(src)
        assert diag.has_errors()
        # The parser should recover and parse GOOD
        names = [s.name for s in ast.statements]
        assert "GOOD" in names


# ---------------------------------------------------------------------------
# Convenience parse() function
# ---------------------------------------------------------------------------


class TestParseFunction:
    def test_returns_tuple(self) -> None:
        result = parse("const X = 1")
        assert isinstance(result, tuple)
        assert len(result) == 2
        ast, diag = result
        assert isinstance(ast, ProgramNode)
        assert isinstance(diag, DiagnosticCollector)

    def test_filename_propagated(self) -> None:
        ast, _ = parse("const X = 1", "myfile.nem")
        # Location should reflect the filename
        assert ast.statements[0].location is not None
        assert ast.statements[0].location.file == "myfile.nem"
