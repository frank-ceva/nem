"""Diagnostic message representation for NEM."""

from __future__ import annotations

from dataclasses import dataclass

from nemlib.diagnostics.location import SourceLocation
from nemlib.diagnostics.severity import DiagnosticSeverity


@dataclass(frozen=True)
class Diagnostic:
    """A single diagnostic message."""

    severity: DiagnosticSeverity
    message: str
    location: SourceLocation | None = None
    notes: tuple[str, ...] = ()

    def __str__(self) -> str:
        loc = f"{self.location}: " if self.location else ""
        return f"{loc}{self.severity}: {self.message}"
