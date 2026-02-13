"""NEM decorator kind definitions."""

from __future__ import annotations

from enum import Enum


class DecoratorKind(Enum):
    """All NEM decorator kinds from the spec."""

    # Semantic decorators (normative)
    MATERIALIZED = "materialized"
    DETERMINISTIC = "deterministic"
    MEMMOVE = "memmove"
    READONLY = "readonly"
    WRITEONLY = "writeonly"
    MAX_IN_FLIGHT = "max_in_flight"
    RESOURCE = "resource"

    # Informational decorators
    DEBUG = "debug"
    PROFILE = "profile"

    @classmethod
    def from_name(cls, name: str) -> DecoratorKind | None:
        """Look up a decorator kind by its source-level name."""
        for member in cls:
            if member.value == name:
                return member
        return None
