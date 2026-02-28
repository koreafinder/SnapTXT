"""Stage 2 postprocessing: dictionary, regex, and context-aware corrections."""

from __future__ import annotations

import logging

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

    text, replace_count = _apply_static_replacements(text, OCR_REPLACEMENTS)
    if replace_count:
        logger.debug("Stage 2: applied %d dictionary replacements", replace_count)

    before = text
    text = apply_dynamic_patterns(text)
    if before != text:
        logger.debug("Stage 2: dynamic regex patterns adjusted text")

    if cfg.enable_contextual_rules:
        before = text
        text = apply_contextual_patterns(text)
        if before != text:
            logger.debug("Stage 2: contextual patterns adjusted sentences")

    if cfg.enable_spacing_refinements:
        before = text
        text = apply_spacing_refinements(text)
        if before != text:
            logger.debug("Stage 2: spacing refinements applied")

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
