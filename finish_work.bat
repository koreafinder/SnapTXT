@echo off
chcp 65001 >nul 2>&1
REM SnapTXT Development Compass - 작업 완료 및 정리 스크립트
REM "증거 중심 문서화" 로 오늘의 성과 기록
REM 사용법:
REM   finish_work.bat "커밋 메시지"                     - 전체 완료 처리
REM   finish_work.bat "커밋 메시지" --git-only          - Git 작업만
REM   finish_work.bat "커밋 메시지" --docs-only         - 문서 정리만
REM   finish_work.bat --dry-run                        - 시뮬레이션

setlocal
cd /d "%~dp0"

set COMMIT_MSG=%~1
set EXTRA_ARGS=%~2 %~3 %~4 %~5

REM 가상환경 확인
if exist ".venv_new\Scripts\python.exe" (
    set "PYTHON_EXE=.venv_new\Scripts\python.exe"
) else (
    set PYTHON_EXE=python
)

echo.
echo 🎉 작업 완료 정리 시작...
echo ==========================================

REM 도움말 표시
if "%~1"=="" (
    echo ❓ 사용법:
    echo   finish_work.bat "커밋 메시지"                     - 전체 완료 처리
    echo   finish_work.bat "커밋 메시지" --git-only          - Git 작업만
    echo   finish_work.bat "커밋 메시지" --docs-only         - 문서 정리만  
    echo   finish_work.bat --dry-run                        - 시뮬레이션
    echo.
    echo 💡 예시:
    echo   finish_work.bat "AI 워크플로우 자동화 완료"
    echo   finish_work.bat "문서 정리" --docs-only
    echo   finish_work.bat --dry-run
    echo.
    goto :show_current_status
)

REM 시뮬레이션 모드 확인
if "%~1"=="--dry-run" (
    echo 🎭 시뮬레이션 모드로 실행합니다...
    echo.
    "%PYTHON_EXE%" "tools\finalize_work.py" --dry-run
    goto :end
)

REM 커밋 메시지가 없으면 기본값 사용
if "%COMMIT_MSG%"=="" (
    for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (
        set TODAY=%%c-%%a-%%b
    )
    set COMMIT_MSG=작업 정리 및 문서 업데이트 (!TODAY!)
    echo 💬 기본 커밋 메시지 사용: !COMMIT_MSG!
    echo.
)

echo 📝 커밋 메시지: %COMMIT_MSG%
echo 🛠️ 추가 옵션: %EXTRA_ARGS%
echo 🐍 Python: %PYTHON_EXE%
echo.

REM 현재 활성 기획서 확인
echo [사전 확인] 현재 활성 기획서 상태...
echo ------------------------------------------
"%PYTHON_EXE%" tools\show_current_status.py --show-active-plans
echo.

REM 사용자 확인
echo ⚠️ 다음 작업이 수행됩니다:
echo   1. 완료된 기획서들을 experiments/results/로 이동
echo   2. current_work.md에서 완료된 항목 정리
echo   3. Git add, commit, push 실행
echo   4. 문서 시스템 무결성 검증
echo.

REM Git 상태 확인
git status --porcelain >nul 2>&1
if errorlevel 1 (
    echo ℹ️ Git 저장소가 아니거나 Git이 설치되지 않았습니다.
    echo    Git 작업을 건너뛰고 문서 정리만 진행합니다.
    set EXTRA_ARGS=%EXTRA_ARGS% --no-git
) else (
    git status --porcelain | findstr /r "." >nul
    if errorlevel 1 (
        echo ℹ️ Git에 변경사항이 없습니다.
    ) else (
        echo 📋 Git 변경사항이 감지되었습니다:
        git status --short
        echo.
    )
)

REM 확인 요청 (dry-run이나 특정 모드가 아닐 때만)
echo %EXTRA_ARGS% | findstr /c:"--dry-run" >nul
if not errorlevel 1 goto :execute

echo %EXTRA_ARGS% | findstr /c:"--git-only" >nul
if not errorlevel 1 goto :execute

echo %EXTRA_ARGS% | findstr /c:"--docs-only" >nul
if not errorlevel 1 goto :execute

set /p CONFIRM=계속 진행하시겠습니까? (Y/n): 
if /i "%CONFIRM%"=="n" (
    echo 작업이 취소되었습니다.
    goto :end
)
if /i "%CONFIRM%"=="no" (
    echo 작업이 취소되었습니다.
    goto :end
)

echo.

:execute
REM finalize_work.py 실행
echo 🚀 작업 완료 처리 실행...
echo ------------------------------------------
if "%COMMIT_MSG%"=="" (
    "%PYTHON_EXE%" "tools\finalize_work.py" %EXTRA_ARGS%
) else (
    "%PYTHON_EXE%" "tools\finalize_work.py" --commit-msg "%COMMIT_MSG%" %EXTRA_ARGS%
)

if errorlevel 1 (
    echo.
    echo ❌ 작업 완료 처리 중 오류가 발생했습니다.
    exit /b 1
)

echo.
echo ==========================================
echo ✅ 작업 완료 정리가 모두 끝났습니다!
echo ==========================================
echo.

REM 최종 상태 확인
echo 📊 최종 상태 확인:
echo ------------------------------------------
"%PYTHON_EXE%" tools\show_current_status.py
echo.

echo 💡 다음 작업 세션을 위해:
echo   .\start_work.bat
echo.

goto :end

:show_current_status
echo 📊 현재 활성 기획서 상태:
echo ------------------------------------------
"%PYTHON_EXE%" tools\show_current_status.py --show-active-plans

:end
echo.
pause