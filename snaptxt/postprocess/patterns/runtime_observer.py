"""PC App 관측 로그 - 단일 진실 소스 기반"""

import logging
from snaptxt.postprocess.patterns.stage2_rules import get_runtime_rule_info
from snaptxt.postprocess.patterns.stage_scope_guard import StageMetadata, log_stage_summary

logger = logging.getLogger(__name__)

def log_runtime_startup():
    """실제 사용 파일 기준 관측 로그 (side-effect 최소화)"""
    try:
        info = get_runtime_rule_info()
        
        # Base Rules 정보
        base_file = info.get("base_path", "unknown").split("/")[-1]  # 파일명만
        base_hash = info.get("base_hash", "none")
        logger.info(f"📊 Stage2 Base: {base_file} (hash={base_hash})")
        
        # Overlay 정보
        overlay_file = info.get("overlay_file")
        if overlay_file:
            overlay_mtime = info.get("overlay_mtime", 0)
            logger.info(f"📊 Stage2 Overlay: ✅ {overlay_file} (mtime={overlay_mtime})")
        else:
            logger.info(f"📊 Stage2 Overlay: ❌ 미발견")
            
    except Exception as e:
        logger.warning(f"📊 Runtime 정보 수집 실패: {e}")

def process_with_runtime_observation(text: str, processor_func):
    """런타임 관측과 함께 텍스트 처리"""
    # 시작 로그
    log_runtime_startup()
    
    # 메타데이터 생성
    metadata = StageMetadata()
    
    try:
        # 프로세서 호출 (metadata 전달)
        if hasattr(processor_func, '__call__'):
            result = processor_func(text, metadata)
        else:
            # 기존 방식 폴백
            result = processor_func(text)
            logger.info("📊 기존 프로세서 사용 (메타데이터 없음)")
            return result
            
        # 결과 로그
        log_stage_summary(metadata, logger)
        
        return result
        
    except Exception as e:
        logger.error(f"📊 프로세서 실행 실패: {e}")
        # 메타데이터가 있으면 현재 상태라도 로그
        if metadata:
            log_stage_summary(metadata, logger)
        raise

def create_metadata_enabled_processor():
    """메타데이터 지원 프로세서 생성"""
    try:
        from snaptxt.postprocess.patterns.stage_pipeline_processor import advanced_korean_text_processor_with_metadata
        return advanced_korean_text_processor_with_metadata
    except ImportError:
        # 폴백: 기존 프로세서 대신 에러 처리
        logger.error("📊 메타데이터 프로세서 사용불가, stage_pipeline_processor 모듈 확인 필요")
        raise ImportError("패턴 프로세서를 찾을 수 없습니다")

# 간단한 사용 예시
def ocr_with_observation(text: str) -> str:
    """관측이 포함된 OCR 처리"""
    processor = create_metadata_enabled_processor()
    return process_with_runtime_observation(text, processor)

# PC 앱에서 직접 호출할 수 있는 통합 함수
def start_ocr_processing_with_observation(text: str) -> str:
    """PC 앱 전용: 관측 로그와 함께 OCR 처리"""
    logger.info("🚀 SnapTXT OCR 처리 시작")
    result = ocr_with_observation(text)
    logger.info("✅ SnapTXT OCR 처리 완료")
    return result