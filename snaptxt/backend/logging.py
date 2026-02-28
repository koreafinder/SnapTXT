"""JSON logging helpers placeholder."""

from __future__ import annotations

from typing import Any, Dict


def make_structured_record(event: str, **fields: Any) -> Dict[str, Any]:
    """Return a structured log record suitable for JSON serialization."""
    record = {"event": event, **fields}
    return record
