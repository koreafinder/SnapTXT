@echo off
chcp 65001 >nul 2>&1
REM SnapTXT Development Compass - 문서 상태 빠른 확인
REM "30초 현황 파악"을 위한 문서 검증
REM 사용법: 
REM   check_docs.bat          - 필수 문서만 확인
REM   check_docs.bat optional - 선택 문서도 확인
REM   check_docs.bat ci       - CI 모드로 확인 (오류 시 종료)

setlocal
cd /d "%~dp0"

echo 📋 SnapTXT Development Compass 문서 상태 확인...

REM 가상환경 활성화
if exist ".venv_new\Scripts\python.exe" (
    set "PYTHON_EXE=.venv_new\Scripts\python.exe"
) else (
    set PYTHON_EXE=python
)

REM 인자에 따른 실행
if /i "%1"=="optional" (
    echo 🔍 선택 문서 포함하여 검사...
    "%PYTHON_EXE%" "tools\check_docs.py" --show-optional
) else if /i "%1"=="ci" (
    echo 🤖 CI 모드로 검사...
    "%PYTHON_EXE%" "tools\check_docs.py" --ci --no-open --show-optional
    if errorlevel 1 (
        echo ❌ 문서 검증 실패!
        exit /b 1
    )
    echo ✅ 문서 검증 통과!
) else (
    echo 📋 필수 문서 검사...
    "%PYTHON_EXE%" "tools\check_docs.py"
)

echo.
echo 💡 사용 팁:
echo   check_docs.bat optional  - 선택 문서도 함께 확인
echo   check_docs.bat ci        - CI 형태로 검증 (스크립트용)
echo   🔗 자세한 규칙: docs\README.md