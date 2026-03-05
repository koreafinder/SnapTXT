"""EasyOCR Worker Stage2/Stage3 메타데이터 처리기 - 호환성 유지"""

import sys
from typing import Optional
from snaptxt.postprocess.stage2 import Stage2Config, apply_stage2_rules
from snaptxt.postprocess.stage3 import Stage3Config, apply_stage3_rules
from snaptxt.postprocess.patterns.stage_scope_guard import (
    StageMetadata, should_apply_rule, mark_rule_applied, log_stage_summary
)

def advanced_korean_text_processor_with_metadata(text: str, metadata: Optional[StageMetadata] = None) -> str:
    """기존 호출 방식 유지, metadata는 옵션 (감독관 지시 호환성 유지)"""
    
    if not text:
        print(f"🔍 [DEBUG] 빈 텍스트 입력", file=sys.stderr)
        return ""

    print(f"🔍 [DEBUG] 처리 전: {len(text)}자", file=sys.stderr)
    original_length = len(text)
    
    # 기본 정규화
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Stage2 실행 (metadata 옵션)
    if metadata:
        stage2_result = _run_stage2_with_metadata(text, metadata)
    else:
        stage2_result = _run_stage2_basic(text)  # 기존 방식
    print(f"🔍 [DEBUG] Stage2 후: {len(stage2_result)}자", file=sys.stderr)
    
    # Stage3 실행 (metadata 옵션)
    if metadata:
        stage3_result = _run_stage3_with_metadata(stage2_result, metadata)
    else:
        stage3_result = _run_stage3_basic(stage2_result)  # 기존 방식
    print(f"🔍 [DEBUG] 안전한 Stage3 후: {len(stage3_result)}자", file=sys.stderr)
    
    # 라인 정리
    lines = [line.strip() for line in stage3_result.split("\n") if line.strip()]
    result = "\n".join(lines)
    print(f"🔍 [DEBUG] 최종 결과: {len(result)}자", file=sys.stderr)
    
    return result

def _run_stage2_basic(text: str) -> str:
    """기존 Stage2 처리 (호환성)"""
    import logging
    stage2_logger = logging.getLogger('snaptxt.stage2')
    cfg = Stage2Config(logger=stage2_logger)
    return apply_stage2_rules(text, cfg)

def _run_stage3_basic(text: str) -> str:
    """기존 Stage3 처리 (호환성)"""
    import logging
    stage3_logger = logging.getLogger('snaptxt.stage3')
    cfg = Stage3Config(
        enable_spacing_normalization=True,
        enable_character_fixes=True,
        enable_ending_normalization=True,
        enable_spellcheck_enhancement=False,
        enable_punctuation_normalization=False,
        enable_paragraph_formatting=False,
        logger=stage3_logger,
    )
    return apply_stage3_rules(text, cfg)

def _run_stage2_with_metadata(text: str, metadata: StageMetadata) -> str:
    """Stage2 + scope guard metadata 수집"""
    from snaptxt.postprocess.patterns.stage2_rules import get_replacements
    
    replacements = get_replacements()
    result = text
    
    for pattern, replacement in replacements.items():
        if should_apply_rule("S2", pattern, replacement, metadata):
            old_result = result
            # 실제 치환 적용
            if pattern in result:
                result = result.replace(pattern, replacement)
                char_diff = len(result) - len(old_result)
                # char_diff==0이어도 rules_applied는 증가 (감독관 지시)
                mark_rule_applied("S2", pattern, replacement, char_diff, metadata)
    
    return result

def _run_stage3_with_metadata(text: str, metadata: StageMetadata) -> str:
    """Stage3 + scope guard metadata 수집"""
    # 기본 Stage3 처리
    old_text = text
    result = _run_stage3_basic(text)
    
    # 전체 변화량을 Stage3에 기록 (간소화)
    char_diff = len(result) - len(old_text)
    if char_diff != 0 or old_text != result:
        metadata.stage3_counter.rules_applied += 1
        metadata.stage3_counter.chars_changed += char_diff
        metadata.stage3_counter.top_patterns["stage3_combined"] += 1
    
    return result

# 기존 함수명 유지 (easyocr_worker.py에서 호출)
def get_advanced_korean_processor():
    """기존 호출부 호환성을 위한 팩토리 함수"""
    return advanced_korean_text_processor_with_metadata