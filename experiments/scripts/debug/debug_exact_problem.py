#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MultiOCRProcessor 단독 테스트 - 정확한 오류 시점 파악
"""

import logging
import sys

# 상세한 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG 레벨로 더 상세히
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

print("🔍 MultiOCRProcessor 단독 테스트 시작...")

try:
    print("🔧 1. EasyOCR 모듈 import 테스트")
    import easyocr
    print("✅ EasyOCR import 성공")
    
    print("\n🔧 2. EasyOCR GPU 모드 시도")
    try:
        print("  - GPU=True로 리더 생성 시도 중...")
        reader_gpu = easyocr.Reader(['ko', 'en'], gpu=True)
        print("✅ GPU 모드 성공!")
        del reader_gpu  # 메모리 정리
    except Exception as gpu_error:
        print(f"❌ GPU 모드 실패: {gpu_error}")
        print(f"   오류 타입: {type(gpu_error)}")
        
        print("\n🔧 3. EasyOCR CPU 모드 시도")
        try:
            print("  - GPU=False로 리더 생성 시도 중...")
            reader_cpu = easyocr.Reader(['ko', 'en'], gpu=False)
            print("✅ CPU 모드 성공!")
            del reader_cpu  # 메모리 정리
        except Exception as cpu_error:
            print(f"❌ CPU 모드도 실패: {cpu_error}")
            print(f"   오류 타입: {type(cpu_error)}")
            raise cpu_error
    
    print("\n🔧 4. MultiOCRProcessor 클래스 테스트")
    from snaptxt.backend.multi_engine import MultiOCRProcessor
    print("✅ MultiOCRProcessor import 성공")
    
    print("  - MultiOCRProcessor 인스턴스 생성 중...")
    processor = MultiOCRProcessor()
    print("✅ MultiOCRProcessor 생성 성공")
    
    print(f"🎯 초기화된 엔진들: {list(processor.engines.keys())}")
    
    if 'easyocr' in processor.engines:
        print("✅ EasyOCR 엔진 정상 초기화됨")
    else:
        print("❌ EasyOCR 엔진 초기화 실패")

except Exception as e:
    print(f"\n🚨 최종 오류 발생: {e}")
    import traceback
    print("\n📋 상세 오류 정보:")
    traceback.print_exc()