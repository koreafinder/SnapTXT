"""Stage 3.5: Sentence boundary processing for TTS-friendly output."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass(slots=True)
class Stage3_5Config:
    enable_sentence_boundary_fix: bool = True
    enable_tts_friendly_symbols: bool = True
    enable_korean_quotes: bool = True
    enable_number_reading_format: bool = False  # Optional for advanced TTS
    logger: logging.Logger | None = None


def apply_stage3_5_rules(text: str, config: Stage3_5Config | None = None) -> str:
    """Apply TTS-friendly sentence boundary and symbol processing."""
    cfg = config or Stage3_5Config()
    logger = cfg.logger or logging.getLogger(__name__)
    
    if cfg.enable_sentence_boundary_fix:
        text = _fix_sentence_boundaries(text, logger)
    
    if cfg.enable_tts_friendly_symbols:
        text = _convert_tts_friendly_symbols(text, logger)
    
    if cfg.enable_korean_quotes:
        text = _apply_korean_style_quotes(text, logger)
    
    if cfg.enable_number_reading_format:
        text = _convert_number_reading_format(text, logger)
    
    return text


def _fix_sentence_boundaries(text: str, logger: logging.Logger) -> str:
    """Fix sentence boundaries for proper TTS breathing and rhythm."""
    original = text
    changes = 0
    
    # 1. 마침표/물음표/느낌표 뒤 공백 정리
    # "습니다.오프라" → "습니다. 오프라"
    sentence_endings = ['.', '!', '?']
    for ending in sentence_endings:
        pattern = f'\\{ending}(?=[가-힣A-Za-z0-9])'
        replacement = f'{ending} '
        matches_before = len(re.findall(pattern, text))
        text = re.sub(pattern, replacement, text)
        matches_after = len(re.findall(pattern, text))
        changes += matches_before - matches_after
    
    # 2. 문장 시작 공백 정리 및 첫 글자 확인
    # "   마이클싱어" → " 마이클싱어" (과도한 공백 제거)
    before_spacing = text
    text = re.sub(r'([.!?])\s{2,}', r'\1 ', text)
    changes += 1 if text != before_spacing else 0
    
    # 3. 문단 끝 정리 (연속된 마침표 정리)
    # "습니다..." → "습니다."
    text = re.sub(r'\.{2,}', '.', text)
    
    # 4. 콜론 뒤 공백 정리
    # "습니다:방송" → "습니다: 방송"
    text = re.sub(r':(?=[가-힣])', ': ', text)
    
    if changes > 0:
        logger.debug("Stage 3.5-1: fixed %d sentence boundary issues", changes)
    else:
        logger.debug("Stage 3.5-1: no sentence boundary fixes needed")
    
    return text


def _convert_tts_friendly_symbols(text: str, logger: logging.Logger) -> str:
    """Convert symbols to TTS-friendly format."""
    original = text
    changes = 0
    
    # 1. 세미콜론 제거 또는 쉼표로 변환
    # "미술; 교육; 보건" → "미술, 교육, 보건"
    semicolon_pattern = r'([가-힣])\s*;\s*([가-힣])'
    text = re.sub(semicolon_pattern, r'\1, \2', text)
    changes += len(re.findall(semicolon_pattern, original))
    
    # 2. @ 기호 처리
    # "@GettyImages" → "(GettyImages 제공)"
    at_pattern = r'@([A-Za-z]+[A-Za-z0-9]*)'
    text = re.sub(at_pattern, r'(\1 제공)', text)
    changes += len(re.findall(at_pattern, original))
    
    # 3. URL 간소화
    # "www.untetheredsoul.com" → "언테더드 소울 닷컴"
    text = re.sub(r'www\.untetheredsoul\.com', '언테더드 소울 닷컴', text)
    
    # 4. 과도한 특수문자 제거
    # "!!!" → "!"
    text = re.sub(r'!{2,}', '!', text)
    text = re.sub(r'\?{2,}', '?', text)
    
    if changes > 0:
        logger.debug("Stage 3.5-2: converted %d TTS-unfriendly symbols", changes)
    else:
        logger.debug("Stage 3.5-2: no symbol conversions needed")
    
    return text


def _apply_korean_style_quotes(text: str, logger: logging.Logger) -> str:
    """Convert to Korean-style quotation marks for better readability."""
    original = text
    changes = 0
    
    # 1. 책 제목용 따옴표
    # "(상처받지 않는 영혼)" → "《상처받지 않는 영혼》"
    book_pattern = r'\(\s*([가-힣\s]+[가-힣]+)\s*\)'
    matches = re.findall(book_pattern, text)
    for match in matches:
        if len(match.strip()) > 3:  # 책 제목으로 보이는 경우만
            text = text.replace(f'({match})', f'《{match.strip()}》')
            changes += 1
    
    # 2. 프로그램명 따옴표
    # "<슈퍼 소울 선데이>" → "〈슈퍼 소울 선데이〉"
    program_pattern = r'<\s*([가-힣\s]+[가-힣]+)\s*>'
    matches = re.findall(program_pattern, text)
    for match in matches:
        if len(match.strip()) > 2:  # 프로그램명으로 보이는 경우만
            text = text.replace(f'<{match}>', f'〈{match.strip()}〉')
            changes += 1
    
    # 3. 일반 인용문 (수정된 부분)
    # '"얼굴 없는"' → "'얼굴 없는'"
    text = re.sub(r'"([^"]+)"', r"'\1'", text)
    
    if changes > 0:
        logger.debug("Stage 3.5-3: applied %d Korean-style quote conversions", changes)
    else:
        logger.debug("Stage 3.5-3: no quote conversions needed")
    
    return text


def _convert_number_reading_format(text: str, logger: logging.Logger) -> str:
    """Convert numbers to Korean reading format (optional for advanced TTS)."""
    original = text
    changes = 0
    
    # 년도 변환 (선택적)
    # "1970년대" → "천구백칠십년대" 
    year_pattern = r'(\d{4})년대'
    matches = re.findall(year_pattern, text)
    for year_str in matches:
        year_num = int(year_str)
        if 1900 <= year_num <= 2100:  # 실제 년도로 보이는 경우만
            korean_year = _convert_year_to_korean(year_num)
            text = text.replace(f'{year_str}년대', f'{korean_year}년대')
            changes += 1
    
    # 순위 변환
    # "1위" → "일위"
    ranking_pattern = r'(\d+)위'
    text = re.sub(ranking_pattern, lambda m: f'{_convert_small_number_to_korean(int(m.group(1)))}위', text)
    
    if changes > 0:
        logger.debug("Stage 3.5-4: converted %d numbers to reading format", changes)
    else:
        logger.debug("Stage 3.5-4: no number conversions applied")
    
    return text


def _convert_year_to_korean(year: int) -> str:
    """Convert year number to Korean reading format."""
    digits = [
        '', '일', '이', '삼', '사', '오', '육', '칠', '팔', '구'
    ]
    
    thousands = year // 1000
    hundreds = (year % 1000) // 100
    tens = (year % 100) // 10
    ones = year % 10
    
    result = ''
    if thousands > 0:
        result += digits[thousands] + '천'
    if hundreds > 0:
        result += digits[hundreds] + '백'
    if tens > 0:
        result += digits[tens] + '십'
    if ones > 0:
        result += digits[ones]
    
    return result


def _convert_small_number_to_korean(num: int) -> str:
    """Convert small numbers (1-99) to Korean."""
    if num <= 0 or num > 99:
        return str(num)
    
    digits = ['', '일', '이', '삼', '사', '오', '육', '칠', '팔', '구']
    
    if num < 10:
        return digits[num]
    
    tens_digit = num // 10
    ones_digit = num % 10
    
    result = ''
    if tens_digit > 1:
        result += digits[tens_digit] + '십'
    elif tens_digit == 1:
        result += '십'
    
    if ones_digit > 0:
        result += digits[ones_digit]
    
    return result