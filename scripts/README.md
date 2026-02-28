# Scripts 폴더

이 디렉터리는 SnapTXT 개발 및 CI/CD 파이프라인에서 사용하는 자동화 스크립트를 포함합니다.

## 📋 문서 검증 스크립트

### `check_docs_ci.ps1`
CI/CD 파이프라인에서 문서 상태를 자동 검증하는 PowerShell 스크립트입니다.

**사용법:**
```powershell
# 필수 문서만 검사
.\scripts\check_docs_ci.ps1

# 선택 문서도 포함하여 검사
.\scripts\check_docs_ci.ps1 -IncludeOptional

# 간단한 출력으로 검사
.\scripts\check_docs_ci.ps1 -IncludeOptional -Quiet
```

**기능:**
- 필수 문서 존재 확인 (`docs/foundation/`, `docs/status/`, `docs/README.md`)
- 선택 문서 존재 확인 (`docs/plans/`, `docs/reference/`)
- 가상환경 자동 활성화
- CI 친화적 종료 코드 (0: 성공, 1: 문서 누락, 2: 실행 오류)

## 🧪 기존 스크립트

### `run_regression.ps1`
Stage 3 후처리 회귀 테스트를 실행합니다.

**사용법:**
```powershell
# 전체 회귀 테스트 (72건)
.\scripts\run_regression.ps1

# 스모크 테스트만 (빠른 확인)
.\scripts\run_regression.ps1 -Smoke
```

### `run_quality_suite.ps1`
Stage 3 회귀, 품질 지표 산출, 룰 비교 리포트를 한 번에 실행합니다.

**사용법:**
```powershell
# 기본 실행 (회귀 + 품질 보고서)
.\scripts\run_quality_suite.ps1

# 최소 품질 점수 게이트 + 룰 비교 포함
.\scripts\run_quality_suite.ps1 -MinQuality 0.85 -Stage2Compare "backups/stage2_rules.yaml" -Stage3Compare "backups/stage3_rules.yaml"

# 품질 계산만 수행 (기존 결과로 대체)
.\scripts\run_quality_suite.ps1 -SkipRegression -SkipRuleDiff -SkipSampleRun

# 샘플 결과에 원문 텍스트도 포함하여 저장
.\scripts\run_quality_suite.ps1 -SampleIncludeText

# 태그별 품질 게이트 적용 (예: article≥0.9, stress≥0.85)
.\scripts\run_quality_suite.ps1 -TagThreshold article=0.9 -TagThreshold stress=0.85
```

**생성 산출물:**
- `reports/quality_suite_report.json`: 샘플 기반 품질 지표
- `reports/rule_diff_report.json`: Stage 2/3 YAML 비교 결과 (비교 경로 제공 시)
- `experiments/results/quality_samples.json`: `experiments/samples/quality_samples.json` 목록을 기반으로 새로 수집한 원본 샘플 결과

**옵션 요약:**
- `-SkipSampleRun`: 이미 생성된 `experiments/results/quality_samples.json`을 재사용할 때 설정합니다.
- `-SampleSpec`, `-SampleResults`: 샘플 정의/출력 경로를 맞춤화합니다.
- `-Samples`: 품질 집계 입력 파일을 직접 지정하고 싶을 때 사용합니다 (기본값은 `-SampleResults`).
- `-SampleIncludeText`: 샘플 실행 시 OCR 텍스트를 결과 JSON에 저장해 디버깅에 활용합니다.
- `-TagThreshold`: 특정 태그(예: `article`, `synthetic`)에 대해 `tag=value` 형식으로 최소 품질을 지정하면 `tools/quality_suite.py`가 태그별 게이트를 검증합니다.

샘플 정의 파일(`experiments/samples/quality_samples.json`)은 `expected_length`, `keywords`, `min_confidence`, `tags` 필드로 각 케이스의 난이도와 기대치를 기술하며, `run_quality_samples.py`가 이를 이용해 `confidence` 점수를 계산합니다. `tools/quality_suite.py`는 태그별 요약(`tag_summaries`)과 게이트(`tag_quality_gates`)를 생성합니다.

## 🔗 관련 자동화

- **GitHub Actions**: `.github/workflows/docs-check.yml`에서 매일 문서 상태를 자동 검증
- **로컬 배치 파일**: 루트의 `check_docs.bat`으로 빠른 수동 검사
- **문서 규칙**: `docs/README.md`에서 문서 작성/관리 가이드 확인

---

스크립트 추가나 수정 시, 이 README도 함께 업데이트하세요.