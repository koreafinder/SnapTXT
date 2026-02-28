#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전처리 과정 시각적 디버깅 도구
"""

import cv2
import numpy as np
from research_based_preprocessing_integration import KoreanOCROptimizedPreprocessor

def debug_preprocessing_steps(image_path):
    """
    전처리 각 단계별 결과를 이미지로 저장해서 확인
    """
    print(f"🔍 디버깅 시작: {image_path}")
    
    # 원본 이미지 로드
    original = cv2.imread(image_path)
    if original is None:
        print("❌ 이미지 로드 실패")
        return
    
    print(f"📊 원본 이미지 크기: {original.shape}")
    
    # 전처리기 생성
    preprocessor = KoreanOCROptimizedPreprocessor()
    
    # 1단계: 이미지 품질 향상
    try:
        enhanced = preprocessor.enhance_image_quality(original)
        cv2.imwrite("debug_1_enhanced.png", enhanced)
        print("✅ 1단계 완료: debug_1_enhanced.png")
    except Exception as e:
        print(f"❌ 1단계 실패: {e}")
        return
    
    # 2단계: 이진화
    try:
        binary = preprocessor.research_based_binarization(enhanced)
        cv2.imwrite("debug_2_binary.png", binary)
        print(f"✅ 2단계 완료: debug_2_binary.png (크기: {binary.shape})")
        
        # 이진화 결과 확인
        unique_values = np.unique(binary)
        print(f"🔍 이진화 후 픽셀값: {unique_values}")
        white_pixels = np.sum(binary == 255)
        black_pixels = np.sum(binary == 0)
        print(f"🔍 흰색 픽셀: {white_pixels}, 검은색 픽셀: {black_pixels}")
        
        if white_pixels == 0:
            print("⚠️ 경고: 흰색 픽셀이 없음 - 모든 텍스트가 제거됨")
        elif black_pixels == 0:
            print("⚠️ 경고: 검은색 픽셀이 없음 - 모든 배경이 제거됨")
            
    except Exception as e:
        print(f"❌ 2단계 실패: {e}")
        return
    
    # 3단계: 형태학적 정리
    try:
        cleaned = preprocessor.morphological_cleaning(binary)
        cv2.imwrite("debug_3_cleaned.png", cleaned)
        print(f"✅ 3단계 완료: debug_3_cleaned.png")
        
        # 정리 후 픽셀 확인
        unique_values = np.unique(cleaned)
        print(f"🔍 형태학적 정리 후 픽셀값: {unique_values}")
        
    except Exception as e:
        print(f"❌ 3단계 실패: {e}")
        return
    
    # 4단계: 웨이블릿 노이즈 제거 
    try:
        denoised = preprocessor.wavelet_denoising(cleaned)
        cv2.imwrite("debug_4_denoised.png", denoised)
        print(f"✅ 4단계 완료: debug_4_denoised.png")
    except Exception as e:
        print(f"❌ 4단계 실패: {e}")
        return
    
    # 5단계: 적응형 개선
    try:
        final = preprocessor.adaptive_enhancement(denoised)
        cv2.imwrite("debug_5_final.png", final)
        print(f"✅ 5단계 완료: debug_5_final.png")
        
        # 최종 결과 확인
        unique_values = np.unique(final)
        print(f"🔍 최종 결과 픽셀값: {unique_values}")
        
    except Exception as e:
        print(f"❌ 5단계 실패: {e}")
        return
    
    print("🎯 디버깅 완료! debug_*.png 파일들을 확인해보세요.")

if __name__ == "__main__":
    debug_preprocessing_steps("uploads/test_korean_clean.png")