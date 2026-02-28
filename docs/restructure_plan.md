# SnapTXT 코드베이스 재구성 계획

> **최종 수정**: 2026-02-28
> **작성자**: SnapTXT 팀 (담당: Copilot)
> **관련 브랜치**: `refactor/layout` (생성 예정)

## 1. 목표
- 전처리/후처리 레이어를 독립 모듈로 분리하여 재사용성과 실험 효율을 높인다.
- PC(PyQt)·웹(Flask)·CLI 모든 진입점에서 동일한 OCR 파이프라인을 공유하도록 API를 통일한다.
- 실험/백업 파일과 배포 대상 코드를 명확히 분리해 릴리스 품질을 개선한다.
- 패턴/룰 사전을 외부화하여 패치 없이 후처리 규칙을 조정할 수 있게 한다.
- 자동화된 회귀 테스트(특히 Stage 3)와 JSON 기반 로깅으로 안정성 지표를 확보한다.

## 2. 현재 문제 요약
| 영역 | 증상 |
| --- | --- |
| 구조 | `easyocr_worker.py` (1000+ 라인)와 `multi_ocr_processor.py` (450+ 라인)에 핵심 로직이 집중돼 있어 모듈 간 결합도가 높음 |
| 중복 | PC 앱은 `MultiOCRProcessor`, 웹 서버는 `OCRProcessor`를 사용해 기능이 이중화됨 |
| 실험물 | stage 백업/실험 스크립트가 루트에 흩어져 배포 대상과 혼재 |
| 규칙 관리 | Stage 2/3 패턴이 코드에 하드코딩되어 버전 추적·롤백이 어려움 |
| 테스트 | `test_stage3_X.py`가 개별 스크립트로 존재해 일괄 회귀 검증이 번거로움 |

## 3. 목표 디렉터리 구조(안)
```
snaptxt/
  __init__.py
  ui/
    __init__.py
    desktop_app.py        # 기존 pc_app 로직 일부 이동
    cli.py
  backend/
    __init__.py
    ocr_pipeline.py       # 공통 서비스 (전처리 → 엔진 → 후처리)
    multi_engine.py       # MultiOCRProcessor 이전 위치
    worker/
      __init__.py
      easyocr_worker.py   # 후처리는 postprocess 모듈 호출
    logging.py            # JSON 로깅 헬퍼
  preprocess/
    __init__.py
    image_filters.py      # CLAHE/언샤프/적응 임계값 등
  postprocess/
    __init__.py
    stage2.py
    stage3.py
    formatting.py
    patterns/
      stage2_rules.yaml
      stage3_rules.yaml
experiments/
  README.md
  ... (백업/실험 스크립트 이동)
docs/
  restructure_plan.md
  ...
```

## 4. 단계별 일정
| 단계 | 설명 | 산출물 |
| --- | --- | --- |
| 0 | Git 브랜치 생성, 현재 상태 커밋 확인 | `refactor/layout` 브랜치 |
| 1 | 패키지 스켈레톤/placeholder 작성 | 빈 `snaptxt/` 구조, `__init__.py` |
| 2 | `ocr_pipeline.py` 초안으로 PC/웹 공통 인터페이스 정의 | 서비스 클래스, 단위 테스트 뼈대 |
| 3 | 전처리 함수 `image_filters.py`로 추출, `multi_engine.py`에서 import | 새 모듈 + 기존 호출부 수정 |
| 4 | 후처리 Stage 2/3 모듈화 + 패턴 YAML 로더 작성 | `postprocess/` 하위 모듈, 로딩 코드 |
| 5 | EasyOCR 워커/멀티엔진을 `snaptxt/backend`로 이전, import 경로 수정 | 새 파일 구조 반영 |
| 6 | 실험/백업 스크립트를 `experiments/`로 이동, README 정리 | 정리된 루트 디렉터리 |
| 7 | pytest 기반 회귀 테스트/fixtures 작성, 실행 스크립트 추가 | `tests/` + `scripts/run_regression.sh` |
| 8 | JSON 로깅 헬퍼 연결, README & 실행 스크립트 업데이트 | 갱신된 문서/로그 포맷 |

## 5. 리스크 및 대응
- **대규모 파일 이동으로 인한 충돌**: 브랜치를 분리하고 logical chunk 단위로 커밋한다.
- **후처리 규칙 회귀**: Stage 3 pytest 스위트를 먼저 확보해 이동마다 실행한다.
- **경로 변경에 따른 실행 스크립트 고장**: `start_app.bat`, `run_pc_app.py`, `.venv` 활성화 스크립트를 마지막 단계에서 일괄 업데이트하고 smoke test를 수행한다.

## 6. 커밋 가이드
1. `refactor: scaffold snaptxt package`
2. `feat: add shared ocr pipeline service`
3. `chore: move preprocess filters`
4. `feat: modularize postprocess stages`
5. `chore: relocate worker/backend`
6. `chore: move experiments`
7. `test: add stage regression suite`
8. `feat: json logging + docs`

각 단계 종료 시 GitHub에 push하여 필요 시 즉시 롤백할 수 있게 한다.

## 7. 진행 현황
| 항목 | 상태 | 비고 |
| --- | --- | --- |
| 계획 문서 정리 | ✅ | `docs/restructure_plan.md` 작성 완료 |
| 리팩토링 브랜치 생성 | ✅ | `refactor/layout` 생성 및 push 예정 |
| 패키지 스켈레톤 작성 | ✅ | `snaptxt/` 기본 구조 커밋 완료 |
| 공통 OCR 파이프라인 초안 | ✅ | `snaptxt/backend/ocr_pipeline.py` 구현 완료 |
| 전처리 모듈 이관 | ✅ | `snaptxt/preprocess/image_filters.py`로 이전 |
| 후처리 모듈 분리 | ✅ | Stage 2/3 모듈 EasyOCR 워커·공통 OCR 파이프라인 연동, Stage 2 룰 YAML 외부화, Stage 2/3 pytest 회귀 확보 |
| 후처리 룰 핫스왑·스모크 러너 | ✅ | Stage 2 YAML 핫리로드, `tests/smoke/test_postprocess_entrypoints.py`로 파이프라인·EasyOCR 워커 경로 검증 |
| Stage 3 룰 YAML 외부화/핫리로드 | ✅ | `snaptxt/postprocess/patterns/stage3_rules.yaml`, `reload_stage3_rules()`로 런타임 교체 지원 |
| Stage 3 룰 핫리로드 회귀 테스트 | ✅ | `tests/postprocess/test_stage3_reload.py`에서 임시 YAML·캐시 복원 플로우 검증 |

## 8. 후처리 룰 관리 현황

| Stage | 룰 파일 | 환경 변수 Override | 핫리로드 API | 회귀 테스트 |
| --- | --- | --- | --- | --- |
| Stage 2 | `snaptxt/postprocess/patterns/stage2_rules.yaml` | `SNAPTXT_STAGE2_RULES_FILE` | `reload_stage2_rules()` (`snaptxt.postprocess`) | `tests/postprocess/test_stage2_reload.py` |
| Stage 3 | `snaptxt/postprocess/patterns/stage3_rules.yaml` | `SNAPTXT_STAGE3_RULES_FILE` | `reload_stage3_rules()` (`snaptxt.postprocess`) | `tests/postprocess/test_stage3_reload.py`, `tests/postprocess/test_stage3_*` |
