"""AST node types for the NEM parser.

Expression nodes are defined in ``nemlib.core.expressions`` and re-exported
here for convenience.  This module adds statement- and program-level nodes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from nemlib.core.expressions import (
    BinaryOp,
    ExprNode,
    FloatLiteral,
    Identifier,
    IntLiteral,
    ParenExpr,
    UnaryOp,
)
from nemlib.diagnostics.location import SourceLocation

# Re-export expression nodes so consumers can import everything from
# ``nemlib.parser.ast_nodes``.
__all__ = [
    # Expression nodes (re-exported from core)
    "ExprNode",
    "IntLiteral",
    "FloatLiteral",
    "Identifier",
    "BinaryOp",
    "UnaryOp",
    "ParenExpr",
    # Value nodes
    "StringLiteral",
    "ArrayLiteral",
    # Quantization descriptors
    "QuantDescNode",
    "PerTensorQuantNode",
    "PerChannelQuantNode",
    "PerGroupQuantNode",
    # Type attributes
    "TypeAttrsNode",
    # Decorator
    "DecoratorNode",
    # Statement nodes
    "ConstDeclNode",
    "BufferDeclNode",
    "RegionDeclNode",
    "LetDeclNode",
    # Statement union
    "StmtNode",
    # Program node
    "ProgramNode",
]


# ---------------------------------------------------------------------------
# Value nodes (extend ExprNode for uniform AST)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StringLiteral(ExprNode):
    """String literal value (used in value positions, e.g. decorator args)."""

    value: str
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ArrayLiteral(ExprNode):
    """Array literal: ``[val, val, ...]``."""

    elements: tuple[ExprNode, ...]
    location: SourceLocation | None = None


# ---------------------------------------------------------------------------
# Quantization descriptors
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PerTensorQuantNode:
    """``per_tensor(scale=VAL, zero_point=VAL)``."""

    scale: ExprNode
    zero_point: ExprNode
    location: SourceLocation | None = None


@dataclass(frozen=True)
class PerChannelQuantNode:
    """``per_channel(axis=INT, scales=[...], zero_points=[...])``."""

    axis: ExprNode
    scales: tuple[ExprNode, ...]
    zero_points: tuple[ExprNode, ...]
    location: SourceLocation | None = None


@dataclass(frozen=True)
class PerGroupQuantNode:
    """``per_group(axis=INT, group_size=INT, scales=[...], zero_points=[...])``."""

    axis: ExprNode
    group_size: ExprNode
    scales: tuple[ExprNode, ...]
    zero_points: tuple[ExprNode, ...]
    location: SourceLocation | None = None


QuantDescNode = Union[PerTensorQuantNode, PerChannelQuantNode, PerGroupQuantNode]


# ---------------------------------------------------------------------------
# Type attributes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TypeAttrsNode:
    """Type attribute block: ``elem=TYPE, shape=[...], layout=ID``."""

    elem: str
    shape: tuple[ExprNode, ...]
    layout: str | None = None
    strides: tuple[ExprNode, ...] | None = None
    quant: QuantDescNode | None = None
    location: SourceLocation | None = None


# ---------------------------------------------------------------------------
# Decorator node
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecoratorNode:
    """``@name`` or ``@name(args)``."""

    name: str
    args: tuple[ExprNode, ...] | None = None
    location: SourceLocation | None = None


# ---------------------------------------------------------------------------
# Statement nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConstDeclNode:
    """``const NAME = expr`` declaration."""

    name: str
    value: ExprNode
    location: SourceLocation | None = None


@dataclass(frozen=True)
class BufferDeclNode:
    """``buffer NAME : level (size=expr, align=INT) @decos``."""

    name: str
    mem_level: str  # "DDR", "L2", "L1"
    size: ExprNode | None = None
    align: ExprNode | None = None
    l1_index: ExprNode | None = None  # for L1[expr]
    decorators: tuple[DecoratorNode, ...] = ()
    location: SourceLocation | None = None


@dataclass(frozen=True)
class RegionDeclNode:
    """``let NAME = region(buf, offset, extent) type_attrs? @decos``."""

    name: str
    buffer_name: str
    offset: ExprNode
    extent: ExprNode
    type_attrs: TypeAttrsNode | None = None
    decorators: tuple[DecoratorNode, ...] = ()
    location: SourceLocation | None = None


@dataclass(frozen=True)
class LetDeclNode:
    """``let NAME = value`` (non-region let binding)."""

    name: str
    value: ExprNode
    location: SourceLocation | None = None


# Union of all statement types the parser can produce.
StmtNode = Union[ConstDeclNode, BufferDeclNode, RegionDeclNode, LetDeclNode]


# ---------------------------------------------------------------------------
# Program node
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProgramNode:
    """Top-level program: optional device ref, optional name, statements."""

    device_ref: str | None
    name: str | None
    statements: tuple[StmtNode, ...]
    location: SourceLocation | None = None
