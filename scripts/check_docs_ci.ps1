#!/usr/bin/env pwsh
<#
.SYNOPSIS
    SnapTXT 문서 상태를 CI에서 검증하는 스크립트
.DESCRIPTION
    필수 문서와 선택 문서 존재 여부를 확인하고, 문제가 있으면 오류로 종료합니다.
    GitHub Actions나 기타 CI 파이프라인에서 사용할 수 있습니다.
.PARAMETER IncludeOptional
    선택 문서(plans, reference)도 함께 검사합니다.
.PARAMETER Quiet
    자세한 출력을 생략하고 결과만 표시합니다.
.EXAMPLE
    .\scripts\check_docs_ci.ps1
    .\scripts\check_docs_ci.ps1 -IncludeOptional
    .\scripts\check_docs_ci.ps1 -IncludeOptional -Quiet
#>

param(
    [switch]$IncludeOptional,
    [switch]$Quiet
)

# 스크립트 디렉터리 기준으로 프로젝트 루트 찾기
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# 작업 디렉터리 설정
Set-Location $ProjectRoot

# .venv_new 활성화 (존재하는 경우)
$VenvPath = ".\.venv_new\Scripts\Activate.ps1"
if (Test-Path $VenvPath) {
    if (-not $Quiet) {
        Write-Host "🔧 Python 가상환경 활성화: $VenvPath" -ForegroundColor Cyan
    }
    & $VenvPath
} else {
    Write-Warning "가상환경을 찾을 수 없습니다: $VenvPath"
}

# Python 실행 경로 설정
$PythonExe = if (Test-Path ".\.venv_new\Scripts\python.exe") {
    ".\.venv_new\Scripts\python.exe"
} else {
    "python"
}

# check_docs.py 실행 인자 구성
$CheckArgs = @("tools\check_docs.py", "--ci", "--no-open")
if ($IncludeOptional) {
    $CheckArgs += "--show-optional"
}

if (-not $Quiet) {
    Write-Host "📋 문서 상태 검증 시작..." -ForegroundColor Green
    Write-Host "명령어: $PythonExe $($CheckArgs -join ' ')" -ForegroundColor DarkGray
    Write-Host "프로젝트 루트: $(Get-Location)" -ForegroundColor DarkGray
    Write-Host ""
}

# check_docs.py 실행
try {
    & $PythonExe @CheckArgs
    $ExitCode = $LASTEXITCODE
    
    if ($ExitCode -eq 0) {
        Write-Host "`n✅ 문서 검증 성공!" -ForegroundColor Green
        if ($IncludeOptional) {
            Write-Host "   (필수 + 선택 문서 모두 확인됨)" -ForegroundColor DarkGreen
        } else {
            Write-Host "   (필수 문서 확인됨, 선택 문서는 -IncludeOptional로 추가 검사)" -ForegroundColor DarkGreen
        }
    } else {
        Write-Host "`n❌ 문서 검증 실패!" -ForegroundColor Red
        Write-Host "   누락된 문서가 있습니다. 위 출력을 확인하세요." -ForegroundColor DarkRed
    }
    
    exit $ExitCode
} catch {
    Write-Host "`n💥 실행 오류: $($_.Exception.Message)" -ForegroundColor Red
    exit 2
}