"""Recursive-descent parser for NEM source code.

Handles:
- ``device "file.cfg"``  (optional header)
- ``program NAME:``      (optional header)
- ``const NAME = expr``  declarations
- ``buffer NAME : level (size=expr, align=INT) @decos``
- ``let NAME = region(buf, offset, extent) type_attrs @decos``
- ``let NAME = value``
- Decorators: ``@name`` or ``@name(args)``
- Type attributes: ``elem=type, shape=[...], layout=ID or strides=[...]``
- Quantization descriptors: per_tensor, per_channel, per_group
- Expressions with standard arithmetic precedence
"""

from __future__ import annotations

from nemlib.core.expressions import (
    BinaryOp,
    ExprNode,
    FloatLiteral,
    Identifier,
    IntLiteral,
    ParenExpr,
    UnaryOp,
)
from nemlib.diagnostics.collector import DiagnosticCollector
from nemlib.diagnostics.location import SourceLocation
from nemlib.parser.ast_nodes import (
    ArrayLiteral,
    BufferDeclNode,
    ConstDeclNode,
    DecoratorNode,
    LetDeclNode,
    PerChannelQuantNode,
    PerGroupQuantNode,
    PerTensorQuantNode,
    ProgramNode,
    RegionDeclNode,
    StmtNode,
    StringLiteral,
    TypeAttrsNode,
)
from nemlib.parser.errors import ParseError
from nemlib.parser.lexer import Lexer
from nemlib.parser.tokens import Token, TokenKind

# Element type token kinds for matching elem_type production.
_ELEM_TYPE_TOKENS: set[TokenKind] = {
    TokenKind.I4,
    TokenKind.I8,
    TokenKind.I16,
    TokenKind.I32,
    TokenKind.U8,
    TokenKind.U16,
    TokenKind.U32,
    TokenKind.F16,
    TokenKind.BF16,
    TokenKind.TF32,
    TokenKind.F32,
    TokenKind.F64,
    TokenKind.BOOL_TYPE,
}


class Parser:
    """Recursive-descent parser for NEM programs."""

    def __init__(
        self,
        tokens: list[Token],
        diagnostics: DiagnosticCollector | None = None,
    ) -> None:
        self._tokens = tokens
        self._diag = diagnostics or DiagnosticCollector()
        self._pos = 0

    # ------------------------------------------------------------------
    # Token stream helpers
    # ------------------------------------------------------------------

    def _peek(self) -> Token:
        """Return the current token without consuming it."""
        return self._tokens[self._pos]

    def _peek_ahead(self, offset: int = 1) -> Token:
        """Peek at a token ahead of current position."""
        idx = self._pos + offset
        if idx < len(self._tokens):
            return self._tokens[idx]
        return self._tokens[-1]  # EOF

    def _at_end(self) -> bool:
        return self._peek().kind == TokenKind.EOF

    def _advance(self) -> Token:
        """Consume and return the current token."""
        tok = self._tokens[self._pos]
        if tok.kind != TokenKind.EOF:
            self._pos += 1
        return tok

    def _check(self, kind: TokenKind) -> bool:
        """Return True if the current token is *kind*."""
        return self._peek().kind == kind

    def _match(self, *kinds: TokenKind) -> Token | None:
        """If current token matches any of *kinds*, consume and return it."""
        for kind in kinds:
            if self._check(kind):
                return self._advance()
        return None

    def _expect(self, kind: TokenKind, message: str) -> Token:
        """Consume a token of *kind* or report an error."""
        tok = self._peek()
        if tok.kind == kind:
            return self._advance()
        self._diag.error(
            f"{message} (got {tok.kind.name} {tok.lexeme!r})",
            tok.location,
        )
        raise ParseError(message, tok.location)

    def _skip_newlines(self) -> None:
        """Skip any NEWLINE tokens."""
        while self._check(TokenKind.NEWLINE):
            self._advance()

    def _skip_to_newline(self) -> None:
        """Advance until NEWLINE or EOF (for error recovery)."""
        while not self._at_end() and not self._check(TokenKind.NEWLINE):
            self._advance()

    def _peek_past_newlines(self) -> TokenKind:
        """Look ahead past newlines to see what the next non-newline token is."""
        i = self._pos
        while i < len(self._tokens) and self._tokens[i].kind == TokenKind.NEWLINE:
            i += 1
        if i < len(self._tokens):
            return self._tokens[i].kind
        return TokenKind.EOF

    # ------------------------------------------------------------------
    # Top-level program parsing
    # ------------------------------------------------------------------

    def parse_program(self) -> ProgramNode:
        """Parse a complete NEM program."""
        loc = self._peek().location
        self._skip_newlines()

        # Optional: device "file.cfg"
        device_ref = self._parse_device_header()
        self._skip_newlines()

        # Optional: program NAME:
        program_name = self._parse_program_header()
        self._skip_newlines()

        # Body: declarations and statements
        stmts = self._parse_body()

        self._skip_newlines()

        return ProgramNode(
            device_ref=device_ref,
            name=program_name,
            statements=tuple(stmts),
            location=loc,
        )

    def _parse_device_header(self) -> str | None:
        """Parse optional ``device "file.cfg"``."""
        if not self._check(TokenKind.DEVICE):
            return None
        self._advance()  # consume DEVICE
        tok = self._expect(TokenKind.STRING_LIT, "Expected string after 'device'")
        # Strip quotes from the lexeme
        return tok.lexeme.strip('"')

    def _parse_program_header(self) -> str | None:
        """Parse optional ``program NAME:``."""
        if not self._check(TokenKind.PROGRAM):
            return None
        self._advance()  # consume PROGRAM
        name_tok = self._expect(TokenKind.IDENT, "Expected identifier after 'program'")
        self._expect(TokenKind.COLON, "Expected ':' after program name")
        return name_tok.lexeme

    # ------------------------------------------------------------------
    # Body: statement list
    # ------------------------------------------------------------------

    def _parse_body(self) -> list[StmtNode]:
        """Parse top-level statements."""
        stmts: list[StmtNode] = []
        loop_depth = 0
        while not self._at_end():
            self._skip_newlines()
            if self._at_end():
                break
            if self._check(TokenKind.LOOP):
                loop_depth += 1
                self._skip_to_newline()
            elif self._check(TokenKind.ENDLOOP):
                if loop_depth > 0:
                    loop_depth -= 1
                self._skip_to_newline()
            elif self._check(TokenKind.CONST):
                if loop_depth > 0:
                    self._diag.error(
                        "Const declaration not permitted inside loop body",
                        self._peek().location,
                    )
                    self._skip_to_newline()
                else:
                    try:
                        stmts.append(self.parse_const_decl())
                    except ParseError:
                        self._skip_to_newline()
            elif self._check(TokenKind.BUFFER):
                try:
                    stmts.append(self.parse_buffer_decl())
                except ParseError:
                    self._skip_to_newline()
            elif self._check(TokenKind.LET):
                try:
                    stmts.append(self.parse_let_decl())
                except ParseError:
                    self._skip_to_newline()
            else:
                # Unknown top-level statement -- skip to next line
                self._skip_to_newline()
        return stmts

    # ------------------------------------------------------------------
    # const declaration
    # ------------------------------------------------------------------

    def parse_const_decl(self) -> ConstDeclNode:
        """Parse ``const NAME = expr``."""
        const_tok = self._expect(TokenKind.CONST, "Expected 'const'")
        name_tok = self._expect(TokenKind.IDENT, "Expected identifier after 'const'")
        self._expect(TokenKind.EQUALS, "Expected '=' after const name")
        value = self.parse_expression()
        return ConstDeclNode(
            name=name_tok.lexeme,
            value=value,
            location=const_tok.location,
        )

    # ------------------------------------------------------------------
    # buffer declaration
    # ------------------------------------------------------------------

    def parse_buffer_decl(self) -> BufferDeclNode:
        """Parse ``buffer NAME : level (size=expr, align=INT) @decos``."""
        buf_tok = self._expect(TokenKind.BUFFER, "Expected 'buffer'")
        name_tok = self._expect(TokenKind.IDENT, "Expected buffer name")
        self._expect(TokenKind.COLON, "Expected ':' after buffer name")

        mem_level, l1_index = self._parse_mem_level()

        self._expect(TokenKind.LPAREN, "Expected '(' after memory level")
        size, align = self._parse_buffer_props()
        self._expect(TokenKind.RPAREN, "Expected ')' after buffer properties")

        decos = self._parse_decorators()

        return BufferDeclNode(
            name=name_tok.lexeme,
            mem_level=mem_level,
            size=size,
            align=align,
            l1_index=l1_index,
            decorators=tuple(decos),
            location=buf_tok.location,
        )

    def _parse_mem_level(self) -> tuple[str, ExprNode | None]:
        """Parse memory level: DDR, L2, L1, or L1[expr]."""
        tok = self._peek()
        if tok.kind == TokenKind.DDR:
            self._advance()
            return ("DDR", None)
        if tok.kind == TokenKind.L2:
            self._advance()
            return ("L2", None)
        if tok.kind == TokenKind.L1:
            self._advance()
            l1_index: ExprNode | None = None
            if self._check(TokenKind.LBRACKET):
                self._advance()
                l1_index = self.parse_expression()
                self._expect(TokenKind.RBRACKET, "Expected ']' after L1 index")
            return ("L1", l1_index)
        self._diag.error(
            f"Expected memory level (DDR, L2, L1), got {tok.kind.name}",
            tok.location,
        )
        raise ParseError("Expected memory level", tok.location)

    def _parse_buffer_props(self) -> tuple[ExprNode | None, ExprNode | None]:
        """Parse ``size=expr, align=expr`` inside buffer parens."""
        size: ExprNode | None = None
        align: ExprNode | None = None
        while not self._check(TokenKind.RPAREN) and not self._at_end():
            if self._check(TokenKind.SIZE):
                self._advance()
                self._expect(TokenKind.EQUALS, "Expected '=' after 'size'")
                size = self.parse_expression()
            elif self._check(TokenKind.ALIGN):
                self._advance()
                self._expect(TokenKind.EQUALS, "Expected '=' after 'align'")
                align = self.parse_expression()
            else:
                break
            # Optional comma between props
            self._match(TokenKind.COMMA)
        return size, align

    # ------------------------------------------------------------------
    # let / region declaration
    # ------------------------------------------------------------------

    def parse_let_decl(self) -> RegionDeclNode | LetDeclNode:
        """Parse ``let NAME = region(...)`` or ``let NAME = value``."""
        let_tok = self._expect(TokenKind.LET, "Expected 'let'")
        name_tok = self._expect(TokenKind.IDENT, "Expected identifier after 'let'")
        self._expect(TokenKind.EQUALS, "Expected '=' after let name")

        # Check if this is a region declaration
        if self._check(TokenKind.REGION):
            return self._parse_region_body(name_tok.lexeme, let_tok.location)

        # Otherwise, parse as a general value
        value = self._parse_value()
        return LetDeclNode(
            name=name_tok.lexeme,
            value=value,
            location=let_tok.location,
        )

    def _parse_region_body(self, name: str, loc: SourceLocation | None) -> RegionDeclNode:
        """Parse region(buf, offset, extent) type_attrs? decos? after 'let NAME ='."""
        self._expect(TokenKind.REGION, "Expected 'region'")
        self._expect(TokenKind.LPAREN, "Expected '(' after 'region'")

        buf_tok = self._expect(TokenKind.IDENT, "Expected buffer name in region")
        self._expect(TokenKind.COMMA, "Expected ',' after buffer name")
        offset = self.parse_expression()
        self._expect(TokenKind.COMMA, "Expected ',' after offset")
        extent = self.parse_expression()
        self._expect(TokenKind.RPAREN, "Expected ')' after region extent")

        # Type attributes may follow on the same line or continuation line
        type_attrs = self._try_parse_type_attrs()

        # Decorators may follow on the same line or continuation line
        decos = self._parse_decorators()

        return RegionDeclNode(
            name=name,
            buffer_name=buf_tok.lexeme,
            offset=offset,
            extent=extent,
            type_attrs=type_attrs,
            decorators=tuple(decos),
            location=loc,
        )

    # ------------------------------------------------------------------
    # Type attributes
    # ------------------------------------------------------------------

    def _try_parse_type_attrs(self) -> TypeAttrsNode | None:
        """Try to parse type_attrs. Looks past newlines for 'elem' keyword."""
        # Check if elem= follows (possibly after newline continuation)
        if self._peek_past_newlines() != TokenKind.ELEM:
            return None
        self._skip_newlines()
        return self._parse_type_attrs()

    def _parse_type_attrs(self) -> TypeAttrsNode:
        """Parse ``elem=type, shape=[...], layout=ID`` or ``strides=[...]``."""
        loc = self._peek().location

        # elem = elem_type
        self._expect(TokenKind.ELEM, "Expected 'elem'")
        self._expect(TokenKind.EQUALS, "Expected '=' after 'elem'")
        elem = self._parse_elem_type()

        self._expect(TokenKind.COMMA, "Expected ',' after elem type")

        # shape = [expr, expr, ...]
        self._expect(TokenKind.SHAPE, "Expected 'shape'")
        self._expect(TokenKind.EQUALS, "Expected '=' after 'shape'")
        shape = self._parse_expr_list()

        # layout = ID  or  strides = [expr, ...]
        layout: str | None = None
        strides: tuple[ExprNode, ...] | None = None

        # Comma before layout/strides
        if self._match(TokenKind.COMMA):
            if self._check(TokenKind.LAYOUT):
                self._advance()
                self._expect(TokenKind.EQUALS, "Expected '=' after 'layout'")
                layout_tok = self._expect(TokenKind.IDENT, "Expected layout name")
                layout = layout_tok.lexeme
            elif self._check(TokenKind.STRIDES):
                self._advance()
                self._expect(TokenKind.EQUALS, "Expected '=' after 'strides'")
                strides = self._parse_expr_list()

        # Optional quant
        quant: PerTensorQuantNode | PerChannelQuantNode | PerGroupQuantNode | None = None
        if self._match(TokenKind.COMMA):
            if self._check(TokenKind.QUANT):
                self._advance()
                self._expect(TokenKind.EQUALS, "Expected '=' after 'quant'")
                quant = self._parse_quant_desc()

        return TypeAttrsNode(
            elem=elem,
            shape=tuple(shape),
            layout=layout,
            strides=strides,
            quant=quant,
            location=loc,
        )

    def _parse_elem_type(self) -> str:
        """Parse an element type keyword and return its string value."""
        tok = self._peek()
        if tok.kind in _ELEM_TYPE_TOKENS:
            self._advance()
            return tok.lexeme
        self._diag.error(
            f"Expected element type, got {tok.kind.name} {tok.lexeme!r}",
            tok.location,
        )
        raise ParseError("Expected element type", tok.location)

    def _parse_expr_list(self) -> tuple[ExprNode, ...]:
        """Parse ``[expr, expr, ...]`` and return the expressions."""
        self._expect(TokenKind.LBRACKET, "Expected '['")
        exprs: list[ExprNode] = []
        if not self._check(TokenKind.RBRACKET):
            exprs.append(self.parse_expression())
            while self._match(TokenKind.COMMA):
                if self._check(TokenKind.RBRACKET):
                    break  # trailing comma
                exprs.append(self.parse_expression())
        self._expect(TokenKind.RBRACKET, "Expected ']'")
        return tuple(exprs)

    # ------------------------------------------------------------------
    # Quantization descriptors
    # ------------------------------------------------------------------

    def _parse_quant_desc(
        self,
    ) -> PerTensorQuantNode | PerChannelQuantNode | PerGroupQuantNode:
        """Parse quant descriptor: per_tensor(...), per_channel(...), per_group(...)."""
        tok = self._peek()
        if tok.kind != TokenKind.IDENT:
            self._diag.error(
                f"Expected quant descriptor kind, got {tok.kind.name}",
                tok.location,
            )
            raise ParseError("Expected quant descriptor kind", tok.location)

        kind = tok.lexeme
        self._advance()
        self._expect(TokenKind.LPAREN, f"Expected '(' after '{kind}'")

        result: PerTensorQuantNode | PerChannelQuantNode | PerGroupQuantNode
        if kind == "per_tensor":
            result = self._parse_per_tensor_quant(tok.location)
        elif kind == "per_channel":
            result = self._parse_per_channel_quant(tok.location)
        elif kind == "per_group":
            result = self._parse_per_group_quant(tok.location)
        else:
            self._diag.error(f"Unknown quant descriptor: {kind!r}", tok.location)
            raise ParseError(f"Unknown quant descriptor: {kind!r}", tok.location)

        self._expect(TokenKind.RPAREN, f"Expected ')' after {kind} descriptor")
        return result

    def _parse_per_tensor_quant(self, loc: SourceLocation | None) -> PerTensorQuantNode:
        """Parse ``per_tensor(scale=VAL, zero_point=VAL)``."""
        self._expect_ident("scale")
        self._expect(TokenKind.EQUALS, "Expected '=' after 'scale'")
        scale = self._parse_value()
        self._expect(TokenKind.COMMA, "Expected ','")
        self._expect_ident("zero_point")
        self._expect(TokenKind.EQUALS, "Expected '=' after 'zero_point'")
        zero_point = self._parse_value()
        return PerTensorQuantNode(scale=scale, zero_point=zero_point, location=loc)

    def _parse_per_channel_quant(self, loc: SourceLocation | None) -> PerChannelQuantNode:
        """Parse ``per_channel(axis=INT, scales=[...], zero_points=[...])``."""
        self._expect_ident("axis")
        self._expect(TokenKind.EQUALS, "Expected '=' after 'axis'")
        axis = self.parse_expression()
        self._expect(TokenKind.COMMA, "Expected ','")
        self._expect_ident("scales")
        self._expect(TokenKind.EQUALS, "Expected '=' after 'scales'")
        scales = self._parse_value_list()
        self._expect(TokenKind.COMMA, "Expected ','")
        self._expect_ident("zero_points")
        self._expect(TokenKind.EQUALS, "Expected '=' after 'zero_points'")
        zero_points = self._parse_value_list()
        return PerChannelQuantNode(axis=axis, scales=scales, zero_points=zero_points, location=loc)

    def _parse_per_group_quant(self, loc: SourceLocation | None) -> PerGroupQuantNode:
        """Parse per_group(axis=INT, group_size=INT, scales=[...], zero_points=[...])."""
        self._expect_ident("axis")
        self._expect(TokenKind.EQUALS, "Expected '=' after 'axis'")
        axis = self.parse_expression()
        self._expect(TokenKind.COMMA, "Expected ','")
        self._expect_ident("group_size")
        self._expect(TokenKind.EQUALS, "Expected '=' after 'group_size'")
        group_size = self.parse_expression()
        self._expect(TokenKind.COMMA, "Expected ','")
        self._expect_ident("scales")
        self._expect(TokenKind.EQUALS, "Expected '=' after 'scales'")
        scales = self._parse_value_list()
        self._expect(TokenKind.COMMA, "Expected ','")
        self._expect_ident("zero_points")
        self._expect(TokenKind.EQUALS, "Expected '=' after 'zero_points'")
        zero_points = self._parse_value_list()
        return PerGroupQuantNode(
            axis=axis,
            group_size=group_size,
            scales=scales,
            zero_points=zero_points,
            location=loc,
        )

    def _expect_ident(self, name: str) -> Token:
        """Consume an IDENT token with a specific name."""
        tok = self._peek()
        if tok.kind == TokenKind.IDENT and tok.lexeme == name:
            return self._advance()
        self._diag.error(
            f"Expected '{name}' (got {tok.kind.name} {tok.lexeme!r})",
            tok.location,
        )
        raise ParseError(f"Expected '{name}'", tok.location)

    def _parse_value_list(self) -> tuple[ExprNode, ...]:
        """Parse ``[value, value, ...]``."""
        self._expect(TokenKind.LBRACKET, "Expected '['")
        values: list[ExprNode] = []
        if not self._check(TokenKind.RBRACKET):
            values.append(self._parse_value())
            while self._match(TokenKind.COMMA):
                if self._check(TokenKind.RBRACKET):
                    break
                values.append(self._parse_value())
        self._expect(TokenKind.RBRACKET, "Expected ']'")
        return tuple(values)

    # ------------------------------------------------------------------
    # Decorators
    # ------------------------------------------------------------------

    def _parse_decorators(self) -> list[DecoratorNode]:
        """Parse zero or more decorators, looking past newlines."""
        decos: list[DecoratorNode] = []
        while self._peek_past_newlines() == TokenKind.AT:
            self._skip_newlines()
            decos.append(self._parse_decorator())
        return decos

    def _parse_decorator(self) -> DecoratorNode:
        """Parse ``@name`` or ``@name(args)``."""
        at_tok = self._expect(TokenKind.AT, "Expected '@'")
        name_tok = self._expect(TokenKind.IDENT, "Expected decorator name after '@'")

        args: tuple[ExprNode, ...] | None = None
        if self._match(TokenKind.LPAREN):
            args = self._parse_deco_args()
            self._expect(TokenKind.RPAREN, "Expected ')' after decorator args")

        return DecoratorNode(
            name=name_tok.lexeme,
            args=args,
            location=at_tok.location,
        )

    def _parse_deco_args(self) -> tuple[ExprNode, ...]:
        """Parse decorator arguments.

        Handles both ``value, value, ...`` and ``unit_type[expr]`` for @resource.
        """
        # Check for @resource(unit_type[idx]) pattern
        tok = self._peek()
        if tok.kind == TokenKind.IDENT and tok.lexeme in (
            "NMU",
            "CSTL",
            "DMA",
            "VPU",
            "SEQ",
            "sDMA",
            "WDM",
        ):
            unit_tok = self._advance()
            if self._check(TokenKind.LBRACKET):
                self._advance()
                idx = self.parse_expression()
                self._expect(TokenKind.RBRACKET, "Expected ']' after resource index")
                # Return as [Identifier(unit), idx_expr]
                return (
                    Identifier(name=unit_tok.lexeme, location=unit_tok.location),
                    idx,
                )
            # If no bracket, treat as regular value
            return (Identifier(name=unit_tok.lexeme, location=unit_tok.location),)

        # Regular value list
        values: list[ExprNode] = []
        if not self._check(TokenKind.RPAREN):
            values.append(self._parse_value())
            while self._match(TokenKind.COMMA):
                if self._check(TokenKind.RPAREN):
                    break
                values.append(self._parse_value())
        return tuple(values)

    # ------------------------------------------------------------------
    # Value parsing
    # ------------------------------------------------------------------

    def _parse_value(self) -> ExprNode:
        """Parse a value: expr, STRING, [value_list], or region_expr."""
        tok = self._peek()

        # String literal
        if tok.kind == TokenKind.STRING_LIT:
            self._advance()
            return StringLiteral(value=tok.lexeme.strip('"'), location=tok.location)

        # Array literal
        if tok.kind == TokenKind.LBRACKET:
            return self._parse_array_literal()

        # Expression (including identifiers, numbers, etc.)
        return self.parse_expression()

    def _parse_array_literal(self) -> ArrayLiteral:
        """Parse ``[value, value, ...]``."""
        tok = self._expect(TokenKind.LBRACKET, "Expected '['")
        elements: list[ExprNode] = []
        if not self._check(TokenKind.RBRACKET):
            elements.append(self._parse_value())
            while self._match(TokenKind.COMMA):
                if self._check(TokenKind.RBRACKET):
                    break
                elements.append(self._parse_value())
        self._expect(TokenKind.RBRACKET, "Expected ']'")
        return ArrayLiteral(elements=tuple(elements), location=tok.location)

    # ------------------------------------------------------------------
    # Expression parsing (precedence climbing)
    # ------------------------------------------------------------------

    def parse_expression(self) -> ExprNode:
        """Parse an expression with operator precedence."""
        return self._parse_additive()

    def _parse_additive(self) -> ExprNode:
        """Left-associative ``+`` and ``-``."""
        left = self._parse_multiplicative()
        while True:
            tok = self._match(TokenKind.PLUS, TokenKind.MINUS)
            if tok is None:
                break
            right = self._parse_multiplicative()
            left = BinaryOp(op=tok.lexeme, left=left, right=right, location=tok.location)
        return left

    def _parse_multiplicative(self) -> ExprNode:
        """Left-associative ``*``, ``/``, ``mod``."""
        left = self._parse_unary()
        while True:
            tok = self._match(TokenKind.STAR, TokenKind.SLASH, TokenKind.MOD)
            if tok is None:
                break
            right = self._parse_unary()
            left = BinaryOp(op=tok.lexeme, left=left, right=right, location=tok.location)
        return left

    def _parse_unary(self) -> ExprNode:
        """Prefix unary ``-``."""
        tok = self._match(TokenKind.MINUS)
        if tok is not None:
            operand = self._parse_unary()
            return UnaryOp(op="-", operand=operand, location=tok.location)
        return self._parse_primary()

    def _parse_primary(self) -> ExprNode:
        """Parse a primary expression: literal, identifier, or parenthesized."""
        tok = self._peek()

        # Integer literal
        if tok.kind == TokenKind.INT_LIT:
            self._advance()
            return IntLiteral(value=int(tok.lexeme), location=tok.location)

        # Float literal
        if tok.kind == TokenKind.FLOAT_LIT:
            self._advance()
            return FloatLiteral(value=float(tok.lexeme), location=tok.location)

        # Identifier
        if tok.kind == TokenKind.IDENT:
            self._advance()
            return Identifier(name=tok.lexeme, location=tok.location)

        # Parenthesized expression
        if tok.kind == TokenKind.LPAREN:
            self._advance()
            expr = self.parse_expression()
            self._expect(TokenKind.RPAREN, "Expected ')' after expression")
            return ParenExpr(expr=expr, location=tok.location)

        # Error
        self._diag.error(
            f"Expected expression, got {tok.kind.name} {tok.lexeme!r}",
            tok.location,
        )
        raise ParseError("Expected expression", tok.location)


# ------------------------------------------------------------------
# Convenience function
# ------------------------------------------------------------------


def parse(source: str, filename: str = "<string>") -> tuple[ProgramNode, DiagnosticCollector]:
    """Parse NEM source code.

    Returns:
        A ``(program_ast, diagnostics)`` tuple.
    """
    diag = DiagnosticCollector()
    lexer = Lexer(source, filename, diag)
    tokens = lexer.tokenize()
    parser = Parser(tokens, diag)
    program = parser.parse_program()
    return program, diag
