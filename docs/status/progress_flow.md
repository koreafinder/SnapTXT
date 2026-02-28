# SnapTXT 진행 흐름 정리

## 1. 참고 문서 스냅샷
- [docs/plans/restructure_plan.md](../plans/restructure_plan.md): 전처리·후처리 모듈 분리, JSON 로깅, 회귀 테스트 확립까지의 8단계 리팩토링 로드맵이 모두 ✅ 상태.
- [docs/plans/future_improvement_plan.md](../plans/future_improvement_plan.md): Q2 이후 **후처리 품질 실험 자동화**, **PC 앱 UX 개선**, **배포/관측성 강화** 등을 P1~P3 우선순위로 정의.
- [PRACTICAL_GUIDE.md](../../PRACTICAL_GUIDE.md): Enhanced Korean Processor, Advanced Image Processor, Ultimate OCR System 등 6개 핵심 모듈 사용법과 GUI/웹 통합 예시 정리.
- [README.md](../../README.md): EasyOCR 기반 웹 앱 개요, Stage 3 회귀 테스트 실행 스크립트, JSON 로깅 옵션 안내.

## 2. 진행 흐름표

| 단계 | 시점 | 주요 내용 | 산출물 | 상태 |
| --- | --- | --- | --- | --- |
| 기초 정비 | 2026-02 | DLL 로딩 체계화, PyQt/CLI/Web가 공유하는 `snaptxt.backend.ocr_pipeline` 확립 | 공통 파이프라인, JSON 로깅, `.venv_new` 표준화 | ✅ 완료 |
| 리팩토링 & 후처리 집중 | 2026-02 | Stage 2/3 모듈 외부화, YAML 룰 핫리로드, `pytest -m stage3` 회귀 72건, EasyOCR 워커 모듈화 | [docs/plans/restructure_plan.md](../plans/restructure_plan.md) 8단계 완료, `scripts/run_regression.ps1` | ✅ 완료 |
| 품질 확장 | 2026 Q2 | 후처리 교정 실험 자동화, 태그별 품질 게이트, PC 앱 로그 히스토리, YAML diff 시뮬레이터 | `scripts/run_quality_suite.ps1`, `tools/rule_diff.py`, 11개 샘플 코퍼스, 후처리 교정 PoC | ⚙️ 진행 중 (샘플 11건·태그 게이트 PASS, 교정 모듈 도입 준비) |
| 배포/관측성 | 2026 Q2~ | PyInstaller 패키지, JSON 로그 포워더, 웹 API 옵션 확장 | `dist/SnapTXT-Setup.exe`, Swagger 문서, Loki/Elastic 파이프 | 📅 계획 중 |

## 3. 후처리 집중 실행선

1. **회귀 방어선** (완료)
   - Stage 3 테스트 72건 자동화 및 `-Smoke` 스위트로 파이프라인/워커 경로 검증.
   - YAML 룰 파일을 `SNAPTXT_STAGE{2,3}_RULES_FILE` 환경 변수로 교체 가능.
2. **질 관리 고도화** (진행 중)
   - `scripts/run_quality_suite.ps1`가 Stage3 회귀 + 태그별 품질 게이트(`article=0.9`, `synthetic=0.95`, `stress=0.85`, `table=0.9`, `lowlight=0.8`)를 한 번에 검증하고 `quality_suite_report.json`을 아티팩트로 업로드.
   - 다음 단계: `py-hanspell`/`pykospacing`, Stage3 교정 룰, `ftfy` 정규화를 PoC해 품질 점수 향상을 수치화한다.
3. **UX/배포 연동** (대기)
   - PC 앱: 추출 히스토리 패널 + JSON 로그 뷰어.
   - 배포: PyInstaller + self-update, JSON 로그 중앙 수집 파이프.

## 4. 다음 액션 체크리스트
- [ ] Stage3 출력 뒤에 `py-hanspell` + `pykospacing`을 연결하고 `scripts/run_quality_suite.ps1 -SampleIncludeText`로 개선 폭을 계측.
- [ ] 빈번한 오타/띄어쓰기 패턴을 Stage3 YAML 룰 테이블에 반영하고 `tests/postprocess/test_stage3_*`로 회귀를 고정.
- [ ] `ftfy` + `unicodedata` 기반 특수문자 정규화 레이어를 추가한 뒤 태그별 품질 점수가 유지/향상되는지 확인.
- [ ] GitHub Actions `quality-suite.yml` 런타임을 관찰해 문서/교정기 도입 후에도 태그 게이트가 안정적으로 PASS 하는지 기록.

---
이 문서는 최신 리팩토링/후처리 문서를 한눈에 정리하고, 현재 진행 중인 품질 강화 흐름을 추적하기 위한 대시보드 역할을 합니다. 필요한 경우 스프린트 회의에서 이 표를 기반으로 담당자/일정을 업데이트하세요.
