"""NEM memory hierarchy level definitions."""

from __future__ import annotations

from enum import Enum


class MemoryLevel(Enum):
    """NEM memory hierarchy levels."""

    DDR = "DDR"
    L2 = "L2"
    L1 = "L1"
