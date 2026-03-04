"""Stage 3 postprocessing utilities (spacing → char fixes → ending normalization)."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import time
import unicodedata
from typing import Any, Callable, Sequence, Tuple, TYPE_CHECKING

try:  # Optional dependency
    from hanspell import spell_checker as _spell_checker
except ImportError:  # pragma: no cover - optional dependency
    _spell_checker = None

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from pykospacing import Spacing as _SpacingType
else:  # pragma: no cover - fallback for runtime typing
    _SpacingType = Any

try:  # Optional dependency
    from pykospacing import Spacing as _SpacingClass
except ImportError:  # pragma: no cover - optional dependency
    _SpacingClass = None

try:  # Optional dependency
    import ftfy as _ftfy
except ImportError:  # pragma: no cover - optional dependency
    _ftfy = None

from .patterns import stage3_rules
from .stage3_5 import apply_stage3_5_rules, Stage3_5Config


PatternList = Sequence[Tuple[str, str]]


SpellcheckHandler = Callable[[str], str]
SpacingHandler = Callable[[str], str]
NormalizerHandler = Callable[[str], str]


_KOSPACING_INSTANCE: _SpacingType | None = None


@dataclass(slots=True)
class Stage3Config:
    enable_spacing_normalization: bool = True
    enable_character_fixes: bool = True
    enable_ending_normalization: bool = True
    enable_spellcheck_enhancement: bool = True
    enable_punctuation_normalization: bool = True
    enable_paragraph_formatting: bool = True  # 문단 나누기 기능 추가
    enable_tts_friendly_processing: bool = False  # 비활성화: 웹에서 TTS 처리할 예정
    tts_config: Stage3_5Config | None = None  # Configuration for TTS processing
    spellcheck_handler: SpellcheckHandler | None = None
    spacing_refiner: SpacingHandler | None = None
    punctuation_normalizer: NormalizerHandler | None = None
    logger: logging.Logger | None = None


def apply_stage3_rules(text: str, config: Stage3Config | None = None) -> str:
    """Sequentially apply Stage 3 sub-stages with optional toggles."""

    cfg = config or Stage3Config()
    logger = cfg.logger or logging.getLogger(__name__)
    
    original_text = text
    stage_changes = []

    if cfg.enable_spacing_normalization:
        before = text
        text = _normalize_spacing_overseparation(text, logger)
        if before != text:
            change = abs(len(text) - len(before))
            stage_changes.append(f"띄어쓰기: {change}자")
            logger.debug(f"      📏 띄어쓰기 정규화: {change}자 조정")

    if cfg.enable_character_fixes:
        before = text
        text = _fix_clear_character_errors(text, logger)
        if before != text:
            change = abs(len(text) - len(before))
            stage_changes.append(f"문자교정: {change}자")
            logger.debug(f"      🔧 문자 오류 수정: {change}자 교정")

    if cfg.enable_ending_normalization:
        before = text
        text = _normalize_korean_endings(text, logger)
        if before != text:
            change = abs(len(text) - len(before))
            stage_changes.append(f"어미정리: {change}자")
            logger.debug(f"      📝 한국어 어미: {change}자 정규화")

    if cfg.enable_spellcheck_enhancement:
        before = text
        text = _apply_spellcheck_and_spacing(text, cfg, logger)
        if before != text:
            change = abs(len(text) - len(before))
            stage_changes.append(f"맞춤법: {change}자")
            logger.debug(f"      ✏️ 맞춤법 검사: {change}자 수정")

    if cfg.enable_punctuation_normalization:
        before = text
        text = _normalize_symbols_and_quotes(text, cfg, logger)
        if before != text:
            change = abs(len(text) - len(before))
            stage_changes.append(f"구두점: {change}자")
            logger.debug(f"      🔤 구두점 정규화: {change}자 조정")

    if cfg.enable_paragraph_formatting:
        before = text
        text = _add_paragraph_breaks(text, logger)
        if before != text:
            change = abs(len(text) - len(before))
            stage_changes.append(f"문단: {change}자")
            logger.debug(f"      📄 문단 구분: {change}자 추가")

    if cfg.enable_tts_friendly_processing:
        before = text
        tts_cfg = cfg.tts_config or Stage3_5Config(logger=logger)
        text = apply_stage3_5_rules(text, tts_cfg)
        if before != text:
            change = abs(len(text) - len(before))
            stage_changes.append(f"TTS: {change}자")
            logger.debug(f"      🔊 TTS 최적화: {change}자 조정")

    # Stage3 전체 결과 요약
    if stage_changes:
        total_change = abs(len(text) - len(original_text))
        logger.debug(f"      ✅ Stage3 세부 처리: {', '.join(stage_changes)} (총 {total_change}자)")
    else:
        logger.debug(f"      ⚪ Stage3 변경 없음 (입력 품질 양호)")

    return text


def _normalize_spacing_overseparation(text: str, logger: logging.Logger) -> str:
    original = text

    spacing_rules = stage3_rules.get_spacing_rules()

    for pattern, replacement in spacing_rules.fixed_patterns:
        text = re.sub(pattern, replacement, text)

    for pattern, replacement in spacing_rules.long_eomis:
        text = re.sub(pattern, replacement, text)

    text = re.sub(r'(?<=[은는이가을를의과와도만])-\s+', ' ', text)
    text = re.sub(r'(?<=[은는이가을를의과와도만])-(?=[가-힣])', '', text)

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

    # === 자연스러운 한국어 단어 복원 (과분리 수정) ===
    natural_words = [
        '낯선', '영혼', '사람', '마음', '생활', '명상', '평화', '체험', 
        '강연', '반향', '저서', '번역', '소개', '침묵', '여행', '안내',
        '독자', '사랑', '대학교', '박사', '과정', '내면', '요가', 
        '센터', '미술', '교육', '보건', '환경', '보호', '분야', '기여',
        '다이어리', '명상가', '부탁', '출간', '모습', '욕망', '굴레',
        '자유', '책들', '꾸준히', '은둔', '몰두', '내적'
    ]
    for word in natural_words:
        if len(word) == 2:
            pattern = f'{word[0]}\\s+{word[1]}'
            text = re.sub(pattern, word, text)
        elif len(word) == 3:
            # 3글자 단어: 첫번째-두번째 or 두번째-세번째 분리 복원
            pattern1 = f'{word[0]}\\s+{word[1:3]}'  # 첫-나머지
            pattern2 = f'{word[0:2]}\\s+{word[2]}'  # 앞두글자-마지막
            text = re.sub(pattern1, word, text)
            text = re.sub(pattern2, word, text)

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


def _apply_spellcheck_and_spacing(text: str, cfg: Stage3Config, logger: logging.Logger) -> str:
    spellcheck = cfg.spellcheck_handler or _spellcheck_with_hanspell
    spacing = cfg.spacing_refiner or _spacing_with_pykospacing

    intermediate = spellcheck(text) if spellcheck else text
    result = spacing(intermediate) if spacing else intermediate

    if result != text:
        logger.debug("Stage 3-4: spellcheck/spacing enhancement applied")
    else:
        logger.debug("Stage 3-4: spellcheck/spacing skipped")

    return result


def _normalize_symbols_and_quotes(text: str, cfg: Stage3Config, logger: logging.Logger) -> str:
    normalizer = cfg.punctuation_normalizer or _default_punctuation_normalizer
    if not normalizer:
        logger.debug("Stage 3-5: no punctuation normalizer available")
        return text

    result = normalizer(text)
    if result != text:
        logger.debug("Stage 3-5: punctuation normalized")
    else:
        logger.debug("Stage 3-5: punctuation already normalized")
    return result


def _spellcheck_with_hanspell(text: str) -> str:
    if _spell_checker is None:
        return text
    try:
        checked = _spell_checker.check(text)
    except Exception:  # pragma: no cover - network / dependency error
        return text
    corrected = getattr(checked, "checked", None)
    if isinstance(corrected, str) and corrected:
        return corrected
    return text


def _spacing_with_pykospacing(text: str) -> str:
    instance = _get_spacing_instance()
    if instance is None:
        return text
    try:
        return instance(text)
    except Exception:  # pragma: no cover - runtime spacing failure
        return text


def _get_spacing_instance() -> _SpacingType | None:
    global _KOSPACING_INSTANCE
    if _SpacingClass is None:
        return None
    if _KOSPACING_INSTANCE is None:
        _KOSPACING_INSTANCE = _SpacingClass()
    return _KOSPACING_INSTANCE


_UNTETHEREDSOUL_PATTERN = re.compile(r"(?i)WW\s+www\s*\.?\s*untetheredsoul\s*\.?\s*com|www\s*\.?\s*www\s*\.?\s*untetheredsoul\s*\.?\s*com|www\s*\.?\s+untetheredsoul\s*\.?\s+com|www\s*\.?\s*untetheredsoul\s*\.?\s*com")
_L_NUMBER_PATTERN = re.compile(r"\bl\s+위에\b")
_EOLCUT_PATTERN = re.compile(r"을\s*컷\s*고|을\s*컫\s*고|을\s*켉\s*고")


def _default_punctuation_normalizer(text: str) -> str:
    normalized = text
    if _ftfy is not None:
        try:
            normalized = _ftfy.fix_text(normalized)
        except Exception:  # pragma: no cover - ftfy internal failure
            normalized = text
    normalized = unicodedata.normalize("NFC", normalized)
    normalized = _UNTETHEREDSOUL_PATTERN.sub("www.untetheredsoul.com", normalized)
    normalized = _L_NUMBER_PATTERN.sub("1위에", normalized)
    normalized = _EOLCUT_PATTERN.sub("올랐고", normalized)
    return normalized


def _add_paragraph_breaks(text: str, logger: logging.Logger) -> str:
    """적절한 위치에 문단 구분을 위한 개행을 추가합니다."""
    
    if not text.strip():
        return text
    
    # 긴 연속 문장을 문단으로 나누기
    # ': ' 이후 새로운 문장이 시작할 때 개행 추가
    text = re.sub(r':\s+([가-힣A-Z])', r':\n\n\1', text)
    
    # 문장이 끝나고(. ! ?) 160자 이상 연속될 때 개행 추가 
    sentences = re.split(r'([.!?])\s*', text)
    result_parts = []
    current_length = 0
    
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i]
        punctuation = sentences[i + 1] if i + 1 < len(sentences) else ''
        
        result_parts.append(sentence + punctuation)
        current_length += len(sentence) + len(punctuation)
        
        # 160자 이상이고 다음 문장이 있을 때 문단 나누기
        if current_length > 160 and i + 2 < len(sentences):
            next_sentence = sentences[i + 2].strip()
            if next_sentence and (next_sentence[0].isalpha() or '가' <= next_sentence[0] <= '힣'):
                result_parts.append('\n\n')
                current_length = 0
            else:
                result_parts.append(' ')
        elif i + 2 < len(sentences):
            result_parts.append(' ')
    
    # 마지막 문장 추가 (구두점이 없어서 분할되지 않은 경우도 처리)        
    if len(sentences) > 1:
        result_parts.append(sentences[-1])
    elif len(sentences) == 1:
        # 구두점이 없는 단일 문장인 경우
        result_parts.append(sentences[0])
        
    final_text = ''.join(result_parts)
    
    # 연속된 개행 정리
    final_text = re.sub(r'\n{3,}', '\n\n', final_text)
    
    logger.debug(f"문단 나누기 완료: {len(final_text)}자")
    return final_text.strip()
