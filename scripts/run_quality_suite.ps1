param(
    [switch]$SkipRegression,
    [switch]$SkipQuality,
    [switch]$SkipRuleDiff,
    [switch]$SkipSampleRun,
    [switch]$SampleIncludeText,
    [string]$SampleSpec = "experiments/samples/quality_samples.json",
    [string]$SampleResults = "experiments/results/quality_samples.json",
    [string]$Samples,
    [string]$OutputDir = "reports",
    [double]$MinQuality = 0,
    [string[]]$TagThreshold,
    [string]$Stage2Base = "snaptxt/postprocess/patterns/stage2_rules.yaml",
    [string]$Stage2Compare,
    [string]$Stage3Base = "snaptxt/postprocess/patterns/stage3_rules.yaml",
    [string]$Stage3Compare,
    [string]$QualityReportName = "quality_suite_report.json",
    [string]$RuleDiffReportName = "rule_diff_report.json"
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
    $venvActivate = Join-Path $repoRoot ".venv_new/Scripts/Activate.ps1"
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

    $outputDirFull = Join-Path $repoRoot $OutputDir
    if (-not (Test-Path $outputDirFull)) {
        New-Item -ItemType Directory -Path $outputDirFull | Out-Null
    }

    if (-not $SkipSampleRun) {
        Write-Host "품질 샘플 실행 중..." -ForegroundColor Cyan
        $sampleArgs = @(
            "--spec", (Join-Path $repoRoot $SampleSpec),
            "--output", (Join-Path $repoRoot $SampleResults),
            "--quiet"
        )
        if ($SampleIncludeText) {
            $sampleArgs += "--include-text"
        }
        python experiments/scripts/run_quality_samples.py @sampleArgs
    }
    else {
        Write-Host "품질 샘플 실행을 건너뜁니다." -ForegroundColor DarkGray
    }

    if (-not $Samples -or $Samples.Trim().Length -eq 0) {
        $Samples = $SampleResults
    }

    if (-not $SkipRegression) {
        Write-Host "Stage 3 회귀 테스트 실행 중..." -ForegroundColor Cyan
        python -m pytest -m stage3 --maxfail 1
    }
    else {
        Write-Host "Stage 3 회귀 테스트를 건너뜁니다." -ForegroundColor DarkGray
    }

    if (-not $SkipQuality) {
        $qualityReportPath = Join-Path $outputDirFull $QualityReportName
        $qualityArgs = @("--samples", (Join-Path $repoRoot $Samples), "--output", $qualityReportPath)
        if ($MinQuality -gt 0) {
            $qualityArgs += @("--min-quality", $MinQuality)
        }
        if ($TagThreshold) {
            foreach ($threshold in $TagThreshold) {
                $qualityArgs += @("--tag-threshold", $threshold)
            }
        }
        Write-Host "품질 지표 산출 중..." -ForegroundColor Cyan
        python tools/quality_suite.py @qualityArgs
    }
    else {
        Write-Host "품질 지표 계산을 건너뜁니다." -ForegroundColor DarkGray
    }

    if (-not $SkipRuleDiff) {
        $ruleArgs = @("--output", (Join-Path $outputDirFull $RuleDiffReportName))
        $hasStage2 = $Stage2Compare -and $Stage2Compare.Trim().Length -gt 0
        $hasStage3 = $Stage3Compare -and $Stage3Compare.Trim().Length -gt 0

        if ($hasStage2) {
            $ruleArgs += @("--stage2-base", (Join-Path $repoRoot $Stage2Base))
            $ruleArgs += @("--stage2-compare", (Join-Path $repoRoot $Stage2Compare))
        }
        if ($hasStage3) {
            $ruleArgs += @("--stage3-base", (Join-Path $repoRoot $Stage3Base))
            $ruleArgs += @("--stage3-compare", (Join-Path $repoRoot $Stage3Compare))
        }

        if ($ruleArgs.Count -eq 2) {
            Write-Host "룰 비교를 건너뜁니다 (비교 경로가 제공되지 않음)." -ForegroundColor DarkGray
        }
        else {
            Write-Host "룰 변경 요약 생성 중..." -ForegroundColor Cyan
            python tools/rule_diff.py @ruleArgs
        }
    }
    else {
        Write-Host "룰 비교 단계를 건너뜁니다." -ForegroundColor DarkGray
    }

    Write-Host "품질 스위트 실행이 완료되었습니다." -ForegroundColor Green
}
finally {
    Pop-Location
}
