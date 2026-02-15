"""Diagnostic severity levels for NEM."""

from __future__ import annotations

from enum import Enum


class DiagnosticSeverity(Enum):
    """Severity level of a diagnostic message."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    def __str__(self) -> str:
        return self.value
