"""Token definitions for the NEM lexer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from nemlib.diagnostics.location import SourceLocation


class TokenKind(Enum):
    """All token types recognized by the NEM lexer."""

    # === Keywords ===
    PROGRAM = auto()
    DEVICE = auto()
    CONST = auto()
    BUFFER = auto()
    LET = auto()
    LOOP = auto()
    ENDLOOP = auto()
    IN = auto()
    OUT = auto()
    INCLUDE = auto()

    # Task keywords
    TRANSFER = auto()
    STORE = auto()
    WAIT = auto()
    REGION = auto()

    # Device config keywords
    EXTENDS = auto()
    TYPE_FAMILY = auto()
    OPCODE = auto()
    TOPOLOGY = auto()
    MANDATORY = auto()
    EXTENDED = auto()
    SPEC_VERSION = auto()

    # Type keywords (element types from spec grammar)
    I4 = auto()
    I8 = auto()
    I16 = auto()
    I32 = auto()
    U8 = auto()
    U16 = auto()
    U32 = auto()
    F16 = auto()
    BF16 = auto()
    TF32 = auto()
    F32 = auto()
    F64 = auto()
    BOOL_TYPE = auto()  # "bool" -- avoid conflict with Python bool

    # Memory levels
    DDR = auto()
    L2 = auto()
    L1 = auto()

    # Attribute keywords
    SIZE = auto()
    ALIGN = auto()
    ELEM = auto()
    SHAPE = auto()
    LAYOUT = auto()
    STRIDES = auto()
    QUANT = auto()
    DEPS = auto()
    ASYNC = auto()
    SYNC = auto()

    # Operators
    PLUS = auto()  # +
    MINUS = auto()  # -
    STAR = auto()  # *
    SLASH = auto()  # /
    MOD = auto()  # mod (keyword operator)

    # Delimiters
    LPAREN = auto()  # (
    RPAREN = auto()  # )
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    LBRACE = auto()  # {
    RBRACE = auto()  # }
    COLON = auto()  # :
    SEMICOLON = auto()  # ;
    COMMA = auto()  # ,
    DOT = auto()  # .
    DOTDOT = auto()  # ..
    EQUALS = auto()  # =
    AT = auto()  # @
    LANGLE = auto()  # <
    RANGLE = auto()  # >

    # Literals
    INT_LIT = auto()
    FLOAT_LIT = auto()
    STRING_LIT = auto()
    IDENT = auto()

    # Special
    NEWLINE = auto()
    EOF = auto()


# Keyword string -> TokenKind mapping.
# Identifiers are checked against this table during lexing.
KEYWORDS: dict[str, TokenKind] = {
    "program": TokenKind.PROGRAM,
    "device": TokenKind.DEVICE,
    "const": TokenKind.CONST,
    "buffer": TokenKind.BUFFER,
    "let": TokenKind.LET,
    "loop": TokenKind.LOOP,
    "endloop": TokenKind.ENDLOOP,
    "in": TokenKind.IN,
    "out": TokenKind.OUT,
    "include": TokenKind.INCLUDE,
    "transfer": TokenKind.TRANSFER,
    "store": TokenKind.STORE,
    "wait": TokenKind.WAIT,
    "region": TokenKind.REGION,
    "extends": TokenKind.EXTENDS,
    "type_family": TokenKind.TYPE_FAMILY,
    "opcode": TokenKind.OPCODE,
    "topology": TokenKind.TOPOLOGY,
    "mandatory": TokenKind.MANDATORY,
    "extended": TokenKind.EXTENDED,
    "spec_version": TokenKind.SPEC_VERSION,
    "i4": TokenKind.I4,
    "i8": TokenKind.I8,
    "i16": TokenKind.I16,
    "i32": TokenKind.I32,
    "u8": TokenKind.U8,
    "u16": TokenKind.U16,
    "u32": TokenKind.U32,
    "f16": TokenKind.F16,
    "bf16": TokenKind.BF16,
    "tf32": TokenKind.TF32,
    "f32": TokenKind.F32,
    "f64": TokenKind.F64,
    "bool": TokenKind.BOOL_TYPE,
    "DDR": TokenKind.DDR,
    "L2": TokenKind.L2,
    "L1": TokenKind.L1,
    "size": TokenKind.SIZE,
    "align": TokenKind.ALIGN,
    "elem": TokenKind.ELEM,
    "shape": TokenKind.SHAPE,
    "layout": TokenKind.LAYOUT,
    "strides": TokenKind.STRIDES,
    "quant": TokenKind.QUANT,
    "deps": TokenKind.DEPS,
    "async": TokenKind.ASYNC,
    "sync": TokenKind.SYNC,
    "mod": TokenKind.MOD,
}


@dataclass(frozen=True)
class Token:
    """A single token produced by the NEM lexer."""

    kind: TokenKind
    lexeme: str
    location: SourceLocation
