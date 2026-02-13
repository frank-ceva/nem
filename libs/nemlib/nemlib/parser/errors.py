"""Parse error types for the NEM parser."""

from __future__ import annotations

from nemlib.diagnostics.location import SourceLocation


class ParseError(Exception):
    """Raised during parsing on unrecoverable errors."""

    def __init__(self, message: str, location: SourceLocation | None = None) -> None:
        super().__init__(message)
        self.location = location
