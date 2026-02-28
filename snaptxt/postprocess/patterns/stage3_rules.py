"""Stage 3 rule loader with YAML + hot-reload support."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from threading import RLock
from typing import Dict, List, Sequence, Tuple

import yaml


PatternList = List[Tuple[str, str]]


@dataclass(slots=True)
class SpacingRules:
    fixed_patterns: PatternList
    long_eomis: PatternList
    josas: Tuple[str, ...]
    safe_two_char_words: Tuple[str, ...]


@dataclass(slots=True)
class CharacterRules:
    replacements: Dict[str, str]
    contextual: PatternList
    regex: PatternList


@dataclass(slots=True)
class EndingGroup:
    name: str
    patterns: PatternList


@dataclass(slots=True)
class Stage3Rules:
    spacing: SpacingRules
    characters: CharacterRules
    ending_groups: Tuple[EndingGroup, ...]


_RULES_ENV_VAR = "SNAPTXT_STAGE3_RULES_FILE"
_CACHE: Stage3Rules | None = None
_CACHE_MTIME: float | None = None
_LOCK = RLock()


def _rules_path() -> Path:
    override = os.getenv(_RULES_ENV_VAR)
    if override:
        return Path(override)
    return Path(__file__).with_name("stage3_rules.yaml")


def _parse_pattern_list(data: Sequence[dict] | None) -> PatternList:
    patterns: PatternList = []
    if not data:
        return patterns
    for entry in data:
        pattern = entry.get("pattern", entry.get("wrong"))
        if pattern is None:
            continue
        replacement = entry.get("replacement", entry.get("correct", ""))
        patterns.append((str(pattern), str(replacement)))
    return patterns


def _parse_spacing(data: dict | None) -> SpacingRules:
    data = data or {}
    return SpacingRules(
        fixed_patterns=_parse_pattern_list(data.get("fixed_patterns")),
        long_eomis=_parse_pattern_list(data.get("long_eomis")),
        josas=tuple(str(item) for item in data.get("josas", []) if str(item)),
        safe_two_char_words=tuple(str(item) for item in data.get("safe_two_char_words", []) if str(item)),
    )


def _parse_characters(data: dict | None) -> CharacterRules:
    data = data or {}
    replacements_map = data.get("replacements", {})
    replacements = {str(k): str(v) for k, v in replacements_map.items()}
    contextual = _parse_pattern_list(data.get("contextual"))
    regex = _parse_pattern_list(data.get("regex"))
    return CharacterRules(replacements=replacements, contextual=contextual, regex=regex)


def _parse_endings(data: Sequence[dict] | None) -> Tuple[EndingGroup, ...]:
    groups: List[EndingGroup] = []
    if not data:
        return tuple()
    for entry in data:
        name = str(entry.get("name", ""))
        if not name:
            continue
        patterns = _parse_pattern_list(entry.get("patterns"))
        groups.append(EndingGroup(name=name, patterns=patterns))
    return tuple(groups)


def _load_rules_from_file(rules_file: Path) -> Stage3Rules:
    raw = rules_file.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    spacing = _parse_spacing(data.get("spacing"))
    characters = _parse_characters(data.get("characters"))
    endings = _parse_endings(data.get("endings"))
    return Stage3Rules(spacing=spacing, characters=characters, ending_groups=endings)


def _refresh_cache(force: bool = False) -> None:
    global _CACHE, _CACHE_MTIME
    rules_file = _rules_path()
    try:
        mtime = rules_file.stat().st_mtime
    except OSError as exc:  # pragma: no cover - catastrophic configuration issue
        raise FileNotFoundError(f"Stage 3 rules file not found: {rules_file}") from exc

    if not force and _CACHE is not None and _CACHE_MTIME and mtime <= _CACHE_MTIME:
        return

    loaded = _load_rules_from_file(rules_file)
    _CACHE = loaded
    _CACHE_MTIME = mtime


def _get_rules(force_refresh: bool = False) -> Stage3Rules:
    with _LOCK:
        _refresh_cache(force_refresh)
        if _CACHE is None:
            raise RuntimeError("Stage 3 rules failed to load")
        return _CACHE


def get_spacing_rules(*, force_refresh: bool = False) -> SpacingRules:
    return _get_rules(force_refresh).spacing


def get_character_rules(*, force_refresh: bool = False) -> CharacterRules:
    return _get_rules(force_refresh).characters


def get_ending_groups(*, force_refresh: bool = False) -> Tuple[EndingGroup, ...]:
    return _get_rules(force_refresh).ending_groups


def reload_rules() -> Stage3Rules:
    """강제로 Stage 3 룰을 다시 읽어 캐시를 갱신한다."""

    return _get_rules(force_refresh=True)


def rules_file_path() -> Path:
    """현재 Stage 3 룰 파일 경로."""

    return _rules_path()


# Prime cache at import time for immediate availability.
reload_rules()
