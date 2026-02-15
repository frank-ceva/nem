"""Expression AST nodes and constant expression evaluator for NEM."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass

from nemlib.diagnostics.location import SourceLocation


class ExprNode(ABC):
    """Base type for expression nodes. All concrete subclasses are frozen dataclasses."""


@dataclass(frozen=True)
class IntLiteral(ExprNode):
    """Integer literal: 42, 0, 1000000."""

    value: int
    location: SourceLocation | None = None


@dataclass(frozen=True)
class FloatLiteral(ExprNode):
    """Float literal: 1.0, 0.00001, 1.0e-5. Only valid in compute attributes."""

    value: float
    location: SourceLocation | None = None


@dataclass(frozen=True)
class Identifier(ExprNode):
    """Identifier reference: variable name, constant name."""

    name: str
    location: SourceLocation | None = None


@dataclass(frozen=True)
class BinaryOp(ExprNode):
    """Binary operation: left op right. Op is one of +, -, *, /, mod."""

    op: str
    left: ExprNode
    right: ExprNode
    location: SourceLocation | None = None


@dataclass(frozen=True)
class UnaryOp(ExprNode):
    """Unary operation: -operand."""

    op: str
    operand: ExprNode
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ParenExpr(ExprNode):
    """Parenthesized expression: (expr)."""

    expr: ExprNode
    location: SourceLocation | None = None


class ConstEvalError(Exception):
    """Raised when constant expression evaluation fails."""

    def __init__(self, message: str, location: SourceLocation | None = None) -> None:
        super().__init__(message)
        self.location = location


def evaluate_const_expr(expr: ExprNode, env: dict[str, int]) -> int:
    """
    Evaluate a constant integer expression.

    Args:
        expr: The expression to evaluate.
        env: Variable environment mapping names to integer values.

    Returns:
        The integer result.

    Raises:
        ConstEvalError: If evaluation fails (unknown variable, division by zero, etc.)
    """
    if isinstance(expr, IntLiteral):
        return expr.value
    elif isinstance(expr, Identifier):
        if expr.name not in env:
            raise ConstEvalError(
                f"Forward reference to undeclared constant {expr.name}",
                expr.location,
            )
        return env[expr.name]
    elif isinstance(expr, BinaryOp):
        left = evaluate_const_expr(expr.left, env)
        right = evaluate_const_expr(expr.right, env)
        if expr.op == "+":
            return left + right
        elif expr.op == "-":
            return left - right
        elif expr.op == "*":
            return left * right
        elif expr.op == "/":
            if right == 0:
                raise ConstEvalError("Division by zero in constant expression", expr.location)
            # Integer division truncates toward zero (per NEM spec)
            return int(left / right)
        elif expr.op == "mod":
            if right == 0:
                raise ConstEvalError("Division by zero in constant expression", expr.location)
            return left % right
        else:
            raise ConstEvalError(f"Unknown operator: {expr.op!r}", expr.location)
    elif isinstance(expr, UnaryOp):
        operand = evaluate_const_expr(expr.operand, env)
        if expr.op == "-":
            return -operand
        else:
            raise ConstEvalError(f"Unknown unary operator: {expr.op!r}", expr.location)
    elif isinstance(expr, ParenExpr):
        return evaluate_const_expr(expr.expr, env)
    elif isinstance(expr, FloatLiteral):
        raise ConstEvalError("Float literals not allowed in constant expressions", expr.location)
    else:
        raise ConstEvalError(
            f"Cannot evaluate expression type: {type(expr).__name__}",
            getattr(expr, "location", None),
        )
