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
_CACHE_MTIME_BASE: float | None = None
_CACHE_MTIME_OVERLAY: float | None = None  # overlay mtime 추가
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
    global _CACHE_MTIME_BASE, _CACHE_MTIME_OVERLAY
    rules_file = _rules_path()
    try:
        base_mtime = rules_file.stat().st_mtime
    except OSError as exc:  # pragma: no cover - catastrophic configuration issue
        raise FileNotFoundError(f"Stage 2 rules file not found: {rules_file}") from exc

    # overlay mtime도 함께 체크 (감독관 지시 4번)
    from .stage2_overlay_loader import get_overlay_file_info
    overlay_info = get_overlay_file_info()
    overlay_mtime = overlay_info.get("overlay_mtime", 0) or 0

    if not force and _CACHE and _CACHE_MTIME_BASE and _CACHE_MTIME_OVERLAY is not None:
        if base_mtime <= _CACHE_MTIME_BASE and overlay_mtime <= _CACHE_MTIME_OVERLAY:
            return

    # Base rules 로드
    parsed = _parse_yaml(rules_file.read_text(encoding="utf-8"))
    if not parsed:
        raise ValueError(f"No Stage 2 replacements loaded from {rules_file}")

    # Overlay 로드 및 병합 (SNAPTXT_DISABLE_OVERLAY 체크)
    if not os.getenv("SNAPTXT_DISABLE_OVERLAY"):
        from .stage2_overlay_loader import load_stage2_overlay, apply_overlay_safe_limits
        overlay_rules, overlay_info_msg = load_stage2_overlay()
        
        if overlay_rules:
            limited_overlay, policy_info = apply_overlay_safe_limits(overlay_rules)
            parsed.update(limited_overlay)
            print(f"📊 Stage2 Overlay: {overlay_info_msg}")
            print(f"📊 Overlay 제한: {policy_info}")

    _CACHE.clear()
    _CACHE.update(parsed)
    _CACHE_MTIME_BASE = base_mtime
    _CACHE_MTIME_OVERLAY = overlay_mtime


def get_replacements(*, force_refresh: bool = False) -> Dict[str, str]:
    with _LOCK:
        _refresh_cache(force_refresh)
        return _CACHE


def reload_replacements() -> Dict[str, str]:
    """강제로 YAML 파일을 다시 읽어 캐시를 갱신한다."""

    return get_replacements(force_refresh=True)


def get_runtime_rule_info() -> dict:
    """관측용: 실제 사용 파일 정보 (side-effect 최소화 - 감독관 지시 9번)"""
    base_path = _rules_path()
    
    # Base 파일 정보
    base_info = {
        "base_path": str(base_path),
        "base_mtime": base_path.stat().st_mtime if base_path.exists() else 0,
        "base_hash": "none"
    }
    
    # Base 해시 계산 (파일이 있을 때만)
    if base_path.exists():
        import hashlib
        base_info["base_hash"] = hashlib.md5(base_path.read_bytes()).hexdigest()[:8]
    
    # Overlay 파일 정보만 (파싱하지 않음)
    from .stage2_overlay_loader import get_overlay_file_info
    overlay_info = get_overlay_file_info()
    
    base_info.update({
        "overlay_file": overlay_info.get("overlay_file"),
        "overlay_mtime": overlay_info.get("overlay_mtime"),
        "overlay_path": overlay_info.get("overlay_path")
    })
    
    return base_info


OCR_REPLACEMENTS = get_replacements(force_refresh=True)
