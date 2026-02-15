"""Diagnostic collector for accumulating messages during parsing and validation."""

from __future__ import annotations

from nemlib.diagnostics.diagnostic import Diagnostic
from nemlib.diagnostics.location import SourceLocation
from nemlib.diagnostics.severity import DiagnosticSeverity


class DiagnosticCollector:
    """Accumulates diagnostics during parsing and validation."""

    def __init__(self) -> None:
        self._diagnostics: list[Diagnostic] = []

    def error(
        self,
        message: str,
        location: SourceLocation | None = None,
        *,
        notes: tuple[str, ...] = (),
    ) -> None:
        """Record an error diagnostic."""
        self._diagnostics.append(Diagnostic(DiagnosticSeverity.ERROR, message, location, notes))

    def warning(
        self,
        message: str,
        location: SourceLocation | None = None,
        *,
        notes: tuple[str, ...] = (),
    ) -> None:
        """Record a warning diagnostic."""
        self._diagnostics.append(Diagnostic(DiagnosticSeverity.WARNING, message, location, notes))

    def info(
        self,
        message: str,
        location: SourceLocation | None = None,
        *,
        notes: tuple[str, ...] = (),
    ) -> None:
        """Record an informational diagnostic."""
        self._diagnostics.append(Diagnostic(DiagnosticSeverity.INFO, message, location, notes))

    def has_errors(self) -> bool:
        """Return True if any error diagnostics have been recorded."""
        return any(d.severity == DiagnosticSeverity.ERROR for d in self._diagnostics)

    def get_all(self) -> list[Diagnostic]:
        """Return a copy of all collected diagnostics."""
        return list(self._diagnostics)

    def format_all(self) -> str:
        """Format all diagnostics as a newline-separated string."""
        return "\n".join(str(d) for d in self._diagnostics)
