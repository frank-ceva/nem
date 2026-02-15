from __future__ import annotations

import pytest

from nemlib.diagnostics import (
    Diagnostic,
    DiagnosticCollector,
    DiagnosticSeverity,
    SourceLocation,
)


class TestSourceLocation:
    def test_creation_simple(self):
        loc = SourceLocation("test.nem", 10, 5)
        assert loc.file == "test.nem"
        assert loc.line == 10
        assert loc.column == 5
        assert loc.end_line is None
        assert loc.end_column is None

    def test_creation_with_end(self):
        loc = SourceLocation("test.nem", 10, 5, end_line=10, end_column=15)
        assert loc.file == "test.nem"
        assert loc.line == 10
        assert loc.column == 5
        assert loc.end_line == 10
        assert loc.end_column == 15

    def test_str_simple(self):
        loc = SourceLocation("test.nem", 10, 5)
        s = str(loc)
        assert "test.nem" in s
        assert "10" in s
        assert "5" in s

    def test_str_with_end(self):
        loc = SourceLocation("test.nem", 10, 5, end_line=10, end_column=15)
        s = str(loc)
        assert "test.nem" in s
        assert "10" in s
        assert "5" in s


class TestDiagnosticSeverity:
    def test_values_exist(self):
        assert DiagnosticSeverity.ERROR
        assert DiagnosticSeverity.WARNING
        assert DiagnosticSeverity.INFO

    def test_str_representation(self):
        assert str(DiagnosticSeverity.ERROR)
        assert str(DiagnosticSeverity.WARNING)
        assert str(DiagnosticSeverity.INFO)


class TestDiagnostic:
    def test_creation_minimal(self):
        diag = Diagnostic(DiagnosticSeverity.ERROR, "test error")
        assert diag.severity == DiagnosticSeverity.ERROR
        assert diag.message == "test error"
        assert diag.location is None
        assert diag.notes == ()

    def test_creation_with_location(self):
        loc = SourceLocation("test.nem", 5, 10)
        diag = Diagnostic(DiagnosticSeverity.WARNING, "test warning", location=loc)
        assert diag.severity == DiagnosticSeverity.WARNING
        assert diag.message == "test warning"
        assert diag.location == loc

    def test_creation_with_notes(self):
        diag = Diagnostic(DiagnosticSeverity.INFO, "test info", notes=("note 1", "note 2"))
        assert diag.notes == ("note 1", "note 2")

    def test_str_representation(self):
        loc = SourceLocation("test.nem", 5, 10)
        diag = Diagnostic(DiagnosticSeverity.ERROR, "test error", location=loc)
        s = str(diag)
        assert "error" in s.lower() or "ERROR" in s
        assert "test error" in s

    def test_frozen(self):
        diag = Diagnostic(DiagnosticSeverity.ERROR, "test")
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            diag.message = "changed"


class TestDiagnosticCollector:
    def test_empty_collector(self):
        collector = DiagnosticCollector()
        assert not collector.has_errors()
        assert collector.get_all() == []

    def test_add_error(self):
        collector = DiagnosticCollector()
        loc = SourceLocation("test.nem", 1, 1)
        collector.error("error message", loc)

        assert collector.has_errors()
        diags = collector.get_all()
        assert len(diags) == 1
        assert diags[0].severity == DiagnosticSeverity.ERROR
        assert diags[0].message == "error message"
        assert diags[0].location == loc

    def test_add_warning(self):
        collector = DiagnosticCollector()
        loc = SourceLocation("test.nem", 2, 3)
        collector.warning("warning message", loc)

        assert not collector.has_errors()  # warnings don't set has_errors
        diags = collector.get_all()
        assert len(diags) == 1
        assert diags[0].severity == DiagnosticSeverity.WARNING
        assert diags[0].message == "warning message"

    def test_add_info(self):
        collector = DiagnosticCollector()
        collector.info("info message")

        assert not collector.has_errors()
        diags = collector.get_all()
        assert len(diags) == 1
        assert diags[0].severity == DiagnosticSeverity.INFO
        assert diags[0].message == "info message"

    def test_multiple_diagnostics(self):
        collector = DiagnosticCollector()
        collector.info("info")
        collector.warning("warning")
        collector.error("error")

        assert collector.has_errors()
        diags = collector.get_all()
        assert len(diags) == 3

    def test_has_errors_only_with_errors(self):
        collector = DiagnosticCollector()
        collector.info("info")
        collector.warning("warning")
        assert not collector.has_errors()

        collector.error("error")
        assert collector.has_errors()

    def test_format_all(self):
        collector = DiagnosticCollector()
        loc = SourceLocation("test.nem", 1, 5)
        collector.error("test error", loc)
        collector.warning("test warning", loc)

        formatted = collector.format_all()
        assert isinstance(formatted, str)
        assert "test error" in formatted
        assert "test warning" in formatted

    def test_format_all_empty(self):
        collector = DiagnosticCollector()
        formatted = collector.format_all()
        assert isinstance(formatted, str)
