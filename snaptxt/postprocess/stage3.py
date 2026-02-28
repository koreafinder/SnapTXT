"""Stage 3 postprocessing utilities (spacing → char fixes → ending normalization)."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Sequence, Tuple

from .patterns import stage3_rules


PatternList = Sequence[Tuple[str, str]]


@dataclass(slots=True)
class Stage3Config:
    enable_spacing_normalization: bool = True
    enable_character_fixes: bool = True
    enable_ending_normalization: bool = True
    logger: logging.Logger | None = None


def apply_stage3_rules(text: str, config: Stage3Config | None = None) -> str:
    """Sequentially apply Stage 3 sub-stages with optional toggles."""

    cfg = config or Stage3Config()
    logger = cfg.logger or logging.getLogger(__name__)

    if cfg.enable_spacing_normalization:
        text = _normalize_spacing_overseparation(text, logger)
    if cfg.enable_character_fixes:
        text = _fix_clear_character_errors(text, logger)
    if cfg.enable_ending_normalization:
        text = _normalize_korean_endings(text, logger)

    return text


def _normalize_spacing_overseparation(text: str, logger: logging.Logger) -> str:
    original = text

    spacing_rules = stage3_rules.get_spacing_rules()

    for pattern, replacement in spacing_rules.fixed_patterns:
        text = re.sub(pattern, replacement, text)

    for pattern, replacement in spacing_rules.long_eomis:
        text = re.sub(pattern, replacement, text)

    for josa in spacing_rules.josas:
        text = re.sub(rf'([가-힣]+)\s+{josa}(?=\s)', rf'\1{josa} ', text)
        text = re.sub(rf'([가-힣]+)\s+{josa}(?=\.|$)', rf'\1{josa}', text)

    text = re.sub(r'([가-힣]+)\s+(입니다|입니까)', r'\1\2', text)
    text = re.sub(r'([가-힣]+)\s+지만', r'\1지만', text)

    text = re.sub(r'할\s+수\s+있\s*습\s*니\s*다', '할 수 있습니다', text)
    text = re.sub(r'될\s+수\s+있\s*습\s*니\s*다', '될 수 있습니다', text)
    text = re.sub(r'해\s*보\s*겠\s*습\s*니\s*다', '해보겠습니다', text)

    text = re.sub(r'시\s*작\s*해\s*보\s*겠\s*습\s*니\s*다', '시작해보겠습니다', text)
    text = re.sub(r'시\s*작(?=\s*해)', '시작', text)
    text = re.sub(r'모\s*였(?=\s*습\s*니\s*다)', '모였', text)
    text = re.sub(r'읽\s*고(?=\s)', '읽고 ', text)
    text = re.sub(r'받\s*았(?=\s*습\s*니\s*다)', '받았', text)
    text = re.sub(r'쉽\s*게(?=\s)', '쉽게 ', text)
    text = re.sub(r'증\s*가\s*했\s*습\s*니\s*다', '증가했습니다', text)

    for word in spacing_rules.safe_two_char_words:
        if len(word) == 2:
            pattern = f'{word[0]}\\s+{word[1]}'
            text = re.sub(pattern, word, text)

    text = re.sub(r'([0-9]+)([가-힣]{1,3})(전|후|간|째|번|개|명|일|년|월|시|분|초)(?![가-힣])', r'\1\2 \3', text)
    text = re.sub(r'([A-Za-z]+)([가-힣]{2,})(?![가-힣])', r'\1 \2', text)
    text = re.sub(r'([가-힣]{2,})([A-Z]{2,})(?![A-Za-z])', r'\1 \2', text)
    text = re.sub(r'([가-힣])([\(\)\[\]{}])([가-힣])', r'\1 \2 \3', text)
    text = re.sub(r'([\(\)\[\]{}])([가-힣])', r'\1 \2', text)
    text = re.sub(r'([가-힣])([\(\)\[\]{}])', r'\1 \2', text)
    text = re.sub(r'([가-힣])\s*([.!?])\s*([가-힣])', r'\1\2 \3', text)
    text = re.sub(r'([가-힣])\s*("|\')\s*([가-힣])', r'\1 \2\3', text)
    text = re.sub(r'([가-힣])\s*("|\')\s*([가-힣])', r'\1\2 \3', text)
    text = re.sub(r'(.)\1{3,}', r'\1\1', text)
    text = re.sub(
        r'([가-힣]+)([0-9]+)([가-힣]+)',
        lambda m: f"{m.group(1)} {m.group(2)} {m.group(3)}" if len(m.group(1)) > 1 and len(m.group(3)) > 1 else m.group(0),
        text,
    )

    text = re.sub(r'\s+', ' ', text).strip()

    if text != original:
        logger.debug("Stage 3-1: spacing normalized (%d→%d chars)", len(original), len(text))
    else:
        logger.debug("Stage 3-1: spacing already normalized")

    return text

def _fix_clear_character_errors(text: str, logger: logging.Logger) -> str:
    correction_count = 0

    char_rules = stage3_rules.get_character_rules()

    for wrong, correct in char_rules.replacements.items():
        if wrong in text:
            occurrences = text.count(wrong)
            text = text.replace(wrong, correct)
            correction_count += occurrences

    for wrong, correct in char_rules.contextual:
        if wrong in text:
            occurrences = text.count(wrong)
            text = text.replace(wrong, correct)
            correction_count += occurrences

    for pattern, replacement in char_rules.regex:
        matches = re.findall(pattern, text)
        if matches:
            text = re.sub(pattern, replacement, text)
            correction_count += len(matches)

    if correction_count:
        logger.debug("Stage 3-2: fixed %d character issues", correction_count)
    else:
        logger.debug("Stage 3-2: no character fixes applied")

    return text

def _normalize_korean_endings(text: str, logger: logging.Logger) -> str:
    total_normalizations = 0

    for group in stage3_rules.get_ending_groups():
        category_count = 0
        for pattern, replacement in group.patterns:
            matches = re.findall(pattern, text)
            if matches:
                text = re.sub(pattern, replacement, text)
                category_count += len(matches)

        if category_count:
            total_normalizations += category_count
            logger.debug("Stage 3-3: %s (%d replacements)", group.name, category_count)

    if total_normalizations:
        logger.debug("Stage 3-3: normalized %d endings", total_normalizations)
    else:
        logger.debug("Stage 3-3: no ending adjustments needed")

    return text
