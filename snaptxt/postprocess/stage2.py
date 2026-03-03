"""Stage 2 postprocessing: dictionary, regex, and context-aware corrections."""

from __future__ import annotations

import logging
import time

from dataclasses import dataclass
from typing import Dict, Tuple

from .patterns.stage2_rules import OCR_REPLACEMENTS
from .stage2_patterns import apply_contextual_patterns, apply_dynamic_patterns, apply_spacing_refinements


@dataclass(slots=True)
class Stage2Config:
    enable_contextual_rules: bool = True
    enable_spacing_refinements: bool = True
    logger: logging.Logger | None = None


def apply_stage2_rules(text: str, config: Stage2Config | None = None) -> str:
    cfg = config or Stage2Config()
    logger = cfg.logger or logging.getLogger(__name__)
    
    original_text = text
    total_changes = 0

    # 1. 사전 기반 교정
    text, replace_count = _apply_static_replacements(text, OCR_REPLACEMENTS)
    total_changes += replace_count
    if replace_count:
        logger.debug(f"      📚 사전 교정: {replace_count}개 패턴 적용")

    # 2. 동적 패턴 매칭
    before = text
    text = apply_dynamic_patterns(text)
    dynamic_changes = len(before) - len(text) if before != text else 0
    if before != text:
        total_changes += abs(dynamic_changes)
        logger.debug(f"      🔍 동적 패턴: {abs(dynamic_changes)}자 변경")

    # 3. 문맥 인식 교정
    if cfg.enable_contextual_rules:
        before = text
        text = apply_contextual_patterns(text)
        if before != text:
            contextual_changes = abs(len(text) - len(before))
            total_changes += contextual_changes
            logger.debug(f"      🧠 문맥 인식: {contextual_changes}자 조정")

    # 4. 띄어쓰기 정제
    if cfg.enable_spacing_refinements:
        before = text
        text = apply_spacing_refinements(text)
        if before != text:
            spacing_changes = abs(len(text) - len(before))
            total_changes += spacing_changes
            logger.debug(f"      📏 띄어쓰기: {spacing_changes}자 조정")
    
    # 전체 Stage2 결과 요약
    if total_changes > 0:
        change_ratio = abs(len(text) - len(original_text)) / len(original_text) * 100
        logger.debug(f"      ✅ Stage2 총 변화: {total_changes}개 수정, {change_ratio:.2f}%")

    return text


def _apply_static_replacements(text: str, replacements: Dict[str, str]) -> Tuple[str, int]:
    count = 0
    for wrong, correct in replacements.items():
        if wrong == correct:
            continue
        occurrences = text.count(wrong)
        if not occurrences:
            continue
        text = text.replace(wrong, correct)
        count += occurrences
    return text, count
