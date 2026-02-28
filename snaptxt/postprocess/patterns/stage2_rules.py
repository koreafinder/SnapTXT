"""Stage 2 rule loader with hot-reload support.

이 모듈은 Stage 2 교정 사전을 YAML 파일로부터 불러오고, 파일 변경을 감지하면
자동으로 캐시를 갱신한다. 실험 상황에서는 ``SNAPTXT_STAGE2_RULES_FILE`` 환경
변수로 다른 YAML 파일을 가리킨 뒤 :func:`reload_replacements` 를 호출하면 된다.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import RLock
from typing import Dict


_RULES_ENV_VAR = "SNAPTXT_STAGE2_RULES_FILE"
_CACHE: Dict[str, str] = {}
_CACHE_MTIME: float | None = None
_LOCK = RLock()


def _rules_path() -> Path:
    override = os.getenv(_RULES_ENV_VAR)
    if override:
        return Path(override)
    return Path(__file__).with_name("stage2_rules.yaml")


def _parse_yaml(text: str) -> Dict[str, str]:
    replacements: Dict[str, str] = {}
    active_block = None
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.endswith(":") and not stripped.startswith("-"):
            active_block = stripped[:-1]
            continue

        if active_block != "replacements" or ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.split("#", 1)[0].strip().strip("\"").strip("'")
        if key:
            replacements[key] = value
    return replacements


def _refresh_cache(force: bool = False) -> None:
    global _CACHE_MTIME
    rules_file = _rules_path()
    try:
        mtime = rules_file.stat().st_mtime
    except OSError as exc:  # pragma: no cover - catastrophic configuration issue
        raise FileNotFoundError(f"Stage 2 rules file not found: {rules_file}") from exc

    if not force and _CACHE and _CACHE_MTIME and mtime <= _CACHE_MTIME:
        return

    parsed = _parse_yaml(rules_file.read_text(encoding="utf-8"))
    if not parsed:
        raise ValueError(f"No Stage 2 replacements loaded from {rules_file}")

    _CACHE.clear()
    _CACHE.update(parsed)
    _CACHE_MTIME = mtime


def get_replacements(*, force_refresh: bool = False) -> Dict[str, str]:
    with _LOCK:
        _refresh_cache(force_refresh)
        return _CACHE


def reload_replacements() -> Dict[str, str]:
    """강제로 YAML 파일을 다시 읽어 캐시를 갱신한다."""

    return get_replacements(force_refresh=True)


def rules_file_path() -> Path:
    """현재 Stage 2 룰 파일 경로를 반환한다."""

    return _rules_path()


OCR_REPLACEMENTS = get_replacements(force_refresh=True)
