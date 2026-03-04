#!/usr/bin/env python3
"""
후처리 시스템 디버깅 테스트
==========================

빈 문자열 반환 문제 원인 조사
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import logging
from snaptxt.postprocess import run_pipeline, Stage2Config, Stage3Config

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_simple_postprocessing():
    """간단한 후처리 테스트"""
    
    print("🔍 후처리 시스템 디버깅 테스트")
    print("="*50)
    
    # 테스트 텍스트 (실제 OCR 결과와 유사)
    test_texts = [
        "안녕하세요 이것은 테스트입니다",
        "마이컨생어 Michael A Singer 숲속의 명상가로 불리는 마이클 싱어는 대중 앞에 나서기를 꺼려",
        "일러두기 : ( 명상 저널 ) 은 저자가 ( 상처받지 암논 영혼>에서 직접 발휘한 핵심 문장과"
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n🧪 테스트 {i}: {len(text)}자")
        print(f"입력: {text[:50]}...")
        
        try:
            # Context-aware 비활성화
            result_no_context = run_pipeline(
                text,
                stage2_config=Stage2Config(),
                stage3_config=Stage3Config(),
                enable_context_aware=False,
                logger=logger
            )
            
            print(f"결과 (Context OFF): '{result_no_context}'")
            print(f"길이 (Context OFF): {len(result_no_context)}자")
            
            # Context-aware 활성화
            result_with_context = run_pipeline(
                text,
                stage2_config=Stage2Config(),
                stage3_config=Stage3Config(),
                enable_context_aware=True,
                logger=logger
            )
            
            print(f"결과 (Context ON): '{result_with_context}'")
            print(f"길이 (Context ON): {len(result_with_context)}자")
            
            if len(result_no_context) == 0:
                print("❌ 후처리 시스템이 빈 문자열 반환!")
            else:
                print("✅ 후처리 정상 작동")
                
        except Exception as e:
            print(f"❌ 오류: {e}")
            import traceback
            print(traceback.format_exc())
    
    print("\n" + "="*50)
    print("테스트 완료")

if __name__ == "__main__":
    test_simple_postprocessing()