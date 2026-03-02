@echo off
REM SnapTXT Phase 1 자동 패턴 분석 및 규칙 생성 스크립트
REM 사용법: run_phase1_tools.bat [analyze|generate|validate|all]

echo.
echo ==========================================
echo  SnapTXT Phase 1 자동화 도구 실행기
echo ==========================================
echo.

if "%1"=="analyze" goto ANALYZE
if "%1"=="generate" goto GENERATE 
if "%1"=="validate" goto VALIDATE
if "%1"=="all" goto ALL

echo 사용법: run_phase1_tools.bat [옵션]
echo.
echo 옵션:
echo   analyze   - 로그 분석만 실행
echo   generate  - YAML 규칙 생성만 실행
echo   validate  - 규칙 검증만 실행
echo   all       - 전체 프로세스 실행 (기본값)
echo.
echo 예제:
echo   run_phase1_tools.bat all
echo   run_phase1_tools.bat analyze
echo.
goto END

:ANALYZE
echo [1/1] 로그 기반 패턴 분석 실행...
python tools/pattern_analyzer.py --analyze-logs
if errorlevel 1 goto ERROR
echo.
echo ✅ 패턴 분석 완료!
echo 결과: reports/pattern_analysis_report.json
goto END

:GENERATE
echo [1/1] YAML 규칙 자동 생성...
python tools/rule_generator.py --generate-yaml --confidence 0.8
if errorlevel 1 goto ERROR
echo.
echo ✅ 규칙 생성 완료!
echo 결과: stage3_rules.yaml
goto END

:VALIDATE
echo [1/1] 규칙 검증 실행...
python tools/rule_validator.py --validate-all
if errorlevel 1 goto ERROR
echo.
echo ✅ 규칙 검증 완료!
echo 결과: reports/rule_validation_report_*.json
goto END

:ALL
echo [1/3] 로그 기반 패턴 분석 실행...
python tools/pattern_analyzer.py --analyze-logs
if errorlevel 1 goto ERROR

echo.
echo [2/3] YAML 규칙 자동 생성...
python tools/rule_generator.py --generate-yaml --confidence 0.8
if errorlevel 1 goto ERROR

echo.
echo [3/3] 규칙 검증 실행...
python tools/rule_validator.py --validate-all
if errorlevel 1 goto ERROR

echo.
echo ==========================================
echo ✅ Phase 1 전체 프로세스 완료!
echo ==========================================
echo.
echo 생성된 파일:
echo   📊 패턴 분석: reports/pattern_analysis_report.json
echo   🔧 YAML 규칙: stage3_rules.yaml  
echo   📋 검증 결과: reports/rule_validation_report_*.json
echo.
echo 다음 단계:
echo   1. stage3_rules.yaml 규칙을 실제 시스템에 적용
echo   2. Phase 2 (PC 앱 학습 기능) 구현 시작
echo.
goto END

:ERROR
echo.
echo ❌ 오류가 발생했습니다!
echo 자세한 내용은 위의 오류 메시지를 확인하세요.
echo.
goto END

:END
pause