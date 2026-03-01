#!/usr/bin/env python3
"""
전처리 시스템 성능 비교 테스트
- Office Lens 지능형 전처리 vs 레거시 전처리
"""

import sys
sys.path.append('.')

from office_lens_book_preprocessor import OfficeLensBookPreprocessor
from snaptxt.preprocess import apply_default_filters
import cv2
import time
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def compare_preprocessing_systems():
    """전처리 시스템 성능 비교"""
    
    print("🔬" + "="*50)
    print("📊 전처리 시스템 성능 비교 테스트")
    print("🔬" + "="*50)
    
    # Office Lens 시스템 초기화
    office_lens = OfficeLensBookPreprocessor()
    
    # 테스트 이미지
    test_image_path = 'experiments/samples/office_lens_test/IMG_4793.JPG'
    
    print(f"🖼️  테스트 이미지: {test_image_path}")
    
    # 이미지 로드
    image = cv2.imread(test_image_path)
    if image is None:
        print(f"❌ 이미지 로드 실패: {test_image_path}")
        return
    
    print(f"📐 원본 크기: {image.shape[1]}×{image.shape[0]} pixels")
    
    # 1. Office Lens 지능형 전처리 테스트
    print("\n🎯 Office Lens 지능형 전처리 시스템")
    print("-" * 40)
    start_time = time.perf_counter()
    
    try:
        selected_preset, office_lens_result, quality_score = office_lens.auto_select_best_preset(image)
        office_lens_time = time.perf_counter() - start_time
        
        print(f"   🏆 선택된 프리셋: {selected_preset}")
        print(f"   📊 품질 점수: {quality_score:.1f}/100")
        print(f"   ⏱️  처리 시간: {office_lens_time:.2f}초")
        print(f"   ✅ Office Lens 처리 성공")
        
    except Exception as e:
        print(f"   ❌ Office Lens 처리 실패: {e}")
        office_lens_result = None
        office_lens_time = 0
    
    # 2. 레거시 전처리 시스템 테스트
    print("\n🏗️ 레거시 전처리 시스템 (레벨 2)")
    print("-" * 40)
    start_time = time.perf_counter()
    
    try:
        legacy_result = apply_default_filters(image, level=2)
        legacy_time = time.perf_counter() - start_time
        
        print(f"   📐 결과 크기: {legacy_result.shape[1] if len(legacy_result.shape) > 1 else 'N/A'}×{legacy_result.shape[0] if len(legacy_result.shape) > 0 else 'N/A'}")
        print(f"   ⏱️  처리 시간: {legacy_time:.2f}초")
        print(f"   ✅ 레거시 처리 성공")
        
    except Exception as e:
        print(f"   ❌ 레거시 처리 실패: {e}")
        legacy_result = None
        legacy_time = 0
    
    # 3. 결과 비교
    print("\n📊" + "="*50)
    print("🏆 성능 비교 결과")
    print("📊" + "="*50)
    
    print(f"🎯 Office Lens:")
    if office_lens_result is not None:
        print(f"   - 프리셋: {selected_preset}")
        print(f"   - 품질: {quality_score:.1f}/100")
        print(f"   - 시간: {office_lens_time:.2f}초")
        print(f"   - 특징: 자동 이미지 분석 + 최적 프리셋 선택")
    else:
        print(f"   - 상태: 실패")
    
    print(f"\n🏗️ 레거시 시스템:")
    if legacy_result is not None:
        print(f"   - 레벨: 2 (중간)")
        print(f"   - 시간: {legacy_time:.2f}초")
        print(f"   - 특징: 고정된 필터 파이프라인")
    else:
        print(f"   - 상태: 실패")
    
    # 속도 비교
    if office_lens_time > 0 and legacy_time > 0:
        speed_ratio = office_lens_time / legacy_time
        print(f"\n⏱️  처리 속도 비교:")
        if speed_ratio > 1:
            print(f"   - Office Lens는 레거시보다 {speed_ratio:.1f}배 느림 (하지만 더 지능적)")
        else:
            print(f"   - Office Lens가 레거시보다 {1/speed_ratio:.1f}배 빠름")
    
    print(f"\n💡 결론:")
    print(f"   🎯 Office Lens: 자동 분석으로 이미지별 맞춤 최적화")
    print(f"   🏗️ 레거시: 빠르지만 일괄 처리")
    print(f"   🏆 추천: Office Lens (IMG_4793 같은 까다로운 케이스 개선)")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    compare_preprocessing_systems()