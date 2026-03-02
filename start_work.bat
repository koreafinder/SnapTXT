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

echo.
echo 📂 작업 파일 열기...
echo ------------------------------------------
echo 문서 정책에 따라 Current_Work.md를 VS Code에서 자동으로 엽니다...

REM VS Code Workspace로 깔끔하게 시작
if exist "SnapTXT.code-workspace" (
    echo ✅ SnapTXT workspace 발견, 깔끔한 세션으로 시작...
    code SnapTXT.code-workspace 2>nul && (
        echo ✅ SnapTXT workspace가 VS Code에서 열렸습니다.
        echo 💡 이제 세션 복원 문제가 해결됩니다.
    ) || (
        echo ⚠️ Workspace 열기 실패, 기본 방법으로 시작...
        code "docs\status\current_work.md" 2>nul
    )
    
    REM current_work.md 자동으로 열기
    timeout /t 2 /nobreak >nul 2>&1
    code "docs\status\current_work.md" 2>nul
    
) else if exist "docs\status\current_work.md" (
    echo ✅ Current_Work.md 발견, 기존 방법으로 열기...
    code "docs\status\current_work.md" 2>nul && (
        echo ✅ Current_Work.md가 VS Code에서 열렸습니다.
        echo 💡 Ctrl+W로 불필요한 restructure_plan.md 탭을 닫아주세요.
    )
) else (
    echo ❌ 필요한 파일들이 존재하지 않습니다.
)

echo.
echo 💡 문서 읽기 순서: Project_Memory.md → Architecture.md → Current_Work.md → progress_flow.md
echo 💡 현재 단계: P2 문서 시스템 정리 및 AI 협업 최적화
echo.
echo ✨ 작업 환경 준비 완료!
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