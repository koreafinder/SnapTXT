#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ultimate OCR System - 궁극의 OCR 처리 시스템
기존 easyocr_worker와 새로운 고급 모듈들의 통합
"""

import sys
import json
import os
import time
from pathlib import Path
import logging
from typing import Dict, List, Union, Optional
import numpy as np
import cv2
from PIL import Image

# 새로운 고급 모듈들 import
from enhanced_korean_processor import EnhancedKoreanProcessor
from advanced_image_processor import AdvancedImageProcessor

logger = logging.getLogger(__name__)

class UltimateOCRSystem:
    """궁극의 OCR 처리 시스템"""
    
    def __init__(self):
        """초기화"""
        self.setup_environment()
        self.korean_processor = EnhancedKoreanProcessor()
        self.image_processor = AdvancedImageProcessor()
        self.easyocr_reader = None
        self.init_easyocr()
        
        # 성능 통계
        self.performance_stats = {
            'total_processed': 0,
            'success_count': 0,
            'average_processing_time': 0.0,
            'average_quality_score': 0.0,
            'error_count': 0
        }
    
    def setup_environment(self):
        """환경 설정 최적화"""
        try:
            os.environ['PYTHONIOENCODING'] = 'utf-8'
            os.environ['CUDA_VISIBLE_DEVICES'] = ''  # CPU 모드
            logger.info("✅ 환경 설정 완료")
        except Exception as e:
            logger.error(f"❌ 환경 설정 실패: {e}")
    
    def init_easyocr(self):
        """EasyOCR 초기화"""
        try:
            import easyocr
            self.easyocr_reader = easyocr.Reader(['ko', 'en'], gpu=False)
            logger.info("✅ EasyOCR 초기화 완료")
        except Exception as e:
            logger.error(f"❌ EasyOCR 초기화 실패: {e}")
    
    def process_image_ultimate(self, image_path: str, options: Dict = None) -> Dict:
        """
        궁극의 이미지 OCR 처리
        
        Args:
            image_path: 이미지 파일 경로
            options: 처리 옵션
            
        Returns:
            Dict: 종합 처리 결과
        """
        start_time = time.time()
        
        default_options = {
            'enable_image_preprocessing': True,
            'enable_morpheme_analysis': True,
            'enable_user_dictionary': True,
            'preprocessing_settings': {
                'denoise': True,
                'enhance_contrast': True,
                'sharpen': True,
                'adaptive_threshold': True,
                'deskew': True,
                'upscale': False,
                'target_dpi': 300
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
        
        if options:
            default_options.update(options)
        
        try:
            # 1. 이미지 로드
            if not Path(image_path).exists():
                return self._error_result(f"이미지 파일을 찾을 수 없습니다: {image_path}")
            
            image = cv2.imread(image_path)
            if image is None:
                return self._error_result(f"이미지를 읽을 수 없습니다: {image_path}")
            
            logger.info(f"🖼️ 이미지 로드 완료: {image.shape}")
            
            # 2. 이미지 전처리 (선택적)
            if default_options['enable_image_preprocessing']:
                preprocess_result = self.image_processor.preprocess_for_korean_ocr(
                    image, default_options['preprocessing_settings']
                )
                
                if preprocess_result['success']:
                    processed_image = preprocess_result['processed_image']
                    image_quality_score = preprocess_result['quality_score']
                    logger.info(f"✅ 이미지 전처리 완료 (품질: {image_quality_score:.3f})")
                else:
                    processed_image = image
                    image_quality_score = 0.5
                    logger.warning("⚠️ 이미지 전처리 실패, 원본 이미지 사용")
            else:
                processed_image = image
                image_quality_score = 0.5
            
            # 3. EasyOCR 텍스트 추출
            if self.easyocr_reader is None:
                return self._error_result("EasyOCR 리더가 초기화되지 않았습니다")
            
            logger.info("🔍 EasyOCR 텍스트 추출 중...")
            easyocr_results = self.easyocr_reader.readtext(
                processed_image,
                **default_options['easyocr_settings']
            )
            
            # 4. 텍스트 병합
            raw_text_blocks = []
            detailed_results = []
            
            for result in easyocr_results:
                if len(result) >= 3:
                    bbox, text, confidence = result[:3]
                    
                    # 신뢰도 필터링
                    if confidence >= 0.3:
                        raw_text_blocks.append(text)
                        detailed_results.append({
                            'bbox': bbox,
                            'text': text,
                            'confidence': confidence
                        })
            
            raw_text = '\n'.join(raw_text_blocks)
            logger.info(f"📝 원시 텍스트 추출 완료: {len(raw_text_blocks)}개 블록")
            
            # 5. 고급 한국어 후처리
            if raw_text.strip():
                korean_result = self.korean_processor.process_text(
                    raw_text,
                    enable_morpheme_analysis=default_options['enable_morpheme_analysis']
                )
                
                if korean_result['success']:
                    final_text = korean_result['processed_text']
                    text_quality_score = korean_result['quality_score']
                    corrections_applied = korean_result['corrections_applied']
                    logger.info(f"✅ 한국어 후처리 완료 (교정: {corrections_applied}회, 품질: {text_quality_score:.3f})")
                else:
                    final_text = raw_text
                    text_quality_score = 0.5
                    corrections_applied = 0
                    logger.warning("⚠️ 한국어 후처리 실패, 원본 텍스트 사용")
            else:
                final_text = ""
                text_quality_score = 0.0
                corrections_applied = 0
                logger.warning("⚠️ 추출된 텍스트가 없습니다")
            
            # 6. 종합 결과 생성
            processing_time = time.time() - start_time
            overall_quality = (image_quality_score + text_quality_score) / 2
            
            result = {
                'success': True,
                'final_text': final_text,
                'raw_text': raw_text,
                'detailed_results': detailed_results,
                'processing_time': round(processing_time, 3),
                'quality_metrics': {
                    'image_quality': round(image_quality_score, 3),
                    'text_quality': round(text_quality_score, 3),
                    'overall_quality': round(overall_quality, 3)
                },
                'processing_stats': {
                    'total_blocks': len(detailed_results),
                    'corrections_applied': corrections_applied,
                    'image_preprocessed': default_options['enable_image_preprocessing'],
                    'morpheme_analyzed': default_options['enable_morpheme_analysis']
                },
                'options_used': default_options
            }
            
            # 7. 성능 통계 업데이트
            self._update_performance_stats(processing_time, overall_quality, True)
            
            return result
            
        except Exception as e:
            error_time = time.time() - start_time
            logger.error(f"❌ OCR 처리 실패: {e}")
            self._update_performance_stats(error_time, 0.0, False)
            return self._error_result(f"OCR 처리 중 오류: {str(e)}")
    
    def process_multiple_images(self, image_paths: List[str], options: Dict = None) -> Dict:
        """다중 이미지 배치 처리"""
        logger.info(f"🚀 배치 처리 시작: {len(image_paths)}개 파일")
        
        batch_start_time = time.time()
        results = []
        success_count = 0
        
        for i, image_path in enumerate(image_paths):
            logger.info(f"📷 처리 중... ({i+1}/{len(image_paths)}): {Path(image_path).name}")
            
            result = self.process_image_ultimate(image_path, options)
            result['file_path'] = image_path
            result['file_name'] = Path(image_path).name
            
            results.append(result)
            
            if result['success']:
                success_count += 1
            
            # 진행률 표시
            progress = (i + 1) / len(image_paths) * 100
            logger.info(f"📊 진행률: {progress:.1f}%")
        
        batch_time = time.time() - batch_start_time
        success_rate = (success_count / len(image_paths)) * 100 if image_paths else 0
        
        batch_result = {
            'success': True,
            'batch_results': results,
            'batch_stats': {
                'total_files': len(image_paths),
                'success_count': success_count,
                'success_rate': round(success_rate, 1),
                'total_time': round(batch_time, 3),
                'average_time_per_file': round(batch_time / len(image_paths), 3) if image_paths else 0
            }
        }
        
        logger.info(f"✅ 배치 처리 완료: {success_count}/{len(image_paths)} 성공 ({success_rate:.1f}%)")
        
        return batch_result
    
    def _error_result(self, error_msg: str) -> Dict:
        """오류 결과 생성"""
        return {
            'success': False,
            'error': error_msg,
            'final_text': '',
            'processing_time': 0.0
        }
    
    def _update_performance_stats(self, processing_time: float, quality_score: float, success: bool):
        """성능 통계 업데이트"""
        self.performance_stats['total_processed'] += 1
        
        if success:
            self.performance_stats['success_count'] += 1
        else:
            self.performance_stats['error_count'] += 1
        
        # 이동 평균 업데이트
        total = self.performance_stats['total_processed']
        self.performance_stats['average_processing_time'] = (
            (self.performance_stats['average_processing_time'] * (total - 1) + processing_time) / total
        )
        
        if success:
            success_count = self.performance_stats['success_count']
            self.performance_stats['average_quality_score'] = (
                (self.performance_stats['average_quality_score'] * (success_count - 1) + quality_score) / success_count
            )
    
    def get_system_stats(self) -> Dict:
        """시스템 통계 조회"""
        korean_stats = self.korean_processor.get_performance_stats()
        image_stats = self.image_processor.get_processing_stats()
        
        return {
            'overall': self.performance_stats,
            'korean_processor': korean_stats,
            'image_processor': image_stats
        }
    
    def add_user_correction(self, wrong_text: str, correct_text: str):
        """사용자 교정 추가"""
        self.korean_processor.add_user_word(wrong_text, correct_text)
        logger.info(f"사용자 교정 추가: '{wrong_text}' → '{correct_text}'")
    
    def reset_stats(self):
        """통계 초기화"""
        self.performance_stats = {
            'total_processed': 0,
            'success_count': 0,
            'average_processing_time': 0.0,
            'average_quality_score': 0.0,
            'error_count': 0
        }
        self.korean_processor.reset_stats()

def main():
    """명령줄 테스트 실행"""
    if len(sys.argv) < 2:
        print("사용법: python ultimate_ocr_system.py <image_path> [options]")
        print("예시: python ultimate_ocr_system.py test.jpg")
        sys.exit(1)
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('ultimate_ocr.log', encoding='utf-8')
        ]
    )
    
    # OCR 시스템 초기화
    ocr_system = UltimateOCRSystem()
    
    image_path = sys.argv[1]
    
    # 옵션 파싱 (간단한 예시)
    options = {}
    if len(sys.argv) > 2 and sys.argv[2] == '--no-preprocess':
        options['enable_image_preprocessing'] = False
    
    print(f"🚀 궁극의 OCR 처리 시작: {image_path}")
    
    # OCR 처리
    result = ocr_system.process_image_ultimate(image_path, options)
    
    # 결과 출력
    if result['success']:
        print("\n" + "="*50)
        print("📝 최종 추출 텍스트:")
        print("="*50)
        print(result['final_text'])
        print("\n" + "="*50)
        print("📊 처리 통계:")
        print(f"- 처리 시간: {result['processing_time']:.3f}초")
        print(f"- 전체 품질: {result['quality_metrics']['overall_quality']:.3f}")
        print(f"- 텍스트 블록 수: {result['processing_stats']['total_blocks']}")
        print(f"- 교정 횟수: {result['processing_stats']['corrections_applied']}")
    else:
        print(f"❌ 처리 실패: {result['error']}")
    
    # JSON 결과 출력 (다른 프로그램과 연동용)
    print("\n" + "="*30 + " JSON 결과 " + "="*30)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()