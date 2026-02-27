#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi OCR Processor 디버깅 - 초기화 과정 확인
"""

import logging
import sys

# 로깅 활성화
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

print("🔍 MultiOCRProcessor 디버깅 시작...")

try:
    from multi_ocr_processor import MultiOCRProcessor
    
    print("📦 MultiOCRProcessor 클래스 import 성공")
    
    print("⚙️ OCR 엔진들 초기화 중...")
    processor = MultiOCRProcessor()
    
    print(f"✅ 초기화 완료!")
    print(f"📊 초기화된 엔진 수: {len(processor.engines)}")
    print(f"🎯 사용 가능한 엔진들: {list(processor.engines.keys())}")
    
    # 각 엔진 상태 확인
    for engine_name in ['easyocr', 'tesseract', 'paddleocr']:
        status = "✅ 초기화됨" if engine_name in processor.engines else "❌ 초기화 실패" 
        print(f"  - {engine_name}: {status}")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()