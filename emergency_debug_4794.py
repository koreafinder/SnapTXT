"""
IMG_4794.JPG 특화 디버깅 및 복구 시스템
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from snaptxt.preprocess.image_filters import apply_default_filters
from snaptxt.backend.multi_engine import MultiOCRProcessor
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def debug_img_4794():
    """IMG_4794.JPG 전용 분석 및 복구"""
    
    img_path = "uploads/IMG_4794.JPG"
    
    if not os.path.exists(img_path):
        # 다른 위치 확인
        possible_paths = [
            "IMG_4794.JPG",
            "uploads/IMG_4794.JPG", 
            "../IMG_4794.JPG"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                img_path = path
                break
        else:
            logger.error(f"❌ IMG_4794.JPG를 찾을 수 없습니다!")
            return
    
    logger.info(f"📄 IMG_4794.JPG 분석 시작: {img_path}")
    
    # 원본 이미지 로드
    image = cv2.imread(img_path)
    if image is None:
        logger.error(f"❌ 이미지 로드 실패!")
        return
    
    h, w = image.shape[:2]
    logger.info(f"📊 원본 이미지: {w}x{h} 픽셀")
    
    # OCR 엔진 초기화
    ocr_engine = MultiOCRProcessor()
    
    # 모든 전처리 레벨 테스트
    levels_to_test = [1, 2, 3]
    
    for level in levels_to_test:
        logger.info(f"\n🔍 === Level {level} 테스트 ===")
        
        try:
            # 전처리 적용
            processed_image = apply_default_filters(image, level=level)
            
            # 전처리된 이미지 저장
            debug_file = f"debug_img_4794_level_{level}.png"
            cv2.imwrite(debug_file, processed_image)
            logger.info(f"💾 전처리 이미지 저장: {debug_file}")
            
            # 이미지 통계
            unique_values = len(np.unique(processed_image))
            mean_val = np.mean(processed_image)
            
            # 텍스트 픽셀 비율 계산 (어두운 픽셀)
            if unique_values == 2:  # 이진화된 이미지
                dark_pixels = np.sum(processed_image == 0)
                total_pixels = processed_image.size
                text_ratio = dark_pixels / total_pixels * 100
            else:
                # 그레이스케일에서 어두운 픽셀 추정
                dark_pixels = np.sum(processed_image < 128)
                total_pixels = processed_image.size 
                text_ratio = dark_pixels / total_pixels * 100
            
            logger.info(f"📊 이미지 통계:")
            logger.info(f"   - 고유값: {unique_values}개")
            logger.info(f"   - 평균 밝기: {mean_val:.1f}")
            logger.info(f"   - 텍스트 픽셀 비율: {text_ratio:.1f}%")
            
            if text_ratio < 5:
                logger.warning(f"⚠️ 텍스트 픽셀 부족! OCR 실패 예상")
            elif text_ratio > 50:
                logger.warning(f"⚠️ 텍스트가 너무 많음! 노이즈 의심")
            else:
                logger.info(f"✅ 적절한 텍스트 비율")
            
            # OCR 테스트 (프로세스 분리 모드)
            try:
                # 임시로 level 변경해서 OCR 테스트
                original_level = 3  # 현재 설정
                result = ocr_engine.extract_text_easyocr(processed_image)
                
                if result and len(result.strip()) > 0:
                    logger.info(f"✅ Level {level} OCR 성공: {len(result)}자")
                    logger.info(f"📝 텍스트 샘플: {result[:100]}...")
                    
                    # 성공한 레벨이면 자세한 분석
                    if len(result) > 50:
                        logger.info(f"🎯 Level {level}이 최적입니다!")
                        return level
                else:
                    logger.error(f"❌ Level {level} OCR 실패: 0자")
                    
            except Exception as e:
                logger.error(f"❌ Level {level} OCR 오류: {e}")
                
        except Exception as e:
            logger.error(f"❌ Level {level} 전처리 실패: {e}")
    
    logger.info(f"\n💡 추가 분석 필요:")
    logger.info(f"   1. 이미지 품질 확인")
    logger.info(f"   2. 다른 OCR 엔진 시도")
    logger.info(f"   3. 수동 전처리 필요")
    
    return None

def apply_manual_preprocessing():
    """IMG_4794.JPG용 수동 전처리"""
    
    img_path = "uploads/IMG_4794.JPG"
    if not os.path.exists(img_path):
        img_path = "IMG_4794.JPG" 
    
    if not os.path.exists(img_path):
        logger.error("❌ IMG_4794.JPG를 찾을 수 없습니다!")
        return
    
    logger.info(f"\n🛠️ IMG_4794.JPG 수동 전처리 시작")
    
    # 원본 로드
    image = cv2.imread(img_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 다양한 전처리 시도
    methods = {
        "original": gray,
        "gaussian_blur": cv2.GaussianBlur(gray, (3,3), 0),
        "median_blur": cv2.medianBlur(gray, 5),
        "bilateral": cv2.bilateralFilter(gray, 9, 75, 75),
        "morphology": cv2.morphologyEx(gray, cv2.MORPH_CLOSE, np.ones((2,2), np.uint8)),
        "thresh_binary": cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        "thresh_adaptive": cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
        "contrast": cv2.convertScaleAbs(gray, alpha=1.5, beta=30),
    }
    
    for name, processed in methods.items():
        filename = f"manual_{name}_4794.png"
        cv2.imwrite(filename, processed)
        logger.info(f"💾 저장됨: {filename}")
    
    logger.info(f"✅ 수동 전처리 완료 - 각 결과를 확인하세요")

if __name__ == "__main__":
    print("\n🔧 IMG_4794.JPG 긴급 복구 시스템")
    print("=" * 50)
    
    # 1. 기본 디버깅
    optimal_level = debug_img_4794()
    
    # 2. 수동 전처리 시도  
    apply_manual_preprocessing()
    
    print(f"\n📋 권장사항:")
    if optimal_level:
        print(f"   ✅ Level {optimal_level} 사용 권장")
    else:
        print(f"   ⚠️ 모든 자동 전처리 실패")
        print(f"   💡 수동 전처리 결과 확인 필요")
    
    print(f"\n🔍 다음 단계:")
    print(f"   1. 생성된 debug_*.png 파일들 확인")
    print(f"   2. manual_*.png 파일들 확인") 
    print(f"   3. 가장 선명한 결과로 OCR 재시도")