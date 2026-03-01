#!/usr/bin/env python3
"""
IMG_4793.JPG 실패 원인 분석 및 해결
새로운 Adaptive 전처리 시스템이 실제로 적용되고 있는지 확인
"""

import cv2
import sys
import os
import logging
sys.path.append(os.path.dirname(__file__))

from snaptxt.backend.multi_engine import MultiOCRProcessor

# 상세 로깅 활성화
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_img_4793_debug():
    """IMG_4793.JPG 문제 원인 정확히 파악"""
    
    print("🔍 IMG_4793.JPG 실패 원인 분석")
    print("=" * 60)
    
    # 1. 이미지 존재 확인
    img_path = "experiments/samples/office_lens_test/IMG_4793.JPG"
    if not os.path.exists(img_path):
        print(f"❌ 이미지가 없습니다: {img_path}")
        return
    
    image = cv2.imread(img_path)
    if image is None:
        print(f"❌ 이미지 로드 실패")
        return
        
    print(f"✅ 이미지 로드 성공: {image.shape}")
    
    # 2. MultiOCRProcessor 초기화
    processor = MultiOCRProcessor()
    
    # 3. 직접 Adaptive 전처리 테스트
    print("\n📸 1. Adaptive 전처리 직접 테스트")
    try:
        processed = processor.preprocess_image(image, use_adaptive=True)
        print(f"   ✅ 전처리 성공: {processed.shape}")
        
        # 전처리된 이미지 저장해서 확인
        output_path = "debug_img_4793_adaptive.jpg"
        cv2.imwrite(output_path, processed)
        print(f"   💾 전처리 결과 저장: {output_path}")
        
    except Exception as e:
        print(f"   ❌ 전처리 실패: {e}")
        return
    
    # 4. PC 앱과 동일한 설정으로 전체 파이프라인 테스트
    print("\n🔧 2. 전체 OCR 파이프라인 테스트 (process_file)")
    
    settings = {
        'use_adaptive': True,  # ✅ Adaptive 전처리 활성화
        'engines': ['easyocr'],
        'language': 'ko,en'
    }
    
    try:
        # PC 앱과 동일한 방식으로 처리 (process_file 사용)
        result_text = processor.process_file(img_path, settings)
        
        print(f"   📊 결과 요약:")
        text_length = len(result_text)
        print(f"      텍스트 길이: {text_length}자")
        
        if text_length > 0:
            preview = result_text[:200]
            print(f"      미리보기: {preview}...")
            print("      ✅ OCR 성공!")
        else:
            print("      ❌ 텍스트 추출 실패")
                
    except Exception as e:
        print(f"   ❌ OCR 파이프라인 실패: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. 원본과 Adaptive 전처리 비교
    print("\n🆚 3. 원본 vs Adaptive 전처리 비교")
    
    # 원본 이미지로 OCR (전처리 없음)
    settings_original = {
        'use_adaptive': False,
        'preprocessing_level': 0,  # 전처리 없음
        'engines': ['easyocr'],
        'language': 'ko,en'
    }
    
    try:
        result_orig = processor.process_file(img_path, settings_original)
        orig_length = len(result_orig)
        print(f"   원본 이미지: {orig_length}자")
        
        if orig_length > 0:
            print(f"   원본 미리보기: {result_orig[:100]}...")
        
    except Exception as e:
        print(f"   원본 테스트 실패: {e}")
    
    # 6. 다른 성공 이미지와 비교
    print("\n📈 4. 성공 이미지 (IMG_4790) 비교 테스트")
    
    img_4790_path = "experiments/samples/office_lens_test/IMG_4790.JPG"
    if os.path.exists(img_4790_path):
        try:
            result_4790 = processor.process_file(img_4790_path, settings)
            length_4790 = len(result_4790)
            print(f"   IMG_4790.JPG: {length_4790}자 ✅")
            
            if length_4790 > 0:
                print(f"   IMG_4790 미리보기: {result_4790[:100]}...")
            
            # 전처리 비교
            img_4790 = cv2.imread(img_4790_path)
            processed_4790 = processor.preprocess_image(img_4790, use_adaptive=True)
            processed_4793 = processor.preprocess_image(image, use_adaptive=True)
            
            print(f"   전처리 결과 크기 비교:")
            print(f"      IMG_4790: {img_4790.shape} → {processed_4790.shape}")
            print(f"      IMG_4793: {image.shape} → {processed_4793.shape}")
            
        except Exception as e:
            print(f"   IMG_4790 테스트 실패: {e}")
    else:
        print(f"   ⚠️  IMG_4790.JPG 파일이 없습니다: {img_4790_path}")
    
    print("\n" + "=" * 60)
    print("🎯 분석 완료 - 위 결과를 확인하세요!")

if __name__ == "__main__":
    test_img_4793_debug()