"""Bridges the legacy MultiOCRProcessor into the new package layout."""

from __future__ import annotations

from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def load_default_engine() -> Any:
    """Return a singleton instance of the legacy MultiOCRProcessor."""

    from multi_ocr_processor import MultiOCRProcessor  # Local import to avoid cycles

    return MultiOCRProcessor()
