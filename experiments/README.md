# Experiments & Backups

이 디렉터리는 배포 대상에서 분리된 실험용 스크립트, 백업본, 중간 결과물을 정리하기 위한 공간입니다.

## 구조

- `backups/`: 대용량 EasyOCR 워커 스냅샷 등 과거 버전을 보관합니다.
- `results/`: 실험 로그, 분석 리포트, 중간 텍스트 결과물을 보관합니다.
- `samples/`: 품질 스위트가 참조하는 입력 정의(JSON 등)를 저장합니다.
- `scripts/research/`: 고급 전처리·후처리 프로토타입, 통합 가이드 등을 위한 스크립트가 있습니다.
- `scripts/debug/`: GUI/Subprocess 비교, Stage2/Stage3 진단 등 문제 재현 스크립트를 모아둡니다.
- `assets/debug_images/`: 전처리 단계별 스냅샷 등 참고 이미지를 저장합니다.

## 실행 방법

실험 스크립트는 패키지 형태로 관리되므로 프로젝트 루트에서 `python -m` 형태로 실행하는 것을 권장합니다.

```powershell
# 예시: Stage3 subprocess 비교 도구 실행
& ".\.venv_new\Scripts\python.exe" -m experiments.scripts.debug.exact_subprocess_debug

# 예시: 고급 전처리 프로토타입 실행
& ".\.venv_new\Scripts\python.exe" -m experiments.scripts.research.advanced_image_processor

# 예시: 품질 샘플 실행 결과 업데이트
& ".\.venv_new\Scripts\python.exe" experiments/scripts/run_quality_samples.py --spec experiments/samples/quality_samples.json --output experiments/results/quality_samples.json --include-text
```

`python path/to/script.py`로 실행할 수도 있지만, 패키지 경로를 자동으로 잡아주는 `-m` 방식을 기본으로 유지해 주세요.

### 품질 샘플 스펙

`experiments/samples/quality_samples.json`의 각 항목은 다음 필드를 사용합니다.

- `expected_length`: 정상 추출 시 기대하는 문자 수(품질 평가에 사용).
- `keywords`: OCR 텍스트에 반드시 포함되어야 할 ASCII 키워드 목록.
- `min_confidence`: 해당 샘플의 허용 최소 신뢰도. `run_quality_samples.py`가 `quality_gate`를 기록합니다.
- `tags`: 리포트에서 그룹화할 때 참고할 카테고리(예: `article`, `synthetic`, `table`, `lowlight`).

`run_quality_samples.py`는 위 데이터를 기반으로 `confidence`와 `quality_components`를 계산하여 `experiments/results/quality_samples.json`에 저장하고, `tools/quality_suite.py`는 이를 집계하여 `reports/quality_suite_report.json`을 생성합니다. 태그별 요약(`tag_summaries`)과 게이트(`tag_quality_gates`)는 CI에서 대표 샘플군(기사, 테이블, 로우라이트 등)을 개별적으로 감시합니다.

필요할 때만 참조하고, 제품 코드와 혼동되지 않도록 이 위치를 유지해 주세요.
