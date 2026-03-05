@echo off
chcp 65001 >nul 2>&1
REM SnapTXT 작업 세션 시작 - current-work.md가 Single Source of Truth
REM 목적: "30초 현황 파악" 후 바로 작업 시작

setlocal
cd /d "%~dp0"

echo.
echo 🧭 SnapTXT 작업 세션 시작
echo ==========================================
echo   현재 상황은 docs\status\current-work.md 에서 확인하세요
echo   📍 Single Source of Truth
echo.

echo 📍 현재 위치: v2.1.3 Stable (고정점) + v2.2 Learning (작업 영역)
echo 📋 오늘 할 일: docs\status\current-work.md 확인 필수
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
echo 🎯 우선순위 작업 현황...
echo ------------------------------------------
echo ✨ 상세 내용: docs\status\current-work.md 확인
echo   📍 Single Source of Truth - 모든 현재 상황 집합
echo   🔄 v2.2 Learning System 작업 영역

echo.
echo 📊 현재 시스템 상태 분석...
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
echo 2. PC 앱 실행:          python run_pc_app.py  (권장 - 환경 문제 자동 해결)
echo    └── 직접 실행:        python pc_app.py      (고급 사용자용)
echo 3. 문서 전체 확인:       .\check_docs.bat optional
echo 4. 회귀 테스트 실행:     powershell -ExecutionPolicy Bypass -File "scripts\run_regression.ps1"
echo 5. 새 기획서 생성:       .\create_plan.bat "기획서명" "plans"
echo.
echo 📱 PC 앱 사용 팁:
echo   run_pc_app.py = 런처 (의존성 확인 + DLL 문제 해결 + pc_app.py 실행)
echo   pc_app.py     = 실제 PyQt5 GUI 애플리케이션
echo   💡 처음 사용 시 run_pc_app.py 권장 (환경 문제 자동 해결)

echo.
echo 🎯 현재 우선순위: AI 워크플로우 자동화 시스템 구축
echo    관련 문서: docs\plans\ai_workflow_automation.md
echo.
echo ==========================================
echo 🎉 작업 세션 준비 완료! 즐거운 개발 되세요!
echo ==========================================
echo.