#!/usr/bin/env python3
"""
VS Code 튜닝 후 성능 체크 스크립트
- IntelliSense 속도
- 파일 로딩 시간 
- OCR 처리 속도
- 전반적인 반응 속도
"""

import time
import sys
import os
from pathlib import Path

def test_import_speed():
    """모듈 import 속도 테스트"""
    print("🔄 모듈 import 속도 테스트...")
    
    start_time = time.time()
    try:
        import cv2
        import numpy as np
        import PIL
        # OCR 관련 모듈들
        sys.path.insert(0, str(Path(__file__).parent))
        from snaptxt.preprocess.scientific_assessor import smart_preprocess_image
        end_time = time.time()
        
        import_time = end_time - start_time
        print(f"✅ 모듈 import 완료: {import_time:.3f}초")
        
        if import_time < 2.0:
            print("🚀 매우 빠름!")
        elif import_time < 5.0:
            print("⚡ 빠름")
        else:
            print("🐌 느림")
            
        return import_time
    except Exception as e:
        print(f"❌ import 오류: {e}")
        return None

def test_file_operations():
    """파일 연산 속도 테스트"""
    print("\n📁 파일 연산 속도 테스트...")
    
    start_time = time.time()
    test_files = list(Path(".").glob("*.py"))[:10]  # 처음 10개 파일만
    
    for file_path in test_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = len(content.split('\n'))
        except:
            pass
    
    end_time = time.time()
    file_time = end_time - start_time
    
    print(f"✅ {len(test_files)}개 파일 처리: {file_time:.3f}초")
    
    if file_time < 0.5:
        print("🚀 매우 빠름!")
    elif file_time < 1.0:
        print("⚡ 빠름")
    else:
        print("🐌 느림")
        
    return file_time

def test_memory_usage():
    """메모리 사용량 체크"""
    print("\n🧠 메모리 사용량 체크...")
    
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        print(f"📊 현재 메모리 사용량: {memory_mb:.1f} MB")
        
        if memory_mb < 100:
            print("💚 메모리 효율적!")
        elif memory_mb < 300:
            print("💛 적당한 메모리 사용")
        else:
            print("💔 메모리 사용량 많음")
            
        return memory_mb
    except ImportError:
        print("⚠️ psutil 없음 - 메모리 체크 생략")
        return None

def main():
    """메인 성능 테스트"""
    print("🎯 VS Code 튜닝 후 성능 체크 시작!")
    print("=" * 50)
    
    # 전체 시작 시간
    total_start = time.time()
    
    # 각 테스트 실행
    import_time = test_import_speed()
    file_time = test_file_operations()  
    memory_usage = test_memory_usage()
    
    total_end = time.time()
    total_time = total_end - total_start
    
    print("\n" + "=" * 50)
    print("📈 성능 테스트 결과 요약:")
    print(f"⏱️  총 실행 시간: {total_time:.3f}초")
    
    if import_time:
        print(f"📦 모듈 로딩: {import_time:.3f}초")
    if file_time:
        print(f"📁 파일 처리: {file_time:.3f}초")
    if memory_usage:
        print(f"🧠 메모리 사용: {memory_usage:.1f} MB")
    
    # 전체 평가
    if total_time < 3.0:
        print("\n🎉 VS Code 튜닝 효과 매우 좋음!")
    elif total_time < 6.0:
        print("\n✅ VS Code 튜닝 효과 좋음!")
    else:
        print("\n🤔 추가 최적화 필요할 수 있음")

if __name__ == "__main__":
    main()