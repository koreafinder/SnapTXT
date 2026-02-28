#!/usr/bin/env python3
"""
SnapTXT PC 앱 실행 스크립트
"""

import sys
import os
from pathlib import Path

def check_dependencies():
    """필수 의존성 확인"""
    missing_packages = []
    
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        missing_packages.append("PyQt5")
    
    try:
        import cv2
    except ImportError:
        missing_packages.append("opencv-python")
        
    try:
        import numpy
    except ImportError:
        missing_packages.append("numpy")
        
    try:
        from PIL import Image
    except ImportError:
        missing_packages.append("Pillow")
    
    if missing_packages:
        print("❌ 다음 패키지들이 없습니다:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n설치 명령어:")
        print(f"pip install {' '.join(missing_packages)}")
        print("\n또는 전체 의존성 설치:")
        print("pip install -r requirements_pc.txt")
        return False
    
    return True

def setup_dll_environment():
    """PyQt5 GUI 환경에서 PyTorch DLL 로딩 문제 해결"""
    try:
        # 가상환경 경로에서 PyTorch DLL 경로 확인
        venv_path = os.path.dirname(sys.executable)
        torch_dll_path = os.path.join(venv_path, "Lib", "site-packages", "torch", "lib")
        
        if os.path.exists(torch_dll_path):
            # PATH 환경변수에 torch/lib 추가 (최우선)
            current_path = os.environ.get('PATH', '')
            if torch_dll_path not in current_path:
                os.environ['PATH'] = f"{torch_dll_path}{os.pathsep}{current_path}"
                print(f"🔧 PyTorch DLL 경로를 PATH에 추가: {torch_dll_path}")
            
            # Windows DLL 디렉토리 명시적 등록
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(torch_dll_path)
                    print("🔧 Windows DLL 디렉토리 등록 완료")
                except Exception as e:
                    print(f"⚠️ DLL 디렉토리 등록 경고: {e}")
            
            # c10.dll 미리 로드 시도 (GUI 시작 전)
            c10_dll_path = os.path.join(torch_dll_path, "c10.dll")
            if os.path.exists(c10_dll_path):
                try:
                    import ctypes
                    ctypes.CDLL(c10_dll_path)
                    print("🔧 c10.dll 미리 로드 성공")
                except Exception as e:
                    print(f"⚠️ DLL 미리 로드 경고: {e}")
        
        return True
    except Exception as e:
        print(f"❌ DLL 환경 설정 실패: {e}")
        return False

def setup_qt_environment():
    """QT 플러그인 환경 설정"""
    try:
        venv_path = os.path.dirname(sys.executable)
        qt_plugin_path = os.path.join(venv_path, "Lib", "site-packages", "PyQt5", "Qt5", "plugins")
        
        if os.path.exists(qt_plugin_path):
            os.environ['QT_PLUGIN_PATH'] = qt_plugin_path
            print(f"🔧 QT_PLUGIN_PATH 설정: {qt_plugin_path}")
        
        return True
    except Exception as e:
        print(f"❌ Qt 환경 설정 실패: {e}")
        return False

def main():
    """메인 실행 함수"""
    print("🚀 SnapTXT PC 앱 시작 중...")
    
    # 현재 디렉토리를 스크립트 위치로 변경
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # GUI 환경 DLL 문제 해결
    print("🔧 GUI 환경 DLL 문제 해결 중...")
    if setup_dll_environment():
        print("✅ PyTorch DLL 환경 설정 완료")
    
    if setup_qt_environment():
        print("✅ Qt 환경 설정 완료")
    
    # 의존성 확인
    if not check_dependencies():
        input("\n❌ 의존성 설치 후 다시 실행해주세요. (엔터키로 종료)")
        return
    
    # PC 앱 실행
    try:
        from pc_app import main as run_pc_app
        print("✅ SnapTXT PC 앱을 실행합니다...")
        run_pc_app()
        
    except ImportError as e:
        print(f"❌ 모듈 import 오류: {e}")
        print("pc_app.py와 snaptxt/backend/multi_engine.py 경로 구성이 올바른지 확인해주세요.")
    except Exception as e:
        print(f"❌ 실행 오류: {e}")
    
    input("\n프로그램이 종료되었습니다. (엔터키로 닫기)")

if __name__ == "__main__":
    main()