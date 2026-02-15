from __future__ import annotations

import pytest

from nemlib.core import (
    BinaryOp,
    ConstEvalError,
    FloatLiteral,
    Identifier,
    IntLiteral,
    ParenExpr,
    UnaryOp,
    evaluate_const_expr,
)
from nemlib.diagnostics import SourceLocation


class TestExpressionNodes:
    def test_int_literal_creation(self):
        expr = IntLiteral(42)
        assert expr.value == 42
        assert expr.location is None

    def test_int_literal_with_location(self):
        loc = SourceLocation("test.nem", 1, 5)
        expr = IntLiteral(42, location=loc)
        assert expr.value == 42
        assert expr.location == loc

    def test_float_literal_creation(self):
        expr = FloatLiteral(3.14)
        assert expr.value == 3.14

    def test_identifier_creation(self):
        expr = Identifier("X")
        assert expr.name == "X"

    def test_binary_op_creation(self):
        left = IntLiteral(2)
        right = IntLiteral(3)
        expr = BinaryOp("+", left, right)
        assert expr.op == "+"
        assert expr.left == left
        assert expr.right == right

    def test_unary_op_creation(self):
        operand = IntLiteral(5)
        expr = UnaryOp("-", operand)
        assert expr.op == "-"
        assert expr.operand == operand

    def test_paren_expr_creation(self):
        inner = IntLiteral(42)
        expr = ParenExpr(inner)
        assert expr.expr == inner

    def test_nodes_are_frozen(self):
        expr = IntLiteral(42)
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            expr.value = 100


class TestConstEvaluator:
    def test_int_literal(self):
        expr = IntLiteral(42)
        assert evaluate_const_expr(expr, {}) == 42

    def test_identifier_from_env(self):
        expr = Identifier("X")
        env = {"X": 10}
        assert evaluate_const_expr(expr, env) == 10

    def test_identifier_undefined(self):
        expr = Identifier("UNDEFINED")
        with pytest.raises(ConstEvalError) as exc_info:
            evaluate_const_expr(expr, {})
        assert "UNDEFINED" in str(exc_info.value)

    def test_addition(self):
        expr = BinaryOp("+", IntLiteral(2), IntLiteral(3))
        assert evaluate_const_expr(expr, {}) == 5

    def test_subtraction(self):
        expr = BinaryOp("-", IntLiteral(10), IntLiteral(3))
        assert evaluate_const_expr(expr, {}) == 7

    def test_multiplication(self):
        expr = BinaryOp("*", IntLiteral(4), IntLiteral(5))
        assert evaluate_const_expr(expr, {}) == 20

    def test_division(self):
        expr = BinaryOp("/", IntLiteral(20), IntLiteral(4))
        assert evaluate_const_expr(expr, {}) == 5

    def test_division_truncates_toward_zero_positive(self):
        expr = BinaryOp("/", IntLiteral(7), IntLiteral(3))
        assert evaluate_const_expr(expr, {}) == 2

    def test_division_truncates_toward_zero_negative(self):
        # -7 / 3 should be -2 (truncate toward zero), not -3 (floor)
        expr = BinaryOp("/", UnaryOp("-", IntLiteral(7)), IntLiteral(3))
        assert evaluate_const_expr(expr, {}) == -2

    def test_modulo(self):
        expr = BinaryOp("mod", IntLiteral(17), IntLiteral(5))
        assert evaluate_const_expr(expr, {}) == 2

    def test_division_by_zero(self):
        expr = BinaryOp("/", IntLiteral(10), IntLiteral(0))
        with pytest.raises(ConstEvalError) as exc_info:
            evaluate_const_expr(expr, {})
        assert "zero" in str(exc_info.value).lower()

    def test_modulo_by_zero(self):
        expr = BinaryOp("mod", IntLiteral(10), IntLiteral(0))
        with pytest.raises(ConstEvalError) as exc_info:
            evaluate_const_expr(expr, {})
        assert "zero" in str(exc_info.value).lower()

    def test_unary_minus(self):
        expr = UnaryOp("-", IntLiteral(5))
        assert evaluate_const_expr(expr, {}) == -5

    def test_nested_expression(self):
        # (2 + 3) * 4 = 20
        inner = BinaryOp("+", IntLiteral(2), IntLiteral(3))
        expr = BinaryOp("*", ParenExpr(inner), IntLiteral(4))
        assert evaluate_const_expr(expr, {}) == 20

    def test_operator_precedence(self):
        # 2 + 3 * 4 = 14 (if parsed correctly with precedence)
        # But this test constructs the tree manually, so we test explicit nesting
        # Let's test: 2 + (3 * 4) = 14
        mult = BinaryOp("*", IntLiteral(3), IntLiteral(4))
        expr = BinaryOp("+", IntLiteral(2), mult)
        assert evaluate_const_expr(expr, {}) == 14

    def test_complex_with_env(self):
        # X * Y + Z with env = {"X": 2, "Y": 3, "Z": 4}
        # Result: 2 * 3 + 4 = 10
        mult = BinaryOp("*", Identifier("X"), Identifier("Y"))
        expr = BinaryOp("+", mult, Identifier("Z"))
        env = {"X": 2, "Y": 3, "Z": 4}
        assert evaluate_const_expr(expr, env) == 10

    def test_float_literal_raises_error(self):
        expr = FloatLiteral(3.14)
        with pytest.raises(ConstEvalError):
            evaluate_const_expr(expr, {})

    def test_parenthesized_expression(self):
        # Just a literal in parens: (42)
        expr = ParenExpr(IntLiteral(42))
        assert evaluate_const_expr(expr, {}) == 42
