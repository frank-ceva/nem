"""Tests for the NEM lexer."""

from __future__ import annotations

from nemlib.diagnostics.collector import DiagnosticCollector
from nemlib.parser.lexer import Lexer
from nemlib.parser.tokens import TokenKind

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def lex(source: str) -> list[tuple[TokenKind, str]]:
    """Tokenize *source* and return ``(kind, lexeme)`` pairs (excluding EOF)."""
    diag = DiagnosticCollector()
    tokens = Lexer(source, "<test>", diag).tokenize()
    assert not diag.has_errors(), diag.format_all()
    # Drop trailing EOF for easier assertions
    return [(t.kind, t.lexeme) for t in tokens if t.kind != TokenKind.EOF]


def lex_with_diag(source: str) -> tuple[list[tuple[TokenKind, str]], DiagnosticCollector]:
    """Tokenize *source* and return tokens + diagnostics."""
    diag = DiagnosticCollector()
    tokens = Lexer(source, "<test>", diag).tokenize()
    pairs = [(t.kind, t.lexeme) for t in tokens if t.kind != TokenKind.EOF]
    return pairs, diag


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------


class TestKeywords:
    def test_program_keyword(self) -> None:
        assert lex("program") == [(TokenKind.PROGRAM, "program")]

    def test_device_keyword(self) -> None:
        assert lex("device") == [(TokenKind.DEVICE, "device")]

    def test_const_keyword(self) -> None:
        assert lex("const") == [(TokenKind.CONST, "const")]

    def test_buffer_keyword(self) -> None:
        assert lex("buffer") == [(TokenKind.BUFFER, "buffer")]

    def test_loop_endloop(self) -> None:
        tokens = lex("loop endloop")
        assert tokens == [
            (TokenKind.LOOP, "loop"),
            (TokenKind.ENDLOOP, "endloop"),
        ]

    def test_mod_keyword(self) -> None:
        assert lex("mod") == [(TokenKind.MOD, "mod")]

    def test_type_keywords(self) -> None:
        tokens = lex("i32 f16 bf16 bool")
        kinds = [t[0] for t in tokens]
        assert kinds == [TokenKind.I32, TokenKind.F16, TokenKind.BF16, TokenKind.BOOL_TYPE]

    def test_memory_levels(self) -> None:
        tokens = lex("DDR L2 L1")
        kinds = [t[0] for t in tokens]
        assert kinds == [TokenKind.DDR, TokenKind.L2, TokenKind.L1]

    def test_async_sync(self) -> None:
        tokens = lex("async sync")
        kinds = [t[0] for t in tokens]
        assert kinds == [TokenKind.ASYNC, TokenKind.SYNC]

    def test_identifier_not_keyword(self) -> None:
        # "constant" is NOT a keyword, just an identifier
        assert lex("constant") == [(TokenKind.IDENT, "constant")]


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------


class TestIdentifiers:
    def test_simple_ident(self) -> None:
        assert lex("foo") == [(TokenKind.IDENT, "foo")]

    def test_underscore_prefix(self) -> None:
        assert lex("_bar") == [(TokenKind.IDENT, "_bar")]

    def test_mixed_case_digits(self) -> None:
        assert lex("myVar2") == [(TokenKind.IDENT, "myVar2")]

    def test_all_underscores_digits(self) -> None:
        assert lex("__x_1_2") == [(TokenKind.IDENT, "__x_1_2")]


# ---------------------------------------------------------------------------
# Integer literals
# ---------------------------------------------------------------------------


class TestIntLiterals:
    def test_zero(self) -> None:
        assert lex("0") == [(TokenKind.INT_LIT, "0")]

    def test_positive(self) -> None:
        assert lex("42") == [(TokenKind.INT_LIT, "42")]

    def test_large(self) -> None:
        assert lex("1000000") == [(TokenKind.INT_LIT, "1000000")]

    def test_int_followed_by_dotdot(self) -> None:
        """``0..T`` must lex as INT DOTDOT IDENT, not a float."""
        tokens = lex("0..T")
        assert tokens == [
            (TokenKind.INT_LIT, "0"),
            (TokenKind.DOTDOT, ".."),
            (TokenKind.IDENT, "T"),
        ]


# ---------------------------------------------------------------------------
# Float literals
# ---------------------------------------------------------------------------


class TestFloatLiterals:
    def test_simple_float(self) -> None:
        assert lex("1.0") == [(TokenKind.FLOAT_LIT, "1.0")]

    def test_small_float(self) -> None:
        assert lex("0.00001") == [(TokenKind.FLOAT_LIT, "0.00001")]

    def test_exponent(self) -> None:
        assert lex("1.0e5") == [(TokenKind.FLOAT_LIT, "1.0e5")]

    def test_negative_exponent(self) -> None:
        assert lex("1.0e-5") == [(TokenKind.FLOAT_LIT, "1.0e-5")]

    def test_positive_exponent(self) -> None:
        assert lex("2.5E+3") == [(TokenKind.FLOAT_LIT, "2.5E+3")]

    def test_float_vs_dotdot(self) -> None:
        """``1.5`` is float, but ``1..5`` is INT DOTDOT INT."""
        assert lex("1.5") == [(TokenKind.FLOAT_LIT, "1.5")]
        tokens = lex("1..5")
        assert tokens == [
            (TokenKind.INT_LIT, "1"),
            (TokenKind.DOTDOT, ".."),
            (TokenKind.INT_LIT, "5"),
        ]


# ---------------------------------------------------------------------------
# String literals
# ---------------------------------------------------------------------------


class TestStringLiterals:
    def test_simple_string(self) -> None:
        tokens = lex('"hello"')
        assert tokens == [(TokenKind.STRING_LIT, '"hello"')]

    def test_empty_string(self) -> None:
        tokens = lex('""')
        assert tokens == [(TokenKind.STRING_LIT, '""')]

    def test_escape_sequences(self) -> None:
        tokens = lex(r'"a\nb\tc\\"')
        assert tokens[0][0] == TokenKind.STRING_LIT

    def test_unterminated_string(self) -> None:
        tokens, diag = lex_with_diag('"oops')
        assert diag.has_errors()


# ---------------------------------------------------------------------------
# Operators and delimiters
# ---------------------------------------------------------------------------


class TestOperatorsAndDelimiters:
    def test_arithmetic_ops(self) -> None:
        tokens = lex("+ - * /")
        kinds = [t[0] for t in tokens]
        assert kinds == [TokenKind.PLUS, TokenKind.MINUS, TokenKind.STAR, TokenKind.SLASH]

    def test_delimiters(self) -> None:
        tokens = lex("( ) [ ] { } : ; , = @")
        kinds = [t[0] for t in tokens]
        assert kinds == [
            TokenKind.LPAREN,
            TokenKind.RPAREN,
            TokenKind.LBRACKET,
            TokenKind.RBRACKET,
            TokenKind.LBRACE,
            TokenKind.RBRACE,
            TokenKind.COLON,
            TokenKind.SEMICOLON,
            TokenKind.COMMA,
            TokenKind.EQUALS,
            TokenKind.AT,
        ]

    def test_dot_vs_dotdot(self) -> None:
        assert lex(".") == [(TokenKind.DOT, ".")]
        assert lex("..") == [(TokenKind.DOTDOT, "..")]

    def test_compound_transfer_async(self) -> None:
        """``transfer.async`` lexes as three tokens."""
        tokens = lex("transfer.async")
        assert tokens == [
            (TokenKind.TRANSFER, "transfer"),
            (TokenKind.DOT, "."),
            (TokenKind.ASYNC, "async"),
        ]

    def test_angle_brackets(self) -> None:
        """``conv2d<f16, f16, f32>`` lexes with angle brackets."""
        tokens = lex("conv2d<f16, f16, f32>")
        kinds = [t[0] for t in tokens]
        assert kinds == [
            TokenKind.IDENT,
            TokenKind.LANGLE,
            TokenKind.F16,
            TokenKind.COMMA,
            TokenKind.F16,
            TokenKind.COMMA,
            TokenKind.F32,
            TokenKind.RANGLE,
        ]


# ---------------------------------------------------------------------------
# Comments and whitespace
# ---------------------------------------------------------------------------


class TestCommentsAndWhitespace:
    def test_comment_skipped(self) -> None:
        tokens = lex("foo # this is a comment")
        assert tokens == [(TokenKind.IDENT, "foo")]

    def test_comment_only(self) -> None:
        assert lex("# just a comment") == []

    def test_whitespace_skipped(self) -> None:
        tokens = lex("  foo   bar  ")
        assert tokens == [
            (TokenKind.IDENT, "foo"),
            (TokenKind.IDENT, "bar"),
        ]

    def test_tabs_skipped(self) -> None:
        tokens = lex("\tfoo\t\tbar")
        assert tokens == [
            (TokenKind.IDENT, "foo"),
            (TokenKind.IDENT, "bar"),
        ]


# ---------------------------------------------------------------------------
# Newline handling
# ---------------------------------------------------------------------------


class TestNewlines:
    def test_single_newline(self) -> None:
        tokens = lex("foo\nbar")
        assert tokens == [
            (TokenKind.IDENT, "foo"),
            (TokenKind.NEWLINE, "\\n"),
            (TokenKind.IDENT, "bar"),
        ]

    def test_consecutive_newlines_collapsed(self) -> None:
        tokens = lex("foo\n\n\nbar")
        assert tokens == [
            (TokenKind.IDENT, "foo"),
            (TokenKind.NEWLINE, "\\n"),
            (TokenKind.IDENT, "bar"),
        ]

    def test_leading_newlines_suppressed(self) -> None:
        tokens = lex("\n\nfoo")
        assert tokens == [(TokenKind.IDENT, "foo")]

    def test_trailing_newline(self) -> None:
        tokens = lex("foo\n")
        assert tokens == [
            (TokenKind.IDENT, "foo"),
            (TokenKind.NEWLINE, "\\n"),
        ]


# ---------------------------------------------------------------------------
# Source locations
# ---------------------------------------------------------------------------


class TestLocations:
    def test_first_token_location(self) -> None:
        diag = DiagnosticCollector()
        tokens = Lexer("foo", "test.nem", diag).tokenize()
        assert tokens[0].location.file == "test.nem"
        assert tokens[0].location.line == 1
        assert tokens[0].location.column == 1

    def test_second_line_location(self) -> None:
        diag = DiagnosticCollector()
        tokens = Lexer("foo\nbar", "test.nem", diag).tokenize()
        # tokens: IDENT("foo"), NEWLINE, IDENT("bar"), EOF
        bar_tok = tokens[2]
        assert bar_tok.location.line == 2
        assert bar_tok.location.column == 1

    def test_eof_location(self) -> None:
        diag = DiagnosticCollector()
        tokens = Lexer("x", "test.nem", diag).tokenize()
        eof = tokens[-1]
        assert eof.kind == TokenKind.EOF


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestLexerErrors:
    def test_unknown_character(self) -> None:
        tokens, diag = lex_with_diag("foo ~ bar")
        assert diag.has_errors()
        # The lexer should still produce tokens for foo and bar
        kinds = [t[0] for t in tokens]
        assert TokenKind.IDENT in kinds

    def test_empty_source(self) -> None:
        tokens = lex("")
        assert tokens == []


# ---------------------------------------------------------------------------
# Full program tokenization
# ---------------------------------------------------------------------------


class TestFullProgram:
    def test_const_decl_line(self) -> None:
        tokens = lex("const WIDTH = 128")
        kinds = [t[0] for t in tokens]
        assert kinds == [
            TokenKind.CONST,
            TokenKind.IDENT,
            TokenKind.EQUALS,
            TokenKind.INT_LIT,
        ]

    def test_device_header(self) -> None:
        tokens = lex('device "my_device.cfg"')
        kinds = [t[0] for t in tokens]
        assert kinds == [TokenKind.DEVICE, TokenKind.STRING_LIT]

    def test_program_header(self) -> None:
        tokens = lex("program MatMul:")
        kinds = [t[0] for t in tokens]
        assert kinds == [TokenKind.PROGRAM, TokenKind.IDENT, TokenKind.COLON]

    def test_loop_range(self) -> None:
        """``[0..N-1]`` should lex correctly."""
        tokens = lex("[0..N-1]")
        kinds = [t[0] for t in tokens]
        assert kinds == [
            TokenKind.LBRACKET,
            TokenKind.INT_LIT,
            TokenKind.DOTDOT,
            TokenKind.IDENT,
            TokenKind.MINUS,
            TokenKind.INT_LIT,
            TokenKind.RBRACKET,
        ]

    def test_expression_with_mod(self) -> None:
        tokens = lex("A mod B + 1")
        kinds = [t[0] for t in tokens]
        assert kinds == [
            TokenKind.IDENT,
            TokenKind.MOD,
            TokenKind.IDENT,
            TokenKind.PLUS,
            TokenKind.INT_LIT,
        ]
