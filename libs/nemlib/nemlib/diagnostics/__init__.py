"""NEM diagnostics subpackage (Layer 0 — zero internal dependencies)."""

from nemlib.diagnostics.collector import DiagnosticCollector
from nemlib.diagnostics.diagnostic import Diagnostic
from nemlib.diagnostics.location import SourceLocation
from nemlib.diagnostics.severity import DiagnosticSeverity

__all__ = ["SourceLocation", "DiagnosticSeverity", "Diagnostic", "DiagnosticCollector"]
