@echo off
chcp 65001 >nul 2>&1
REM SnapTXT 작업 세션 시작 스크립트
REM 목적: VS Code 실행 후 AI와 사용자가 현재 상황을 즉시 파악할 수 있도록 함

setlocal
cd /d "%~dp0"

echo.
echo 🚀 SnapTXT 작업 세션 시작...
echo ==========================================
echo.

REM 가상환경 확인
if exist ".venv_new\Scripts\python.exe" (
    set "PYTHON_EXE=.venv_new\Scripts\python.exe"
    echo ✅ Python 환경: .venv_new 가상환경 감지됨
) else (
    set PYTHON_EXE=python
    echo ⚠️ Python 환경: 시스템 Python 사용
)

echo.
echo 📋 문서 시스템 상태 확인...
echo ------------------------------------------
call check_docs.bat

echo.
echo 📊 현재 작업 상황 분석...
echo ------------------------------------------
"%PYTHON_EXE%" tools\show_current_status.py

echo.
echo 🔍 최근 Git 변경사항...
echo ------------------------------------------
git log --oneline -5 --color=always 2>nul || (
    echo ❌ Git 저장소가 감지되지 않았거나 Git이 설치되지 않음
)

echo.
echo 🔧 환경 상태 점검...
echo ------------------------------------------
echo Python 실행 파일: %PYTHON_EXE%
"%PYTHON_EXE%" --version 2>nul || echo ❌ Python 실행 실패

REM 주요 패키지 버전 확인
echo.
echo 📦 주요 패키지 버전:
"%PYTHON_EXE%" -c "import easyocr; print(f'  EasyOCR: {easyocr.__version__}')" 2>nul || echo "  EasyOCR: 미설치"
"%PYTHON_EXE%" -c "import cv2; print(f'  OpenCV: {cv2.__version__}')" 2>nul || echo "  OpenCV: 미설치"
"%PYTHON_EXE%" -c "import torch; print(f'  PyTorch: {torch.__version__}')" 2>nul || echo "  PyTorch: 미설치"

echo.
echo 💡 추천 다음 단계...
echo ------------------------------------------
echo 1. 메인 웹 서버 실행:     python main.py
echo 2. PC 앱 실행:          python pc_app.py  
echo 3. 문서 전체 확인:       .\check_docs.bat optional
echo 4. 회귀 테스트 실행:     powershell -ExecutionPolicy Bypass -File "scripts\run_regression.ps1"
echo 5. 새 기획서 생성:       .\create_plan.bat "기획서명" "plans"

echo.
echo 🎯 현재 우선순위: AI 워크플로우 자동화 시스템 구축
echo    관련 문서: docs\plans\ai_workflow_automation.md
echo.
echo ==========================================
echo 🎉 작업 세션 준비 완료! 즐거운 개발 되세요!
echo ==========================================
echo.