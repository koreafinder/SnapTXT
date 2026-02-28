#!/usr/bin/env python3
"""전처리 레벨별 상세 디버깅 테스트"""

import cv2
import numpy as np
import tempfile
from pathlib import Path
from snaptxt.preprocess import apply_default_filters
from snaptxt.backend.worker.easyocr_worker import process_image_easyocr
import logging

# 디버깅 로그 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def create_test_text_image():
    """읽기 쉬운 테스트 텍스트 이미지 생성"""
    # 더 큰 이미지로 생성
    img = np.ones((600, 800, 3), dtype=np.uint8) * 250
    
    # 더 명확한 텍스트 추가
    cv2.putText(img, "Simple Test Text", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 3)
    cv2.putText(img, "Level Comparison", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 3)
    cv2.putText(img, "Korean: 한국어 테스트", (50, 350), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
    
    # 약간의 노이즈 추가 (적당히)
    noise = np.random.normal(0, 10, img.shape).astype(np.uint8)
    noisy_img = cv2.add(img, noise)
    
    return noisy_img

def test_with_detailed_logging():
    """상세한 로깅과 함께 전처리 테스트"""
    
    test_img = create_test_text_image()
    print("🎯 상세 전처리 디버깅 테스트 시작")
    print("=" * 60)
    
    for level in [1, 2, 3]:
        print(f"\n🔍 === Level {level} 상세 분석 ===")
        
        # 전처리 적용 (디버깅 모드)
        try:
            processed = apply_default_filters(test_img, level=level)
            
            # 처리된 이미지 저장
            debug_filename = f"test_level_{level}_processed.png"
            cv2.imwrite(debug_filename, processed)
            print(f"💾 처리된 이미지 저장: {debug_filename}")
            
            # 이미지 통계
            if processed.ndim == 2:  # 그레이스케일
                unique_vals = len(np.unique(processed))
                min_val, max_val = np.min(processed), np.max(processed)
                mean_val = np.mean(processed)
                print(f"📊 이미지 통계: {processed.shape}, 고유값 {unique_vals}개")
                print(f"📊 픽셀 범위: {min_val}~{max_val}, 평균: {mean_val:.1f}")
                
                # 텍스트/배경 비율 분석
                dark_pixels = np.sum(processed < 128)
                light_pixels = np.sum(processed >= 128)
                text_ratio = dark_pixels / (dark_pixels + light_pixels) * 100
                print(f"📊 어두운 픽셀(텍스트): {text_ratio:.1f}%, 밝은 픽셀(배경): {100-text_ratio:.1f}%")
                
                # OCR 적합성 예측
                if text_ratio < 5:
                    print("⚠️ 경고: 텍스트 픽셀이 너무 적음 - OCR 성능 저하 예상")
                elif text_ratio > 50:
                    print("⚠️ 경고: 배경이 너무 어두움 - OCR 성능 저하 예상")
                else:
                    print("✅ 양호: 텍스트/배경 비율 적절")
            
            # OCR 테스트
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            cv2.imwrite(tmp_path, processed)
            result = process_image_easyocr(tmp_path)
            
            if result.get('success'):
                text = result.get('text', '')
                char_count = len(text.replace(' ', ''))
                exec_time = result.get('execution_time', 0)
                
                print(f"✅ OCR 성공: {char_count}자 추출")
                print(f"⏱️ 처리 시간: {exec_time:.2f}초")
                print(f"📝 추출 텍스트: '{text.strip()}'")
                
                # 품질 점수
                expected_chars = 35  # 예상 문자 수
                quality = min(100, (char_count / expected_chars) * 100)
                print(f"🎯 품질 점수: {quality:.1f}%")
                
                if quality < 50:
                    print("❌ 품질 불량: OCR 성능이 크게 저하됨")
                elif quality < 80:
                    print("⚠️ 품질 보통: 약간의 성능 저하")
                else:
                    print("✅ 품질 우수: OCR 성능 양호")
                    
            else:
                print(f"❌ OCR 실패: {result.get('error')}")
                
            Path(tmp_path).unlink(missing_ok=True)
            
        except Exception as e:
            print(f"❌ Level {level} 테스트 실패: {e}")
    
    print(f"\n🎯 결론 및 권장사항:")
    print("   • 각 레벨의 디버그 이미지를 확인하세요")
    print("   • Level 1이 가장 안정적일 가능성 높음") 
    print("   • Level 3은 과도한 전처리로 오히려 역효과 가능")

if __name__ == "__main__":
    test_with_detailed_logging()