"""Structured JSON logging utilities for backend components."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_DEFAULT_DIR = Path(os.getenv("SNAPTXT_LOG_DIR", "logs"))
_DEFAULT_FILE = Path(os.getenv("SNAPTXT_JSON_LOG", _DEFAULT_DIR / "snaptxt_ocr.jsonl"))
_LOGGER_TARGETS: Dict[str, str] = {}


def _resolve_target(path_hint: Optional[str | Path]) -> Path:
    target = Path(path_hint) if path_hint else _DEFAULT_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def get_json_logger(name: str, log_file: Optional[str | Path] = None) -> logging.Logger:
    """Return a logger configured to write JSON lines to disk."""

    logger = logging.getLogger(name)
    target = str(_resolve_target(log_file))
    if _LOGGER_TARGETS.get(name) != target:
        for handler in list(logger.handlers):
            if getattr(handler, "_snaptxt_json", False):
                logger.removeHandler(handler)
        handler = logging.FileHandler(target, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler._snaptxt_json = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
        logger.setLevel(os.getenv("SNAPTXT_JSON_LOG_LEVEL", "INFO"))
        logger.propagate = False
        _LOGGER_TARGETS[name] = target
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


def log_event(logger: logging.Logger, event: str, **payload: Any) -> None:
    """Emit a structured JSON log entry using the provided logger."""

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **payload,
    }
    try:
        logger.info(json.dumps(record, ensure_ascii=False))
    except Exception:
        logger.exception("Failed to write structured log", exc_info=True)
