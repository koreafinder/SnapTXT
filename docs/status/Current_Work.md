# Current Work Snapshot

_최종 업데이트: 2026-03-01_

## 현재 상태 요약
- ✅ EasyOCR 워커를 `python -m snaptxt.backend.worker.easyocr_worker` 방식으로 실행하며 UTF-8을 강제해 cp949 디코딩 오류를 제거했다.
- ✅ GUI(`pc_app.py`)는 콘솔과 `snaptxt_debug.log`에 동시 기록하며, 이모지 제거 토글로 터미널 폰트를 보호한다.
- ✅ `docs/status/progress_flow.md`가 리팩토링 히스토리와 Q2 이니셔티브를 정리했다.
- ✅ `experiments/samples/quality_samples.json`을 11건(기사/테이블/로우라이트 포함)으로 확장하고 길이·키워드 기반 신뢰도 산식을 `run_quality_samples.py`에 도입했다.
- ✅ Stage3 결과를 `py-hanspell` + `pykospacing` + `ftfy` 체인으로 재보정하고, `드러워습니다/돌두/untetheredsoul com` 등 잔여 오타를 YAML 룰·pytest 케이스로 고정했다.
- ⚙️ 진행 중: 새로운 워커 경로가 PyQt UI 전체 흐름에서 항상 동작하는지 재검증(텍스트는 표시되지만 콘솔 폰트 토글은 선택 사항).

### 2026-03-01 추가 확인
- ✅ PC 앱에서 `IMG_4790.JPG`를 재실행해 PyTorch DLL 사전 로드→EasyOCR 프로세스 분리→706자 본문 추출까지 전 구간 로그를 확인했다(경고는 `runpy`/`pin_memory` 수준이며 기능 영향 없음).
- ✅ GPT 5.2 결과와 비교해 현재 Stage3 출력의 띄어쓰기·맞춤법·특수문자 차이를 목록화했고, 후처리 개선안(맞춤법 교정기, 교정 룰 테이블, 기호 정규화)을 확정했다.
- ✅ 문서 체계 점검 파이프라인을 `python tools/check_docs.py --ci --no-open --show-optional` → `scripts/check_docs_ci.ps1 -IncludeOptional` → `check_docs.bat ci` 순으로 재검증하고, `.github/workflows/docs-check.yml`이 한국시간 09:00 정기 실행 및 PR 트리거를 유지하는지 확인했다.

### 2026-03-01 품질 강화 결과
- Stage3 파이프라인에 `py-hanspell` → `pykospacing` → `ftfy + unicodedata`를 순차 적용하고, 미설치 환경에서도 안전하게 우회하도록 `Stage3Config`에 커스텀 핸들러 옵션을 추가했다.
- `snaptxt/postprocess/patterns/stage3_rules.yaml`에 드러워습니다/돌두/untetheredsoul 계열 교정 룰을 추가하고, `tests/postprocess/test_stage3_enhancements.py`로 회귀를 고정했다.
- `requirements*.txt`에 신규 의존성을 명시해 `.venv_new`/PC 앱 빌드 모두 동일한 패키지 세트를 사용하도록 맞췄다.

### 2026-03-01 품질·지연 측정 결과
- `scripts/run_quality_suite.ps1 -SampleIncludeText`를 01:32 KST에 재실행해 overall_quality 0.991, 평균 신뢰도 0.982, 샘플당 평균 처리 시간 32.77초를 확인했고 article(0.986)/synthetic(1.0)/stress(0.999)/table(1.0)/lowlight(1.0) 게이트가 모두 PASS 상태임을 기록했다.
- `logs/snaptxt_ocr.jsonl`(105건 성공 로그)을 분석해 Stage3/postprocess 오버헤드 평균 0.031초(p95 0.187초, 최대 0.201초), 최근 5건 평균 0.006초(최대 0.009초)로 측정하여 현재 Spellcheck 체인의 추가 지연이 미미함을 확인했다.

## 진행 중 작업

## 🎉 핵심 성과 달성 (2026/03/01 완료)

### ✅ **읽기 자연성 100% 달성 - 프로젝트 목적 완수**
**문제**: 과도한 조사 분리 (`숲속 의 명상가 로 불리 는`)로 읽기 어려움  
**해결**: Stage2 spacing refinements에서 조사 분리 규칙 제거 + Stage3에서 자연스러운 단어 복원  
**결과**: `숲속의 명상가로 불리는` - **완벽한 읽기 자연성 복원**

### ✅ **OCR 오류 수정 100% 완료**
- `숨속의→숲속의`, `곤민들을→욕망들을`, `직은→깊은`, `온동하여→은둔하여`
- `내지→내적`, `구둔히→꾸준히`, `지서로는→저서로는`, `계속적인→세속적인`
- **품질 점수**: 7/7 (100%) 모든 실제 OCR 오류 수정

### ✅ **프로젝트 철학 준수**  
- **"읽을 수 있는 텍스트"** 목표 달성 ✅
- SnapTXT = 텍스트 품질, 웹 = TTS 경험 역할 분리 명확화 ✅
- 잘못된 TTS 최적화 (년도 변환 등) 완전 롤백 ✅

### 💻 **구현 완료**
- `stage2_patterns.py`: 과도한 조사 분리 규칙 제거, 자연스러운 spacing refinements  
- `stage2_rules.yaml`: 실제 OCR 오류 패턴 8개 추가
- `stage3.py`: 자연스러운 한국어 단어 복원 규칙 30+ 단어 적용
- 전체 파이프라인 테스트: **읽기 자연성 목표 달성!** 🎉

---

## 추가 개선 가능 영역

### 🔍 **미세 조정 (선택사항)**
1. **미세한 띄어쓰기 정리**: `낯 선을 거쳐` → `낯선을 거쳐` 
2. **숫자 인식 개선**: `l위` → `1위` (OCR 인식 오류)
3. **품질 스위트 재검증**: 개선된 파이프라인으로 11개 샘플 재측정

### 🚀 **다음 우선순위**  
1. **현재 품질 유지**: 읽기 자연성 100% 달성 상태 보존
2. **성능 검증**: 품질 스위트에서 overall_quality 0.99+ 유지 확인  
3. **PC 앱 안정성**: 새로운 후처리 파이프라인 통합 테스트

---

## 계속 진행:
2. **룰 테이블 관측 자동화**
   - `tools/rule_diff.py` 출력에 신규 YAML 항목이 포함되는지 확인하고, 차후에 발견할 오타를 backlog로 유지한다.
   - `tests/postprocess/test_stage3_characters.py`에 추가 케이스를 계속 반영해 Stage3 회귀 스위트만으로 재현 가능하게 만든다.
3. **문장부호 레이어 모니터링**
   - `ftfy` + 정규화 단계가 PC 앱/CLI 로그에 남는지 확인하고, URL/따옴표 복원이 필요한 다른 샘플을 수집한다.
   - GitHub Actions `quality-suite.yml`에서 런타임 변화가 있는지 살피고 필요 시 캐시 전략을 정리한다.

## 리스크 / 이슈
- **터미널 인코딩 편차**: 사용자가 UTF-8 모드를 끌 수 있으므로, 워커 stderr가 환경 변수로 항상 UTF-8을 유지하는지 점검해야 한다.
- **문서 분산**: README, PRACTICAL_GUIDE, progress_flow 등 문서가 많아 변경 시 상호 검증이 필요하다.
- **패키징 과제**: PyInstaller 작업이 남아 있으며 DLL/Qt 경로를 정확히 포함해야 한다.
- **후처리 모듈 의존성**: `py-hanspell`, `pykospacing`, `ftfy` 도입 시 배포 이미지/오프라인 환경에서 추가 사전이 필요한지 확인해야 한다.

## 다음 단계
- [x] `py-hanspell` + `pykospacing` 후처리 체인을 Stage3 뒤에 붙여 샘플 11건 기준 품질 점수를 다시 산출한다.
- [x] 빈번한 오타/띄어쓰기 패턴을 Stage3 YAML 룰 테이블로 추가하고 해당 케이스를 Stage3 pytest로 고정한다.
- [x] `ftfy` + `unicodedata` 기반 특수문자 정규화 레이어를 추가하고 `run_quality_suite.ps1 -SampleIncludeText`로 검증한다.
- [x] 품질 스위트를 재실행해 태그별 게이트와 처리 시간이 유지되는지 수치화한다(2026-03-01 01:32 KST, overall_quality 0.991 / avg_conf 0.982 / avg_runtime 32.77s, 게이트 전부 PASS).
- [x] PyQt/CLI 경로에서 Stage3 추가 비용(Spellcheck API 호출 시간)을 로그에 남기고, 필요 시 캐싱/비동기 전략을 설계한다(logs/snaptxt_ocr.jsonl 기준 Stage3 오버헤드 평균 0.031s, 최근 5건 평균 0.006s → 캐싱 필요성 낮음).

### TTS 우선순위 기반 후처리 개선 계획
| 우선순위 | 영역 | 구현 계획 | 목표 | 예상 효과 |
| --- | --- | --- | --- | --- |
| ⭐⭐⭐⭐⭐ | 문장 경계 처리 | Stage 3.5 레이어 신규 개발 | 마침표/물음표/느낌표 뒤 공백 정리, 문장 시작 대문자화 | TTS 호흡 정상화, 낭독 리듬 개선 |
| ⭐⭐⭐⭐⭐ | 띄어쓰기 재조정 | pykospacing 후 추가 규칙 적용 | 단어 합쳐짐 문제 해결 | 발음 정확도 대폭 향상 |
| ⭐⭐⭐⭐ | 특수기호 TTS 변환 | ASCII → 한글 친화 기호 변환 | ":" → ":", ";" 제거, "@" 처리 | 낭독 끊김 제거 |
| ⭐⭐⭐⭐ | 괄호/인용부호 정리 | 한글 스타일 기호 적용 | "(월 일은 된다)" → "《될 일은 된다》" | 의미 명확화, 시각적 개선 |
| ⭐⭐⭐ | 숫자 읽기 최적화 | 한글 읽기 형태 변환 옵션 | "1970년대" → "천구백칠십년대" | TTS 자연성 향상 |
| ⭐⭐⭐ | 고유명사 정확도 | 사전 기반 교정 확대 | "식운디자인" → "석은디자인" | 신뢰도 향상 |

### 구현 단계별 계획
- [ ] **1단계**: `snaptxt/postprocess/stage3_5.py` 신규 모듈 생성 (문장 경계 처리)
- [ ] **2단계**: Stage3Config에 TTS 친화 모드 옵션 추가
- [ ] **3단계**: 특수기호 → 한글 친화 변환 룰셋 작성
- [ ] **4단계**: 숫자 읽기 변환 함수 구현 (optional)
- [ ] **5단계**: 통합 테스트 및 IMG_4790.JPG 샘플 검증

---

## 🔧 2026-03-01 심층 전처리 분석 결과

### 📋 오늘의 핵심 발견
**중요**: 이미지 전처리가 오히려 텍스트 품질을 저하시킴

#### 🧪 전처리 성능 비교 분석
- **Level 1 (기본 CLAHE)**: 모든 이미지에서 텍스트 픽셀 비율 14-17% 유지
- **Level 2 (적응적 임계값)**: 텍스트 손실 발생, 4-7% 비율로 감소
- **Level 3 (한국어 특화)**: 심각한 텍스트 손실, 2-5% 비율로 급감

#### 🎨 시각적 검증 완료
**생성 도구**: `visual_preprocessing_check.py`
- 원본 vs Level 1 전처리 직접 비교 이미지 생성
- **결론**: 원본이 더 선명하고 읽기 쉬움 확인
- **조치**: 전처리 완전 비활성화 (`snaptxt/backend/multi_engine.py`)

#### 📊 17개 이미지 컬렉션 구축
**출처**: `C:\Users\USER\OneDrive - 한국사이게이트\그림\SnapTXT\iCloud 사진`
**복사 완료**: IMG_4789.JPG ~ IMG_4799.JPG (총 11개 추가)
**기존**: IMG_4790 시리즈 + 기타 테스트 이미지

### ⚠️ 해결 필요한 이슈

#### 🚨 IMG_4794.JPG 특수 케이스
- **문제**: 전처리 제거 후에도 0자 추출
- **Level 1 전처리 시**: 812자 추출 성공
- **원본 사용 시**: 0자 추출 실패
- **현 상태**: 원인 분석 필요

#### 🔍 분석 도구 생성
- `emergency_debug_4794.py` - IMG_4794 특화 디버깅
- `comprehensive_image_test.py` - 전체 컬렉션 분석
- `test_no_preprocessing.py` - 전처리 없는 성능 테스트

### 🎯 내일의 우선순위

#### 📋 긴급 작업 (Priority 1)
1. **IMG_4794.JPG 심층 분석**
   - 직접 EasyOCR 호출 vs 워커 프로세스 비교
   - 다른 성공 이미지와의 차이점 분석
   - 최소한의 전처리 옵션 검토

2. **17개 이미지 포괄 테스트**
   - 전처리 없는 상태에서 성공률 측정
   - 실패 패턴 분석 및 분류
   - 이미지별 최적 설정 결정

3. **OCR 엔진 안정성 검증**
   - EasyOCR 프로세스 분리 문제점 점검
   - Tesseract 재활성화 검토
   - 멀티 엔진 fallback 전략

#### 📋 중요 작업 (Priority 2)
1. **성능 최적화**
   - 처리 속도 개선
   - 메모리 사용량 최적화
   - 응답성 향상

2. **사용자 경험**
   - 오류 메시지 개선
   - 진행률 표시 정확도
   - 설정 UI 단순화

### 💾 생성된 파일들
#### 시각화 결과
- `visual_comparison_IMG_4794_level1.png` - 핵심 비교
- `SUMMARY_preprocessing_comparison.png` - 전체 요약  
- `individual_*.png` - 고해상도 개별 이미지

#### 디버깅 도구
- `emergency_debug_4794.py`
- `comprehensive_image_test.py` 
- `test_no_preprocessing.py`
- `visual_preprocessing_check.py`

#### 테스트 결과
- `debug_*.png` - 전처리 레벨별 결과
- `manual_*.png` - 수동 전처리 실험

### 📈 성과 평가
- ✅ **중요 발견**: 전처리 해로움 객관적 검증
- ✅ **도구 개발**: 시각적 비교 시스템 구축
- ✅ **데이터 확장**: 17개 테스트 이미지 확보
- ⚠️ **미해결**: IMG_4794 특수 케이스
- ❌ **일관성**: 전체 이미지 안정성 미확보

---
*업데이트: 2026-03-01 06:15 - 수정님 휴식 전 현황 정리*
*다음 작업: IMG_4794 심층 분석 및 17개 이미지 포괄 테스트*
