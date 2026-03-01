@echo off
chcp 65001 >nul 2>&1
REM SnapTXT 새 기획서 생성 및 current_work.md 자동 연동 스크립트
REM 사용법:
REM   create_plan.bat "기획서명"                    - plans 카테고리로 생성
REM   create_plan.bat "기획서명" "plans"            - plans 카테고리로 생성  
REM   create_plan.bat "기획서명" "reference"        - reference 카테고리로 생성
REM   create_plan.bat "기획서명" "analysis"         - analysis 카테고리로 생성

setlocal
cd /d "%~dp0"

REM 인수 확인
if "%~1"=="" (
    echo ❌ 오류: 기획서 이름을 입력해주세요.
    echo.
    echo 💡 사용법:
    echo   create_plan.bat "기획서명"                    - plans 카테고리로 생성
    echo   create_plan.bat "기획서명" "plans"            - plans 카테고리
    echo   create_plan.bat "기획서명" "reference"        - reference 카테고리  
    echo   create_plan.bat "기획서명" "analysis"         - analysis 카테고리
    echo.
    echo 📚 사용 가능한 템플릿:
    python tools\create_planning_doc.py --list-templates
    exit /b 1
)

set PLAN_NAME=%~1
set PLAN_TYPE=%~2

REM 기본값 설정
if "%PLAN_TYPE%"=="" set PLAN_TYPE=plans

REM 가상환경 확인
if exist ".venv_new\Scripts\python.exe" (
    set "PYTHON_EXE=.venv_new\Scripts\python.exe"
) else (
    set PYTHON_EXE=python
)

echo.
echo 📝 새 기획서 생성 시작...
echo ==========================================
echo 📄 기획서 이름: %PLAN_NAME%
echo 📂 카테고리: %PLAN_TYPE%
echo 🐍 Python: %PYTHON_EXE%
echo.

REM 1단계: 기획서 템플릿 생성
echo [1/4] 기획서 템플릿 생성 중...
echo ------------------------------------------
"%PYTHON_EXE%" "tools\create_planning_doc.py" --name "%PLAN_NAME%" --type "%PLAN_TYPE%"

if errorlevel 1 (
    echo ❌ 기획서 생성에 실패했습니다.
    exit /b 1
)

echo.

REM 2단계: current_work.md에 링크 추가
echo [2/4] current_work.md 연동 중...
echo ------------------------------------------
"%PYTHON_EXE%" "tools\update_current_work.py" --add-planning-doc "%PLAN_NAME%" --category "%PLAN_TYPE%" --description "%PLAN_NAME% 기획 및 실행" --status "진행중 - 신규"

if errorlevel 1 (
    echo ❌ current_work.md 업데이트에 실패했습니다.
    exit /b 1
)

echo.

REM 3단계: 문서 시스템 검증
echo [3/4] 문서 시스템 무결성 검증...
echo ------------------------------------------
call check_docs.bat optional

echo.

REM 4단계: 최종 상태 확인
echo [4/4] 최종 상태 확인...
echo ------------------------------------------
"%PYTHON_EXE%" tools\show_current_status.py --show-active-plans

echo.
echo ==========================================
echo ✅ 새 기획서 생성 완료!
echo ==========================================
echo.

REM 생성된 파일 경로 구성
set FILENAME=%PLAN_NAME: =_%
set FILENAME=%FILENAME:-=_%
for /L %%i in (1,1,100) do if "!FILENAME:~%%i,1!"=="" goto :FilenameDone
:FilenameDone
set FILENAME=%FILENAME%.md

echo 💡 다음 단계:
echo ------------------------------------------
echo 1. VS Code에서 기획서 편집: 
if "%PLAN_TYPE%"=="plans" (
    echo    code docs\plans\%FILENAME%
) else if "%PLAN_TYPE%"=="reference" (
    echo    code docs\reference\%FILENAME%
) else if "%PLAN_TYPE%"=="analysis" (
    echo    code docs\plans\%FILENAME%
) else (
    echo    code docs\%PLAN_TYPE%\%FILENAME%
)

echo.
echo 2. 현재 상황 재확인:
echo    .\start_work.bat
echo.
echo 3. 작업 완료 시:
echo    .\finish_work.bat "기획서 작성 완료"
echo.

echo 🎯 현재 활성 기획서에서 '%PLAN_NAME%'를 확인할 수 있습니다.
echo    파일이 current_work.md에 자동으로 연동되었습니다!

echo.
pause