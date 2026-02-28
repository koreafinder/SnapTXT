param(
    [switch]$Smoke
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) {
    $scriptDir = Get-Location
}
$repoRoot = Split-Path $scriptDir -Parent
if (-not $repoRoot) {
    $repoRoot = $scriptDir
}

Push-Location $repoRoot
try {
    $venvActivate = Join-Path $repoRoot ".venv_new\Scripts\Activate.ps1"
    if (Test-Path $venvActivate) {
        Write-Host "가상환경 활성화 (.venv_new)" -ForegroundColor DarkGray
        . $venvActivate
    }
    else {
        Write-Warning "'.venv_new' 가상환경을 찾을 수 없습니다. 시스템 Python을 사용합니다."
    }

    if ($env:PYTHONPATH) {
        $env:PYTHONPATH = "$repoRoot;" + $env:PYTHONPATH
    }
    else {
        $env:PYTHONPATH = $repoRoot
    }

    Write-Host "작업 경로: $repoRoot" -ForegroundColor DarkGray
    Write-Host "Stage 3 회귀 테스트 실행 중..." -ForegroundColor Cyan
    python -m pytest -m stage3 --maxfail 1

    if ($Smoke) {
        Write-Host "Smoke 테스트 실행 중..." -ForegroundColor Cyan
        python -m pytest -m smoke --maxfail 1
    }
}
finally {
    Pop-Location
}
