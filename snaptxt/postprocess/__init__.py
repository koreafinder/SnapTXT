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

# Book Profile import
try:
    from .book_sense.book_profile_manager import BookProfileManager
    BOOK_PROFILE_AVAILABLE = True
except ImportError:
    BOOK_PROFILE_AVAILABLE = False
    BookProfileManager = None

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

# Context-Conditioned Replay import (Phase 3.2 연구 성과 통합)
try:
    from .context_aware_processor import ContextConditionedProcessor
    CONTEXT_CONDITIONED_AVAILABLE = True
except ImportError:
    CONTEXT_CONDITIONED_AVAILABLE = False
    ContextConditionedProcessor = None

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
    "ContextConditionedProcessor",  # NEW: Context-aware 처리기 노출
]


def run_pipeline(
    text: str,
    *,
    book_profile: str | None = None,  # ← NEW: Book Profile ID for book-specific optimization
    stage2_config: Stage2Config | None = None,
    stage3_config: Stage3Config | None = None,
    logger: logging.Logger | None = None,
    collect_patterns: bool = True,  # ← 신규 파라미터: 패턴 수집 여부
    enable_context_aware: bool = True  # ← NEW: Context-Conditioned Replay 활성화 (연구 검증: INSERT 패턴 3배 성능 향상)
) -> str:
    """Run postprocessing stages sequentially with optional pattern collection."""

    log = logger or logging.getLogger(__name__)
    stage2_cfg = stage2_config or Stage2Config(logger=log)
    stage3_cfg = stage3_config or Stage3Config(logger=log)
    
    # 🔥 Book Profile Integration
    book_rules_applied = False
    if book_profile and BOOK_PROFILE_AVAILABLE:
        try:
            profile_manager = BookProfileManager()
            profile_data = profile_manager.load_book_profile(book_profile)
            log.info(f"📂 Book Profile 로드 시도: {book_profile}")
            if profile_data:
                # Apply book-specific correction rules
                text = _apply_book_profile_rules(text, profile_data, log)
                book_rules_applied = True
                log.info(f"📚 Book Profile '{book_profile}' 적용됨")
            else:
                log.warning(f"⚠️ Book Profile '{book_profile}' 로드 실패")
        except Exception as e:
            log.warning(f"⚠️ Book Profile 적용 실패: {e}")
            import traceback
            log.debug(f"📋 Traceback: {traceback.format_exc()}")
        except Exception as e:
            log.warning(f"⚠️ Book Profile 적용 실패: {e}")
    
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
    
    # ✨ Context-Conditioned Replay (Phase 3.2 연구 성과 통합)
    context_aware_result = None
    if enable_context_aware and CONTEXT_CONDITIONED_AVAILABLE:
        context_start = time.time()
        log.info("   🧠 Context-Conditioned Replay 시작 (연구 검증: INSERT 패턴 3배 향상)")
        
        try:
            context_processor = ContextConditionedProcessor(log)
            context_aware_result = context_processor.process_text(stage3, enable_context_aware)
            context_time = time.time() - context_start
            
            if context_aware_result.patterns_applied:
                stage3 = context_aware_result.processed_text  # Context-aware 결과 적용
                log.info(f"   ✅ Context-aware 완료 ({context_time*1000:.1f}ms)")
                log.info(f"      🎨 적용 패턴: {len(context_aware_result.patterns_applied)}개")
                log.info(f"      📈 신뢰도: {context_aware_result.confidence_score:.1%}")
                
                # 적용된 패턴 상세 로그
                for pattern in context_aware_result.patterns_applied:
                    log.debug(f"      → {pattern['type']}:{pattern['subtype']} @{pattern['position']} ({pattern['confidence']:.1%})")
            else:
                log.debug(f"   📋 Context-aware: 적용 가능한 패턴 없음 ({context_time*1000:.1f}ms)")
                
        except Exception as e:
            log.warning(f"   ⚠️ Context-aware 처리 실패: {e}")
            import traceback
            log.debug(f"📋 Context-aware Traceback: {traceback.format_exc()}")
    elif enable_context_aware and not CONTEXT_CONDITIONED_AVAILABLE:
        log.warning("   ⚠️ Context-Conditioned Replay 불가: 모듈 import 실패")
    elif not enable_context_aware:
        log.debug("   📋 Context-Conditioned Replay 비활성화")
    
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
    # Context-aware 성과 요약
    if context_aware_result and context_aware_result.patterns_applied:
        context_improvement = len(context_aware_result.patterns_applied)
        log.info(f"   🧠 Context-aware 개선: {context_improvement}개 패턴 적용 (연구검증: 3배 성능향상)")    
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


def _apply_book_profile_rules(text: str, profile_data: dict, logger: logging.Logger) -> str:
    """Book Profile의 correction rules를 텍스트에 적용"""
    
    processed_text = text
    rules_applied = 0
    
    try:
        # profile_data가 문자열인 경우 처리
        if isinstance(profile_data, str):
            logger.warning(f"⚠️ profile_data가 문자열입니다: {profile_data}")
            return processed_text
            
        # profile_data가 None인 경우 처리
        if profile_data is None:
            logger.warning("⚠️ profile_data가 None입니다")
            return processed_text
        
        correction_rules = profile_data.get('correction_rules', [])
        user_settings = profile_data.get('user_settings', {})
        
        # 비활성화된 규칙들 확인
        disabled_rules = user_settings.get('disabled_rules', [])
        
        for i, rule in enumerate(correction_rules):
            
            if isinstance(rule, str):
                logger.warning(f"⚠️ rule[{i}]이 문자열입니다: {rule}")
                continue
                
            # 비활성화된 규칙 건너뛰기
            rule_id = rule.get('rule_id') or rule.get('id')  # YAML 키 호환성
            if rule_id in disabled_rules:
                continue
                
            # 위험도가 높은 규칙은 사용자 설정 확인
            priority = rule.get('priority', rule.get('priority_level', 'medium'))  # YAML 키 호환성
            scope = rule.get('scope', {})
            
            # scope가 문자열인 경우 딕셔너리로 변환
            if isinstance(scope, str):
                scope = {'pattern_scope': scope}
                
            pattern_scope = scope.get('pattern_scope', 'local') if isinstance(scope, dict) else 'local'
            
            requires_confirmation = user_settings.get('require_confirmation_for', [])
            if (priority in ['critical', 'high'] or 
                pattern_scope in requires_confirmation):
                
                # 자동 적용 안전 규칙만 적용
                if not user_settings.get('auto_apply_safe_rules', True):
                    continue
                    
                # 위험도가 높으면 건너뛰기
                if priority == 'critical':
                    continue
            
            # 규칙 적용
            pattern = rule.get('pattern', '')
            replacement = rule.get('replacement', '')
            
            if pattern and replacement:
                try:
                    # 정규식 패턴 적용
                    before_length = len(processed_text)
                    processed_text = re.sub(pattern, replacement, processed_text)
                    
                    # 실제 교체가 이루어졌는지 확인
                    if len(processed_text) != before_length:
                        rules_applied += 1
                        logger.debug(f"   📝 규칙 적용: {rule.get('explanation', pattern)}")
                        
                except re.error as e:
                    logger.warning(f"   ⚠️ 규칙 적용 실패: {pattern} - {e}")
                    continue
        
        if rules_applied > 0:
            logger.info(f"   ✅ Book Profile: {rules_applied}개 규칙 적용됨")
        else:
            logger.info(f"   ℹ️ Book Profile: 적용 가능한 규칙 없음")
            
    except Exception as e:
        logger.warning(f"   ⚠️ Book Profile 처리 오류: {e}")
        return text
    
    return processed_text