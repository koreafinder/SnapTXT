#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EasyOCR DLL 오류 심층 진단 스크립트
"""

import logging
import sys
import os

print("🔬 EasyOCR DLL 오류 심층 진단 시작...")

try:
    print("1️⃣ 기본 환경 정보")
    print(f"   Python 버전: {sys.version}")
    print(f"   실행 경로: {sys.executable}")
    print(f"   작업 디렉토리: {os.getcwd()}")
    
    print("\n2️⃣ PyTorch 및 DLL 경로 확인")
    try:
        import torch
        print(f"   ✅ PyTorch 버전: {torch.__version__}")
        
        # DLL 경로 확인
        torch_path = torch.__file__
        torch_lib_path = os.path.join(os.path.dirname(torch_path), 'lib')
        c10_dll_path = os.path.join(torch_lib_path, 'c10.dll')
        
        print(f"   📁 PyTorch 경로: {torch_path}")
        print(f"   📁 PyTorch lib 경로: {torch_lib_path}")
        print(f"   📁 c10.dll 존재: {os.path.exists(c10_dll_path)}")
        
        if os.path.exists(c10_dll_path):
            file_size = os.path.getsize(c10_dll_path)
            print(f"   📊 c10.dll 크기: {file_size:,} bytes")
    
    except Exception as e:
        print(f"   ❌ PyTorch 검사 실패: {e}")
    
    print("\n3️⃣ Visual C++ Redistributable 확인")
    try:
        import platform
        print(f"   OS: {platform.platform()}")
        
        # msvcr DLL 확인
        import ctypes
        try:
            msvcr = ctypes.cdll.msvcr120  # Visual C++ 2013
            print("   ✅ Visual C++ 2013 Redistributable 감지됨")
        except:
            print("   ⚠️ Visual C++ 2013 Redistributable 없음")
            
        try:
            kernel32 = ctypes.windll.kernel32
            print("   ✅ Windows 기본 DLL 접근 가능")
        except Exception as e:
            print(f"   ❌ Windows DLL 접근 실패: {e}")
            
    except Exception as e:
        print(f"   ❌ VC++ 확인 실패: {e}")
    
    print("\n4️⃣ PATH 환경변수 확인")
    path_var = os.environ.get('PATH', '')
    path_list = path_var.split(os.pathsep)
    
    torch_in_path = any('torch' in p for p in path_list)
    print(f"   🔍 PATH에 torch 경로: {torch_in_path}")
    
    # PyTorch DLL 경로가 PATH에 있는지 확인
    venv_path = os.path.dirname(sys.executable)
    expected_torch_lib = os.path.join(venv_path, "Lib", "site-packages", "torch", "lib")
    torch_lib_in_path = expected_torch_lib in path_list
    print(f"   🔍 PATH에 torch/lib: {torch_lib_in_path}")
    
    print("\n5️⃣ 메모리/프로세스 환경 확인")
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        print(f"   💾 메모리 사용량: {memory_info.rss / (1024*1024):.1f} MB")
        print(f"   👤 실행 사용자: {process.username()}")
    except:
        print("   ⚠️ psutil 없음 - 메모리 정보 확인 불가")
    
    print("\n6️⃣ EasyOCR 임포트 단독 테스트")
    try:
        # 환경변수 설정 없이 먼저 시도
        print("   🧪 환경변수 설정 없이 import 시도...")
        import easyocr
        print("   ✅ EasyOCR import 성공!")
        
        # Reader 생성 시도
        print("   🧪 EasyOCR Reader 생성 시도...")
        reader = easyocr.Reader(['ko', 'en'], gpu=False, verbose=False)
        print("   ✅ EasyOCR Reader 생성 성공!")
        
    except Exception as e:
        print(f"   ❌ EasyOCR 테스트 실패: {e}")
        print(f"   📋 오류 타입: {type(e)}")
        
        # 더 상세한 오류 정보
        import traceback
        print("   📋 상세 스택 트레이스:")
        traceback.print_exc()
    
    print("\n7️⃣ GUI vs 스크립트 환경 차이 분석")
    # QApplication이 실행 중인지 확인
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            print("   🖥️ PyQt5 QApplication 실행 중")
            print(f"   🖥️ 앱 이름: {app.applicationName()}")
        else:
            print("   📝 PyQt5 QApplication 없음 (순수 스크립트 환경)")
    except Exception as e:
        print(f"   ⚠️ PyQt5 확인 실패: {e}")

except Exception as e:
    print(f"\n🚨 진단 스크립트 오류: {e}")
    import traceback
    traceback.print_exc()

print("\n🔬 심층 진단 완료!")