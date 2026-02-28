#!/usr/bin/env python3
"""Compatibility shim for the relocated EasyOCR worker module."""

from __future__ import annotations

from snaptxt.backend.worker import easyocr_worker as _impl
from snaptxt.backend.worker.easyocr_worker import *  # noqa: F401,F403

__all__ = getattr(
    _impl,
    "__all__",
    [name for name in dir(_impl) if not name.startswith("_")],
)


def main() -> None:
    """Reuse the backend worker CLI."""

    _impl.main()


if __name__ == "__main__":
    main()
