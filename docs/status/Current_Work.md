# Current Work Snapshot

_최종 업데이트: 2026-03-01_

## 현재 상태 요약
- ✅ EasyOCR 워커를 `python -m snaptxt.backend.worker.easyocr_worker` 방식으로 실행하며 UTF-8을 강제해 cp949 디코딩 오류를 제거했다.
- ✅ GUI(`pc_app.py`)는 콘솔과 `snaptxt_debug.log`에 동시 기록하며, 이모지 제거 토글로 터미널 폰트를 보호한다.
- ✅ `docs/status/progress_flow.md`가 리팩토링 히스토리와 Q2 이니셔티브를 정리했다.
- ✅ `experiments/samples/quality_samples.json`을 11건(기사/테이블/로우라이트 포함)으로 확장하고 길이·키워드 기반 신뢰도 산식을 `run_quality_samples.py`에 도입했다.
- ⚙️ 진행 중: 새로운 워커 경로가 PyQt UI 전체 흐름에서 항상 동작하는지 재검증(텍스트는 표시되지만 콘솔 폰트 토글은 선택 사항).

### 2026-03-01 추가 확인
- ✅ PC 앱에서 `IMG_4790.JPG`를 재실행해 PyTorch DLL 사전 로드→EasyOCR 프로세스 분리→706자 본문 추출까지 전 구간 로그를 확인했다(경고는 `runpy`/`pin_memory` 수준이며 기능 영향 없음).
- ✅ GPT 5.2 결과와 비교해 현재 Stage3 출력의 띄어쓰기·맞춤법·특수문자 차이를 목록화했고, 후처리 개선안(맞춤법 교정기, 교정 룰 테이블, 기호 정규화)을 확정했다.
- ✅ 문서 체계 점검 파이프라인을 `python tools/check_docs.py --ci --no-open --show-optional` → `scripts/check_docs_ci.ps1 -IncludeOptional` → `check_docs.bat ci` 순으로 재검증하고, `.github/workflows/docs-check.yml`이 한국시간 09:00 정기 실행 및 PR 트리거를 유지하는지 확인했다.

## 진행 중 작업
1. **py-hanspell + pykospacing 통합 검증**
   - Stage3 출력 문자열을 두 패키지에 통과시켜 띄어쓰기·맞춤법 오류의 60~70%를 자동으로 제거하는 흐름을 PoC 한다.
   - `quality_samples.json` 11건 전부를 대상으로 개선 전/후 길이 대비 오류율을 기록해 태그별 영향도를 문서화한다.
2. **Stage3 교정 룰 테이블 확장**
   - `docs/plans/restructure_plan.md`에서 도출한 오타(예: `드러워습니다`, `돌두`, `untetheredsoul com`)를 YAML 사전으로 정리하고 `tests/postprocess/test_stage3_*`에 케이스를 추가한다.
   - `tools/rule_diff.py` 리포트에 새 교정 룰이 표기되는지 확인한다.
3. **문장부호/특수문자 정규화 레이어**
   - `ftfy` + `unicodedata` 조합으로 괄호/따옴표/기호를 복원하고, `www.untetheredsoul.com` 같은 URL 포맷을 고정한다.
   - Stage3 이후 모듈로 삽입해도 성능/지연에 영향이 없는지 `run_quality_suite.ps1`로 검증한다.

## 리스크 / 이슈
- **터미널 인코딩 편차**: 사용자가 UTF-8 모드를 끌 수 있으므로, 워커 stderr가 환경 변수로 항상 UTF-8을 유지하는지 점검해야 한다.
- **문서 분산**: README, PRACTICAL_GUIDE, progress_flow 등 문서가 많아 변경 시 상호 검증이 필요하다.
- **패키징 과제**: PyInstaller 작업이 남아 있으며 DLL/Qt 경로를 정확히 포함해야 한다.
- **후처리 모듈 의존성**: `py-hanspell`, `pykospacing`, `ftfy` 도입 시 배포 이미지/오프라인 환경에서 추가 사전이 필요한지 확인해야 한다.

## 다음 단계
- [ ] `py-hanspell` + `pykospacing` 후처리 체인을 Stage3 뒤에 붙여 샘플 11건 기준 품질 점수를 다시 산출한다.
- [ ] 빈번한 오타/띄어쓰기 패턴을 Stage3 YAML 룰 테이블로 추가하고 해당 케이스를 Stage3 pytest로 고정한다.
- [ ] `ftfy` + `unicodedata` 기반 특수문자 정규화 레이어를 추가하고 `run_quality_suite.ps1 -SampleIncludeText`로 검증한다.
