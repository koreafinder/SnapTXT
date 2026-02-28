#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR System Integration Adapter
기존 시스템과 새로운 궁극의 OCR 시스템 간의 통합 어댑터
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class OCRSystemAdapter:
    """기존 시스템과 새로운 OCR 시스템 간의 호환성 제공"""
    
    def __init__(self):
        """어댑터 초기화"""
        self.ultimate_system = None
        self.legacy_available = False
        self.ultimate_available = False
        self.init_systems()
    
    def init_systems(self):
        """OCR 시스템들 초기화"""
        
        # 새로운 궁극의 OCR 시스템 초기화 시도
        try:
            from ultimate_ocr_system import UltimateOCRSystem
            self.ultimate_system = UltimateOCRSystem()
            self.ultimate_available = True
            logger.info("✅ 궁극의 OCR 시스템 초기화 완료")
        except Exception as e:
            logger.error(f"❌ 궁극의 OCR 시스템 초기화 실패: {e}")
            self.ultimate_available = False
        
        # 기존 시스템들 호환성 체크
        try:
            # easyocr_worker 확인
            from snaptxt.backend.worker import easyocr_worker
            self.legacy_available = True
            logger.info("✅ 기존 EasyOCR 시스템 확인 완료")
        except Exception as e:
            logger.warning(f"⚠️ 기존 시스템 확인 실패: {e}")
            self.legacy_available = False
    
    def enhanced_ocr_processing(self, image_path: str, use_new_system: bool = True) -> Dict:
        """
        개선된 OCR 처리 (자동 시스템 선택)
        
        Args:
            image_path: 이미지 파일 경로
            use_new_system: 새로운 시스템 우선 사용 여부
            
        Returns:
            Dict: 통합 OCR 결과
        """
        
        if use_new_system and self.ultimate_available:
            logger.info("🚀 궁극의 OCR 시스템으로 처리")
            return self._process_with_ultimate(image_path)
        elif self.legacy_available:
            logger.info("🔧 기존 EasyOCR 시스템으로 처리")
            return self._process_with_legacy(image_path)
        else:
            return self._error_result("사용 가능한 OCR 시스템이 없습니다.")
    
    def _process_with_ultimate(self, image_path: str) -> Dict:
        """궁극의 OCR 시스템으로 처리"""
        try:
            # 최적화된 옵션으로 처리
            options = {
                'enable_image_preprocessing': True,
                'enable_morpheme_analysis': True,
                'enable_user_dictionary': True,
                'preprocessing_settings': {
                    'denoise': True,
                    'enhance_contrast': True,
                    'sharpen': True,
                    'adaptive_threshold': True,
                    'deskew': True,
                },
                'easyocr_settings': {
                    'contrast_ths': 0.1,
                    'adjust_contrast': 0.5,
                    'text_threshold': 0.7,
                    'low_text': 0.4,
                    'link_threshold': 0.4,
                    'canvas_size': 2560,
                    'mag_ratio': 1.0,
                    'paragraph': True,
                    'detail': 1
                }
            }
            
            result = self.ultimate_system.process_image_ultimate(image_path, options)
            
            # 기존 시스템 호환 형태로 변환
            return self._convert_to_legacy_format(result)
            
        except Exception as e:
            logger.error(f"❌ 궁극의 OCR 처리 실패: {e}")
            return self._error_result(f"궁극의 OCR 처리 실패: {str(e)}")
    
    def _process_with_legacy(self, image_path: str) -> Dict:
        """기존 EasyOCR 시스템으로 처리"""
        try:
            import easyocr_worker
            
            # 기존 시스템 호출
            result_text = easyocr_worker.process_image_easyocr(image_path)  # 함수명 수정
            
            return {
                'success': True,
                'text': result_text,
                'confidence': 0.8,  # 기본값
                'processing_time': 0.0,  # 측정 안됨
                'system_used': 'legacy',
                'quality_score': 0.75  # 추정값
            }
            
        except Exception as e:
            logger.error(f"❌ 기존 OCR 처리 실패: {e}")
            return self._error_result(f"기존 OCR 처리 실패: {str(e)}")
    
    def _convert_to_legacy_format(self, ultimate_result: Dict) -> Dict:
        """궁극의 OCR 결과를 기존 형태로 변환"""
        if ultimate_result['success']:
            return {
                'success': True,
                'text': ultimate_result['final_text'],
                'confidence': ultimate_result['quality_metrics']['overall_quality'],
                'processing_time': ultimate_result['processing_time'],
                'system_used': 'ultimate',
                'quality_score': ultimate_result['quality_metrics']['overall_quality'],
                'detailed_info': {
                    'raw_text': ultimate_result['raw_text'],
                    'corrections': ultimate_result['processing_stats']['corrections_applied'],
                    'blocks_count': ultimate_result['processing_stats']['total_blocks']
                }
            }
        else:
            return self._error_result(ultimate_result.get('error', '알 수 없는 오류'))
    
    def _error_result(self, error_msg: str) -> Dict:
        """오류 결과 생성"""
        return {
            'success': False,
            'error': error_msg,
            'text': '',
            'confidence': 0.0,
            'processing_time': 0.0,
            'system_used': 'none',
            'quality_score': 0.0
        }
    
    def get_available_systems(self) -> Dict:
        """사용 가능한 시스템 목록"""
        return {
            'ultimate_system': self.ultimate_available,
            'legacy_system': self.legacy_available,
            'recommended': 'ultimate' if self.ultimate_available else 'legacy'
        }
    
    def add_user_correction(self, wrong_text: str, correct_text: str):
        """사용자 교정 추가 (새로운 시스템만 지원)"""
        if self.ultimate_available and self.ultimate_system:
            self.ultimate_system.add_user_correction(wrong_text, correct_text)
            logger.info(f"사용자 교정 추가: '{wrong_text}' → '{correct_text}'")
        else:
            logger.warning("사용자 교정 기능은 궁극의 OCR 시스템에서만 지원됩니다.")
    
    def get_system_stats(self) -> Dict:
        """시스템 통계"""
        if self.ultimate_available and self.ultimate_system:
            return self.ultimate_system.get_system_stats()
        else:
            return {
                'error': '통계는 궁극의 OCR 시스템에서만 지원됩니다.',
                'ultimate_available': self.ultimate_available,
                'legacy_available': self.legacy_available
            }


# 전역 어댑터 인스턴스 (싱글톤 패턴)
_global_adapter = None

def get_ocr_adapter() -> OCRSystemAdapter:
    """전역 OCR 어댑터 인스턴스 반환"""
    global _global_adapter
    if _global_adapter is None:
        _global_adapter = OCRSystemAdapter()
    return _global_adapter

def enhanced_process_image(image_path: str, prefer_new_system: bool = True) -> Dict:
    """
    통합 이미지 처리 함수 (기존 코드 호환용)
    
    이 함수는 기존 코드에서 쉽게 호출할 수 있도록 만들어진 래퍼입니다.
    """
    adapter = get_ocr_adapter()
    return adapter.enhanced_ocr_processing(image_path, prefer_new_system)

def is_new_system_available() -> bool:
    """새로운 시스템 사용 가능 여부 확인"""
    adapter = get_ocr_adapter()
    return adapter.ultimate_available

def add_correction(wrong: str, correct: str):
    """사용자 교정 추가"""
    adapter = get_ocr_adapter()
    adapter.add_user_correction(wrong, correct)


# GUI 통합을 위한 래퍼 함수들
class GUIIntegration:
    """GUI 프로그램과의 통합을 위한 클래스"""
    
    @staticmethod
    def process_for_gui(image_path: str, progress_callback=None) -> str:
        """
        GUI용 간단한 처리 함수
        
        Returns:
            str: 추출된 텍스트 (오류시 빈 문자열)
        """
        try:
            if progress_callback:
                progress_callback("OCR 처리 시작...")
            
            result = enhanced_process_image(image_path)
            
            if progress_callback:
                if result['success']:
                    progress_callback(f"OCR 완료 (품질: {result['quality_score']:.2f})")
                else:
                    progress_callback("OCR 처리 실패")
            
            return result.get('text', '') if result['success'] else ''
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"오류: {str(e)}")
            logger.error(f"GUI OCR 처리 실패: {e}")
            return ''
    
    @staticmethod
    def get_processing_info() -> Dict:
        """처리 시스템 정보"""
        adapter = get_ocr_adapter()
        systems = adapter.get_available_systems()
        
        return {
            'systems_available': systems,
            'recommended_system': systems['recommended'],
            'can_add_corrections': systems['ultimate_system']
        }


if __name__ == "__main__":
    """테스트 실행"""
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    if len(sys.argv) < 2:
        print("사용법: python ocr_integration_adapter.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    print("🔧 OCR 시스템 통합 어댑터 테스트")
    print("=" * 40)
    
    # 시스템 정보 확인
    adapter = get_ocr_adapter()
    systems = adapter.get_available_systems()
    
    print(f"궁극의 OCR 시스템: {'✅' if systems['ultimate_system'] else '❌'}")
    print(f"기존 OCR 시스템: {'✅' if systems['legacy_system'] else '❌'}")
    print(f"권장 시스템: {systems['recommended']}")
    print()
    
    # OCR 처리
    print(f"📷 이미지 처리: {Path(image_path).name}")
    result = enhanced_process_image(image_path)
    
    if result['success']:
        print("✅ 처리 성공!")
        print(f"시스템: {result['system_used']}")
        print(f"품질: {result['quality_score']:.3f}")
        print(f"처리시간: {result['processing_time']:.3f}초")
        print("-" * 30)
        print("추출된 텍스트:")
        print(result['text'])
    else:
        print(f"❌ 처리 실패: {result['error']}")