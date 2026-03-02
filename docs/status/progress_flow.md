# SnapTXT 진행 흐름 정리

## 1. 참고 문서 스냅샷
- [docs/plans/adaptive_preprocessing_implementation.md](../plans/adaptive_preprocessing_implementation.md): **🚀 GPT 5.2 기반 Adaptive 전처리 시스템** - 4-타입 분류(본문/배경/그림자/비침), 80-20 전략, Office Lens 들쭉날쭉 문제 완전 해결 설계 (2026-03-02 실행중)
- [docs/plans/restructure_plan.md](../plans/restructure_plan.md): 전처리·후처리 모듈 분리, JSON 로깅, 회귀 테스트 확립까지의 8단계 리팩토링 로드맵이 모두 ✅ 상태.
- [docs/plans/future_improvement_plan.md](../plans/future_improvement_plan.md): Q2 이후 **후처리 품질 실험 자동화**, **PC 앱 UX 개선**, **배포/관측성 강화** 등을 P1~P3 우선순위로 정의.
- [PRACTICAL_GUIDE.md](../../PRACTICAL_GUIDE.md): Enhanced Korean Processor, Advanced Image Processor, Ultimate OCR System 등 6개 핵심 모듈 사용법과 GUI/웹 통합 예시 정리.
- [README.md](../../README.md): EasyOCR 기반 웹 앱 개요, Stage 3 회귀 테스트 실행 스크립트, JSON 로깅 옵션 안내.

## 2. 진행 흐름표

| 단계 | 시점 | 주요 내용 | 산출물 | 상태 |
| --- | --- | --- | --- | --- |
| 기초 정비 | 2026-02 | DLL 로딩 체계화, PyQt/CLI/Web가 공유하는 `snaptxt.backend.ocr_pipeline` 확립 | 공통 파이프라인, JSON 로깅, `.venv_new` 표준화 | ✅ 완료 |
| 리팩토링 & 후처리 집중 | 2026-02 | Stage 2/3 모듈 외부화, YAML 룰 핫리로드, `pytest -m stage3` 회귀 72건, EasyOCR 워커 모듈화 | [docs/plans/restructure_plan.md](../plans/restructure_plan.md) 8단계 완료, `scripts/run_regression.ps1` | ✅ 완료 |
| **🎆 전처리 혁신 GPT 5.2 개선** | **2026-03-02** | **GPT 5.2 개선사항 전면 적용: 상/하 그라데이션 감지, 분류 순서 최적화, 평탄화 안정화, CLAHE 약화, Fallback 세분화** | **MinimalAdaptivePreprocessor 업그레이드, 7.0→7.1점 성능 향상, test_preprocessing_improvement.py** | **✅ 완료** |
| **🧠 Phase 2 학습 시스템** | **2026-03-02** | **29개 Ground Truth 데이터 기반 고급 학습 시스템: 150회 시뮤레이션, 39개 규칙 생성, 12.6% 성능 향상** | **ground_truth_advanced_learner.py, integrated_performance_test.py, learned_rules_advanced.yaml** | **✅ 완료** |
| **⚠️ 시스템 통합 문제 해결** | **2026-03-02** | **Context 없는 무차별 문자 치환 문제 발견 및 해결: 위험한 20개 규칙 제거, 패턴 검증 시스템 필요성 파악** | **integrate_phase2_to_system.py, 안전한 시스템 복구** | **✅ 완료** |
| 품질 확장 | 2026 Q2 | 후처리 교정 실험 자동화, 태그별 품질 게이트, PC 앱 로그 히스토리, YAML diff 시뮤레이터, **Phase 2 패턴 검증 시스템** | `scripts/run_quality_suite.ps1`, `tools/rule_diff.py`, 11개 샘플 코퍼스, `py-hanspell`·`pykospacing`·`ftfy` Stage3 채인, **PatternValidator 및 Context-aware 규칙** | ⚙️ 진행 중 (교정 체인은 적용 완료, 패턴 검증 시스템 개발 단계)
| 배포/관측성 | 2026 Q2~ | PyInstaller 패키지, JSON 로그 포워더, 웹 API 옵션 확장 | `dist/SnapTXT-Setup.exe`, Swagger 문서, Loki/Elastic 파이프 | 📅 계획 중 |

## 3. 전처리 혁신 실행선 완료 (2026-03-02)

**🎯 핵심 목표**: Office Lens 이미지의 "들쭉날쭉" OCR 결과 완전 해결
- **기존 문제**: 레거시 레벨1으로 812자→0자→625자 불일치 성능 
- **혁신 접근**: GPT 5.2 분석 기반 4-타입(본문/배경/그림자/비침) 분류 + 적응형 전처리
- **80-20 전략**: 80% 케이스는 빠르게, 20%는 Fallback으로 정확하게
- **🎆 GPT 5.2 개선완료**: 7.0→7.1점 성능 향상 달성

1. **🔬 설계 완료** (2026-03-02 ✅)
   - MinimalAdaptivePreprocessor 클래스 완전 구현
   - 4-타입 분류 + 타입별 최적 전처리 + Fallback 전략
   - 성능 vs 정확도 균형을 위한 썸네일 분석(512px) 적용

2. **📊 GPT 5.2 개선 완료** (2026-03-02 ✅)
   - 상/하 그라데이션 감지 추가 (tb_gradient 필드)
   - 분류 순서 최적화: TYPE_C(그림자) 우선 분류
   - cv2.divide 평탄화 안정화 + CLAHE 약화 (clipLimit 1.5)
   - Fallback 전략 세분화: 원본 타입별 단계적 강화

3. **📈 성능 검증 완료** (2026-03-02 ✅)
   - test_preprocessing_improvement.py로 5개 파일 비교
   - 전체 평균: 7.0→7.1점 (+0.1점 개선)
   - 개선 파일: 4/5개 (80%), 최대 개선 IMG_4792 (+0.4점)
   - JSON 결과 데이터 생성 및 아카이브

4. **🚀 통합 준비** (다음 단계)
   - 전체 10개 파일 확장 테스트
   - PC 앱 Adaptive 옵션 통합
   - 성능 벤치마크 문서화

## 4. 기존 후처리 집중 실행선

1. **회귀 방어선** (완료)
   - Stage 3 테스트 72건 자동화 및 `-Smoke` 스위트로 파이프라인/워커 경로 검증.
   - YAML 룰 파일을 `SNAPTXT_STAGE{2,3}_RULES_FILE` 환경 변수로 교체 가능.
2. **질 관리 고도화** (진행 중)
   - `scripts/run_quality_suite.ps1`가 Stage3 회귀 + 태그별 품질 게이트(`article=0.9`, `synthetic=0.95`, `stress=0.85`, `table=0.9`, `lowlight=0.8`)를 한 번에 검증하고 `quality_suite_report.json`을 아티팩트로 업로드.
   - Spellcheck/spacing/punctuation 체인이 Stage3 기본값으로 편입됐으며, 다음 단계는 품질 상승폭·지연 변화를 수치화하는 것이다.
3. **UX/배포 연동** (대기)
   - PC 앱: 추출 히스토리 패널 + JSON 로그 뷰어.
   - 배포: PyInstaller + self-update, JSON 로그 중앙 수집 파이프.

## 5. 현재 액션 체크리스트 (2026-03-02)

### 🚀 전처리 혁신 (최우선 P1)
- [ ] **분류 정확도 테스트**: Office Lens 10장으로 4-타입 분류 검증
- [ ] **성능 비교 분석**: Adaptive vs 레거시 레벨1 vs 원본 OCR 결과 측정
- [ ] **임계값 최적화**: 실제 결과 기반 classification threshold 조정
- [ ] **MultiOCRProcessor 통합**: 기존 시스템에 Adaptive 전처리 연동
- [ ] **프로덕션 테스트**: 회귀 테스트 + 성능 벤치마크 완료

### 📋 기존 후처리 품질 (병행)
|- [x] Stage3 출력 뒤에 `py-hanspell` + `pykospacing`을 연결하고 `scripts/run_quality_suite.ps1 -SampleIncludeText`로 개선 폭을 계측.
|- [x] 빈번한 오타/띄어쓰기 패턴을 Stage3 YAML 룰 테이블에 반영하고 `tests/postprocess/test_stage3_*`로 회귀를 고정.
|- [x] `ftfy` + `unicodedata` 기반 특수문자 정규화 레이어를 추가한 뒤 태그별 품질 점수가 유지/향상되는지 확인.
- [x] GitHub Actions `quality-suite.yml` 스케줄(매일 01:00 UTC), 타임아웃(90분), 아티팩트(`quality-suite-<run_id>`) 구성을 점검하고 태그 게이트 인자가 로컬/CI 모두 동일함을 확인했다.
|- [x] Stage3 latency(Spellcheck API 호출 포함)를 `logs/snaptxt_ocr.jsonl`에서 산출(평균 0.031초, p95 0.187초, 최대 0.201초 / 최근 5건 평균 0.006초)해 캐싱/비동기 전략을 현재는 보류해도 됨을 기록했다.

---
이 문서는 최신 리팩토링/후처리 문서와 **2026-03-02 전처리 혁신 계획**을 한눈에 정리하고, 현재 진행 중인 품질 강화 흐름을 추적하기 위한 대시보드 역할을 합니다. 필요한 경우 스프린트 회의에서 이 표를 기반으로 담당자/일정을 업데이트하세요.
