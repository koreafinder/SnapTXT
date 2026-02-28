# SnapTXT 향후 개선 계획 (2026 Q2)

## 1. 현재 상태 요약
- `docs/plans/restructure_plan.md` 8단계 전부 ✅: 백엔드 모듈화, Stage 2/3 외부화, 회귀 러너 및 JSON 로깅 완료.
- Stage 3 회귀 72건 + 스모크 2건 모두 통과 (`scripts/run_regression.ps1 -Smoke`).
- `enhanced_korean_processor.py` 샘플 실행 결과 품질점수 **0.94** (기존 대비 띄어쓰기·고유명사 교정 개선 확인).
- PC 앱/웹/CLI가 동일한 `snaptxt.backend.ocr_pipeline` 경로를 공유, 실험 스크립트는 `experiments/` 폴더에 정리됨.

## 2. 실제 개선 체감 지표
| 지표 | Before | After | 근거 |
| --- | --- | --- | --- |
| Stage 3 회귀 커버리지 | 단일 스크립트 수동 실행 | `pytest -m stage3` 72건 자동화 | `scripts/run_regression.ps1 -Smoke` 로그 |
| 후처리 규칙 배포 | 코드 수정 필요 | YAML 핫리로드 + JSON 로그 추적 | `snaptxt/postprocess/patterns/*.yaml`, `snaptxt/backend/logging.py` |
| 품질 점수(샘플) | 0.70 내외 (기존 테스트 로그) | **0.94** | `python experiments/scripts/research/enhanced_korean_processor.py` |
| 구조 복잡도 | 루트에 40+ 실험 스크립트 혼재 | `experiments/`로 격리 | `docs/plans/restructure_plan.md` 7단계 |

## 3. 브레인스토밍 – 다음 분기 우선 후보
1. **후처리 실험 자동화**
   - Stage 2/3 룰 변경 시 샘플 코퍼스 50건 자동 채점 → 품질 점수/규칙별 영향 히트맵 export.
   - `enhanced_korean_processor`를 pytest fixture에서 옵션으로 호출해 추가 지표 수집.
2. **데스크톱 앱 사용자 경험**
   - PyQt UI에 JSON 로그 뷰어 패널 추가, 최근 10건 추출 히스토리 표시.
   - 배치 작업 중 중단/재시작, 결과 CSV export.
3. **배포 및 관측성**
   - Windows 패키징( PyInstaller ) 및 self-update 스크립트 초안.
   - JSON 로그를 Loki/Elastic 등에 전달할 수 있는 forwarder 스크립트.
4. **모바일/웹 통합**
   - Flask API에 Stage 3 옵션 토글, 전처리 강도 슬라이더 제공.
   - 브라우저 TTS 스크립트에 한영 전환 자동 감지 추가.

## 4. 실행 계획 (Q2)
| 우선순위 | 작업 | 담당/메모 | 예상 산출물 |
| --- | --- | --- | --- |
| P1 | Stage 3 회귀 + 품질 점수 통합 대시보드 | 데이터/백엔드 | `scripts/run_quality_suite.ps1`, `reports/quality_dashboard.json` |
| P1 | PC 앱 로그 히스토리 패널 | 앱 팀 | `snaptxt/ui/desktop_app.py` 개선, 사용자 가이드 업데이트 |
| P2 | YAML 룰 diff 시뮬레이터 | 후처리 팀 | `tools/rule_diff.py`, 비교 리포트 템플릿 |
| P2 | PyInstaller 기반 데스크톱 배포 | 플랫폼 팀 | `dist/SnapTXT-Setup.exe`, 설치 가이드 |
| P3 | 웹 API 옵션 확장 | 서버 팀 | `README.md` API 섹션 갱신, Swagger 예시 |

## 5. 즉시 액션 항목
- `scripts/run_regression.ps1 -Smoke`를 하루 한 번 CI에 붙이고, 실패 시 로그 링크를 Slack에 전송.
- `enhanced_korean_processor` 결과를 Stage 3 회귀 출력에 함께 표시하도록 pytest 플러그인 초안 작성.
- 다음 스프린트 계획 회의에서 위 표 기반으로 담당자 배정 및 일정 확정.
