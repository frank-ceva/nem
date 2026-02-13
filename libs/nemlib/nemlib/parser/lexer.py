"""Lexer (tokenizer) for NEM source code."""

from __future__ import annotations

from nemlib.diagnostics.collector import DiagnosticCollector
from nemlib.diagnostics.location import SourceLocation
from nemlib.parser.tokens import KEYWORDS, Token, TokenKind


class Lexer:
    """Tokenize NEM source into a flat token stream.

    The lexer handles comments, whitespace collapsing, all literal types,
    keywords, identifiers, operators, and delimiters.  Unknown characters
    are reported as diagnostics and skipped.
    """

    # Single-character tokens that need no lookahead.
    _SINGLE_CHAR: dict[str, TokenKind] = {
        "+": TokenKind.PLUS,
        "-": TokenKind.MINUS,
        "*": TokenKind.STAR,
        "/": TokenKind.SLASH,
        "(": TokenKind.LPAREN,
        ")": TokenKind.RPAREN,
        "[": TokenKind.LBRACKET,
        "]": TokenKind.RBRACKET,
        "{": TokenKind.LBRACE,
        "}": TokenKind.RBRACE,
        ":": TokenKind.COLON,
        ";": TokenKind.SEMICOLON,
        ",": TokenKind.COMMA,
        "=": TokenKind.EQUALS,
        "@": TokenKind.AT,
        "<": TokenKind.LANGLE,
        ">": TokenKind.RANGLE,
    }

    def __init__(
        self,
        source: str,
        filename: str = "<string>",
        diagnostics: DiagnosticCollector | None = None,
    ) -> None:
        self._source = source
        self._filename = filename
        self._diag = diagnostics or DiagnosticCollector()
        self._pos = 0
        self._line = 1
        self._col = 1

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _peek(self, offset: int = 0) -> str:
        """Return character at current position + offset, or '' at EOF."""
        idx = self._pos + offset
        if idx < len(self._source):
            return self._source[idx]
        return ""

    def _advance(self) -> str:
        """Consume and return the current character, updating line/col."""
        ch = self._source[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return ch

    def _at_end(self) -> bool:
        return self._pos >= len(self._source)

    def _loc(self, line: int, col: int) -> SourceLocation:
        return SourceLocation(file=self._filename, line=line, column=col)

    # ------------------------------------------------------------------
    # Scanning helpers
    # ------------------------------------------------------------------

    def _skip_comment(self) -> None:
        """Skip from '#' to end of line (the newline itself is NOT consumed)."""
        while not self._at_end() and self._peek() != "\n":
            self._advance()

    def _scan_string(self, start_line: int, start_col: int) -> Token:
        """Scan a double-quoted string literal. Opening '"' already consumed."""
        chars: list[str] = []
        while not self._at_end():
            ch = self._advance()
            if ch == '"':
                lexeme = '"' + "".join(chars) + '"'
                return Token(TokenKind.STRING_LIT, lexeme, self._loc(start_line, start_col))
            if ch == "\\":
                if self._at_end():
                    self._diag.error(
                        "Unterminated escape in string literal",
                        self._loc(self._line, self._col),
                    )
                    break
                esc = self._advance()
                escape_map = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}
                chars.append(escape_map.get(esc, "\\" + esc))
            elif ch == "\n":
                self._diag.error(
                    "Unterminated string literal (newline in string)",
                    self._loc(start_line, start_col),
                )
                # Return what we have so far; the newline was already consumed
                # so line/col already updated
                lexeme = '"' + "".join(chars)
                return Token(TokenKind.STRING_LIT, lexeme, self._loc(start_line, start_col))
            else:
                chars.append(ch)
        # Reached EOF without closing quote
        self._diag.error(
            "Unterminated string literal",
            self._loc(start_line, start_col),
        )
        lexeme = '"' + "".join(chars)
        return Token(TokenKind.STRING_LIT, lexeme, self._loc(start_line, start_col))

    def _scan_number(self, start_line: int, start_col: int) -> Token:
        """Scan an integer or float literal. First digit already consumed via _advance."""
        # We already consumed the first digit; collect the rest of the integer part.
        # Back up: we need the first char. The caller already advanced, so
        # the first digit is at _pos - 1.
        begin = self._pos - 1
        while not self._at_end() and self._peek().isdigit():
            self._advance()

        # Check for float: digit+ '.' digit+ (but NOT '..' which is DOTDOT)
        if self._peek() == "." and self._peek(1).isdigit():
            self._advance()  # consume '.'
            while not self._at_end() and self._peek().isdigit():
                self._advance()
            # Optional exponent
            if self._peek() in ("e", "E"):
                self._advance()
                if self._peek() in ("+", "-"):
                    self._advance()
                if not self._at_end() and self._peek().isdigit():
                    while not self._at_end() and self._peek().isdigit():
                        self._advance()
                else:
                    self._diag.error(
                        "Expected digits after exponent in float literal",
                        self._loc(self._line, self._col),
                    )
            lexeme = self._source[begin : self._pos]
            return Token(TokenKind.FLOAT_LIT, lexeme, self._loc(start_line, start_col))

        lexeme = self._source[begin : self._pos]
        return Token(TokenKind.INT_LIT, lexeme, self._loc(start_line, start_col))

    def _scan_identifier_or_keyword(self, start_line: int, start_col: int) -> Token:
        """Scan an identifier or keyword. First char already consumed."""
        begin = self._pos - 1
        while not self._at_end() and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        lexeme = self._source[begin : self._pos]
        kind = KEYWORDS.get(lexeme, TokenKind.IDENT)
        return Token(kind, lexeme, self._loc(start_line, start_col))

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def tokenize(self) -> list[Token]:
        """Tokenize the entire source. Returns list ending with an EOF token."""
        tokens: list[Token] = []
        # Track whether the last emitted non-NEWLINE token exists,
        # so we can collapse consecutive newlines.
        last_was_newline = True  # suppress leading newlines

        while not self._at_end():
            ch = self._peek()

            # --- Whitespace (non-newline) ---
            if ch in (" ", "\t", "\r"):
                self._advance()
                continue

            # --- Comments ---
            if ch == "#":
                self._skip_comment()
                continue

            # --- Newlines ---
            if ch == "\n":
                line, col = self._line, self._col
                self._advance()
                if not last_was_newline:
                    tokens.append(Token(TokenKind.NEWLINE, "\\n", self._loc(line, col)))
                    last_was_newline = True
                continue

            # From here on we have a non-whitespace, non-comment character.
            last_was_newline = False

            # --- String literal ---
            if ch == '"':
                line, col = self._line, self._col
                self._advance()  # consume opening '"'
                tokens.append(self._scan_string(line, col))
                continue

            # --- Number literal ---
            if ch.isdigit():
                line, col = self._line, self._col
                self._advance()
                tokens.append(self._scan_number(line, col))
                continue

            # --- Identifier / keyword ---
            if ch.isalpha() or ch == "_":
                line, col = self._line, self._col
                self._advance()
                tokens.append(self._scan_identifier_or_keyword(line, col))
                continue

            # --- Dot / DotDot ---
            if ch == ".":
                line, col = self._line, self._col
                self._advance()
                if self._peek() == ".":
                    self._advance()
                    tokens.append(Token(TokenKind.DOTDOT, "..", self._loc(line, col)))
                else:
                    tokens.append(Token(TokenKind.DOT, ".", self._loc(line, col)))
                continue

            # --- Single-character tokens ---
            if ch in self._SINGLE_CHAR:
                line, col = self._line, self._col
                self._advance()
                tokens.append(Token(self._SINGLE_CHAR[ch], ch, self._loc(line, col)))
                continue

            # --- Unknown character ---
            line, col = self._line, self._col
            self._advance()
            self._diag.error(
                f"Unexpected character: {ch!r}",
                self._loc(line, col),
            )

        # Append EOF
        tokens.append(Token(TokenKind.EOF, "", self._loc(self._line, self._col)))
        return tokens
