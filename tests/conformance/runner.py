"""Conformance test runner protocol and result types."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ValidationResult:
    """Result of validating a NEM program."""
    valid: bool
    diagnostics: list[str] = field(default_factory=list)


class ConformanceRunner(Protocol):
    """Tool-agnostic interface for conformance testing."""

    name: str

    def validate(self, source: str, device_config: str | None = None) -> ValidationResult:
        """Parse and validate a NEM program. Returns validation result."""
        ...
