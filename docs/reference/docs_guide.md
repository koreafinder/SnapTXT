# Docs 안내서

SnapTXT에서 문서를 작성하거나 참고할 때 이 파일을 먼저 읽습니다. Project_Memory와 Architecture가 방향을 고정하고, 나머지 문서가 세부 실행을 담당합니다.

## 1. 필수 읽기 순서
1. **Project_Memory.md**: 프로젝트 목적·철학·실행 기준. 무엇을 위해 일하는지 먼저 확인합니다.
2. **Architecture.md**: 사용자 흐름과 시스템 구성. 구현/수정 시 어떤 계층을 건드리는지 파악합니다.
3. **Current_Work.md**: 오늘의 진행 상황과 다음 할 일. 착수 전, 해당 섹션을 업데이트하거나 확인합니다.
4. **progress_flow.md**: 히스토리/로드맵. 과거 결정과 스프린트 맥락을 확인합니다.

## 2. 폴더/파일 분류
| 구분 | 용도 | 현재 파일 | 향후 위치 가이드 |
| --- | --- | --- | --- |
| 핵심 철학 (foundation) | 변하지 않는 기준 | Project_Memory.md, Architecture.md | `docs/foundation/` (필요 시 이동) |
| 진행 현황 (status) | 오늘 상태, 흐름 | Current_Work.md, progress_flow.md | `docs/status/` (필요 시 이동) |
| 계획/기획 (plans) | 스프린트별 기획, 품질 실험 계획 | plans/restructure_plan.md, plans/future_improvement_plan.md 등 | `docs/plans/` 내부에 `YYYYMM_plan-name.md` |
| 참고/가이드 (reference) | PRACTICAL_GUIDE 등 실행 가이드 | PRACTICAL_GUIDE.md, README.md | `docs/reference/` 혹은 루트 README |

> **Note**: foundation/status/plans 디렉터리로 정리 중이니, 새 문서는 해당 경로에 바로 작성하고 루트에 남은 문서는 순차적으로 이동합니다.

## 3. 이름 짓기 규칙
- **기본 포맷**: `[카테고리]_[주제].md` 혹은 `YYYYMMDD_[주제].md`
- **카테고리 접두어 예시**
  - `foundation_` → 철학/아키텍처 (이미 존재하는 파일은 고유 이름 유지)
  - `status_` → 진행 상황
  - `plan_YYYYQX_주제` → 분기별 계획
  - `guide_` → 실용 가이드/튜토리얼
- 링크/레퍼런스를 깨지지 않게 하려면 파일 이동 전에 README와 progress_flow에 반영합니다.

## 4. 새 문서 작성 절차
1. Project_Memory와 Architecture를 읽어 목적과 구조를 확인합니다.
2. Current_Work에서 현재 이슈/태스크를 확인하고 필요한 경우 업데이트합니다.
3. 새 문서가 **계획**이라면 `docs/plans/plan_YYYYMM_topic.md` 형식으로 작성하고 progress_flow에 링크를 추가합니다.
4. 새 문서가 **레퍼런스/가이드**라면 `docs/guide_topic.md` 혹은 해당 카테고리 디렉터리에 넣습니다.
5. 작성 후 본 README의 표에 새 파일을 한 줄로 추가합니다.

## 5. 유지보수 원칙
- 문서가 바뀌면 관련 링크(progress_flow, README, Current_Work)를 반드시 동기화합니다.
- “필수 읽기 순서” 목록이 바뀌는 경우, 팀원에게 공유하고 Project_Memory에도 필요한 내용을 갱신합니다.
- 오래된 문서는 `docs/archive/`로 이동하고 progress_flow에 이동 기록을 남깁니다.

이 README를 출발점으로 삼으면, 새로운 기획이나 리팩토링을 시작하기 전에 어떤 문서를 봐야 하고 어디에 기록해야 하는지 즉시 파악할 수 있습니다.
