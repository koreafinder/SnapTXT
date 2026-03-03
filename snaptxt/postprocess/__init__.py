"""Postprocessing package scaffolding."""
import logging
import time
import re
from difflib import SequenceMatcher
from .stage2 import Stage2Config, apply_stage2_rules
from .stage3 import Stage3Config, apply_stage3_rules
from .formatting import clean_special_characters, finalize_output
from .patterns.stage2_rules import reload_replacements as reload_stage2_rules
from .patterns.stage3_rules import reload_rules as reload_stage3_rules

# Phase 1 MVP 패턴 추천 엔진 import
try:
    from .pattern_engine import DiffCollector, StageResult
    from .pattern_engine.session_context import get_session_context  # Phase 1.5 추가
    PATTERN_ENGINE_AVAILABLE = True
except ImportError:
    PATTERN_ENGINE_AVAILABLE = False
    DiffCollector = None
    StageResult = None
    get_session_context = None

__all__ = [
    "Stage2Config",
    "Stage3Config",
    "apply_stage2_rules",
    "apply_stage3_rules",
    "finalize_output",
    "clean_special_characters",
    "reload_stage2_rules",
    "reload_stage3_rules",
    "run_pipeline",
]


def run_pipeline(
    text: str,
    *,
    stage2_config: Stage2Config | None = None,
    stage3_config: Stage3Config | None = None,
    logger: logging.Logger | None = None,
    collect_patterns: bool = True  # ← 신규 파라미터: 패턴 수집 여부
) -> str:
    """Run postprocessing stages sequentially with optional pattern collection."""

    log = logger or logging.getLogger(__name__)
    stage2_cfg = stage2_config or Stage2Config(logger=log)
    stage3_cfg = stage3_config or Stage3Config(logger=log)
    
    # 전체 시작 시간 및 입력 분석
    start_time = time.time()
    input_len = len(text)
    input_words = len(text.split()) if text else 0
    input_quality = _assess_input_quality(text)
    
    log.info("🧠 후처리 파이프라인 시작")
    log.info(f"   📊 입력: {input_len}자, {input_words}단어, 품질: {input_quality:.1%}")
    
    # Stage 2 처리
    stage2_start = time.time()
    log.info("   🔧 Stage 2 시작 (사전 교정)")
    stage2 = apply_stage2_rules(text, stage2_cfg)
    stage2_time = time.time() - stage2_start
    stage2_change = _calculate_change_metrics(text, stage2)
    
    log.info(f"   ✅ Stage 2 완료 ({stage2_time*1000:.1f}ms)")
    log.info(f"      📈 변화: {stage2_change['char_change']:.1f}%, 단어: {stage2_change['word_change']:.1f}%")
    log.info(f"      🔄 패턴 적용: {stage2_change['pattern_count']}개")
    
    # Stage 3 처리
    stage3_start = time.time()
    log.info("   🔧 Stage 3 시작 (언어학적 정제)")
    stage3 = apply_stage3_rules(stage2, stage3_cfg)
    stage3_time = time.time() - stage3_start
    stage3_change = _calculate_change_metrics(stage2, stage3)
    
    log.info(f"   ✅ Stage 3 완료 ({stage3_time*1000:.1f}ms)")
    log.info(f"      📈 변화: {stage3_change['char_change']:.1f}%, 단어: {stage3_change['word_change']:.1f}%")
    
    # ✨ 신규: 패턴 수집 (Phase 1.5 - Session-aware)
    if collect_patterns and PATTERN_ENGINE_AVAILABLE:
        try:
            diff_collector = DiffCollector()
            
            # Phase 1.5: 세션 컨텍스트 생성
            session_ctx = None
            if get_session_context:
                session_ctx = get_session_context(text)
            
            stage_result = StageResult(
                original_text=text,
                stage2_result=stage2, 
                stage3_result=stage3,
                stage2_time=stage2_time,
                stage3_time=stage3_time,
                total_changes=stage2_change.get('pattern_count', 0) + stage3_change.get('pattern_count', 0),
                # Phase 1.5: Session Context 필드들
                book_session_id=session_ctx.book_session_id if session_ctx else None,
                device_id=session_ctx.device_id if session_ctx else None,
                capture_batch_id=session_ctx.capture_batch_id if session_ctx else None,
                book_domain=session_ctx.book_domain if session_ctx else None,
                image_quality=session_ctx.image_quality if session_ctx else None
            )
            diffs = diff_collector.collect_stage_diffs(stage_result)
            
            if diffs:
                log.debug(f"   📝 패턴 수집: {len(diffs)}개 diff 저장됨 (세션: {session_ctx.book_session_id if session_ctx else 'none'})")
                
        except Exception as e:
            log.warning(f"   ⚠️  패턴 수집 실패: {e}")
    
    # 최종 처리
    final_text = finalize_output(stage3, logger=log)
    total_time = time.time() - start_time
    final_change = _calculate_change_metrics(text, final_text)
    
    # 안전성 평가
    safety_score = _evaluate_safety(text, final_text, input_quality)
    
    log.info("🎯 후처리 파이프라인 완료")
    log.info(f"   ⏱️  총 처리 시간: {total_time*1000:.1f}ms")
    log.info(f"   📊 전체 변화율: {final_change['char_change']:.1f}%")
    log.info(f"   🛡️  안전성 점수: {safety_score:.1%}")
    log.info(f"   ✨ 최종 품질: {_assess_input_quality(final_text):.1%} (원본: {input_quality:.1%})")
    
    if final_change['char_change'] < 0.1 and input_quality < 0.3:
        log.warning("   ⚠️  저품질 입력 감지 - 안전성 우선 정책 적용")
    
    return final_text

def _assess_input_quality(text: str) -> float:
    """입력 텍스트 품질 평가 (0.0-1.0)"""
    if not text or not text.strip():
        return 0.0
    
    score = 0.0
    
    # 1. 한국어 비율 (20%)
    korean_chars = len(re.findall(r'[가-힣]', text))
    korean_ratio = korean_chars / len(text) if text else 0
    score += korean_ratio * 0.2
    
    # 2. 일반적인 단어 패턴 (30%)
    common_words = ['이다', '하다', '되다', '있다', '없다', '그리다', '말하다']
    word_score = sum(1 for word in common_words if word in text) / len(common_words)
    score += word_score * 0.3
    
    # 3. 구두점 사용 (10%)
    punct_chars = len(re.findall(r'[.,!?:]', text))
    punct_ratio = min(punct_chars / (len(text.split()) * 0.1), 1.0)  # 10% 정도가 적정
    score += punct_ratio * 0.1
    
    # 4. 오류 패턴 감지 (40% - 역산)
    error_patterns = [r'[가-힣]{1}\s+[가-힣]{1}', r'[ㄱ-ㅎㅏ-ㅣ]', r'\d[가-힣]']
    error_count = sum(len(re.findall(pattern, text)) for pattern in error_patterns)
    error_penalty = min(error_count / len(text) * 10, 0.4)  # 최대 40% 감점
    score += (0.4 - error_penalty)
    
    return max(0.0, min(1.0, score))


def _calculate_change_metrics(before: str, after: str) -> dict:
    """텍스트 변화 메트릭 계산"""
    if not before or not after:
        return {'char_change': 0.0, 'word_change': 0.0, 'pattern_count': 0}
    
    # 문자 변화율
    char_change = abs(len(after) - len(before)) / len(before) * 100
    
    # 단어 변화율
    before_words = before.split()
    after_words = after.split()
    word_change = abs(len(after_words) - len(before_words)) / len(before_words) * 100 if before_words else 0
    
    # 유사도 기반 패턴 수 추정
    similarity = SequenceMatcher(None, before, after).ratio()
    pattern_count = int((1 - similarity) * len(before) / 10)  # 대략적 추정
    
    return {
        'char_change': char_change,
        'word_change': word_change, 
        'pattern_count': pattern_count,
        'similarity': similarity
    }


def _evaluate_safety(original: str, processed: str, input_quality: float) -> float:
    """후처리 안전성 평가"""
    if not original or not processed:
        return 0.5
    
    # 1. 길이 변화 안전성 (50%)
    length_ratio = len(processed) / len(original) if original else 1.0
    length_safety = 1.0 if 0.8 <= length_ratio <= 1.2 else max(0.0, 1.0 - abs(length_ratio - 1.0))
    
    # 2. 내용 보존성 (40%) 
    content_similarity = SequenceMatcher(None, original, processed).ratio()
    
    # 3. 입력 품질 고려 보정 (10%)
    quality_bonus = input_quality * 0.1
    
    return length_safety * 0.5 + content_similarity * 0.4 + quality_bonus