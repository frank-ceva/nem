"""Source location tracking for NEM diagnostics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceLocation:
    """A location in NEM source code."""

    file: str
    line: int  # 1-indexed
    column: int  # 1-indexed
    end_line: int | None = None
    end_column: int | None = None

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.column}"
