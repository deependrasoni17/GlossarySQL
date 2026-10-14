"""Result normalisation, so that equivalent result tables compare equal.

BIRD's EX compares results as *sets of rows*, so voting uses the same notion:
two candidates agree when their row sets match after rounding floats.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def _norm_value(v: Any, ndigits: int) -> Any:
    if isinstance(v, float):
        r = round(v, ndigits)
        return int(r) if r.is_integer() else r
    if isinstance(v, bytes):
        return v.hex()
    return v


def result_key(rows: Iterable[tuple], ndigits: int = 4) -> frozenset:
    """Order-insensitive, duplicate-insensitive key for a result table."""
    return frozenset(tuple(_norm_value(v, ndigits) for v in row) for row in rows)
