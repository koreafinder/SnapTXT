# SnapTXT 문서 시스템 📋

**📍 [Current Work Status](status/current-work.md) - "30초 현황 파악" Single Source of Truth**  
*지금 어디에 있고, 무엇을 해야 하는지 여기서만 확인*

---

## 🎯 **현재 위치** (You are here)

**📍 v2.1.3 Stable Working Engine** - 고정점 (수정 금지)  
**🔄 v2.2 Learning System** - 작업 영역 (진행 중)

### **우선순위 작업** ⚡
1. **Ground Truth 파일명 매핑 수정** (최우선)
2. **샘플 복사 기능 정상화** (최우선)  
3. **"샘플 폴더 열기" UI 추가** (높음)

---

## 🗺️ **SnapTXT System Layer Map**

| Layer | 현재 상태 | 핵심 컴포넌트 |
|-------|-----------|---------------|
| **L1: Input** | ✅ 안정 | Office Lens, 폴더 드롭, 이미지 캡처 |
| **L2: OCR** | ✅ 안정 | EasyOCR 엔진, Google Vision GT 생성 |
| **L3: Postprocess** | ✅ 안정 | Stage1(전처리) → Stage2(교정) → Stage3(문맥) |  
| **L4: Learning** | 🔄 **작업중** | Ground Truth 학습, Overlay 생성, Book Profile |
| **L5: Output** | ✅ 안정 | 텍스트 저장, 웹 업로드, TTS |

**🎯 현재 집중 영역**: **L4 Learning System** 실사용화

## 🚀 빠른 시작 (start_work.bat 워크플로우)

### **⚡ 업무 시작 체크리스트 (2분)**
```bash
# 1. 작업 환경 확인
cd C:\dev\SnapTXT                    # ✅ 작업 폴더 확인
.\.venv\Scripts\activate             # ✅ Python 환경 활성화

# 2. 현재 상황 파악 (30초)
# ✅ 현재 위치: v2.1.3 Stable Working Engine (고정점)
# ✅ 오늘 작업: v2.2 Learning System 트랙
# ✅ 오늘 목표: "작동 증거 1건" (예: 샘플 복사 버튼 → 로그 확인)
```

### **📋 필수 읽기 순서 (Progress > Perfection)**
1. **[Project_Status_Summary_2026-03-06.md](Project_Status_Summary_2026-03-06.md)**: 전체 현황 30초 파악
2. **[SnapTXT_v2.1.3_Development_Plan.md](SnapTXT_v2.1.3_Development_Plan.md)**: v2.1.3 안정 엔진 상세  
3. **[v2.2_Future_Development_Plan.md](v2.2_Future_Development_Plan.md)**: 다음 4주 로드맵
4. **[status/current_work.md](status/current_work.md)**: 오늘의 세부 작업

### **작업 시작/완료 워크플로우**
- **작업 시작**: `.\start_work.bat` → **30초 현황 파악** + Layer Map 위치 확인
- **작업 완료**: `.\finish_work.bat "커밋메시지"` → 문서 정리 + 증거 기록

---

## 📐 **작업 원칙 (Progress > Perfection)**

### **🔒 철칙 3개** 
1. **v2.1.3는 고정점** - 안정버전은 더 이상 건드리지 않음
2. **v2.2 트랙에서만 개선** - 실험/개선은 별도 트랙으로 분리
3. **증거 있는 전진 우선** - "완벽" 보다 **작동 1건 + 로그 + 문서**

### **💡 작업 시 Claude 지시 템플릿**
```
[Claude, SnapTXT Development Compass 기준 작업]
1. 작업 위치 명시: Layer Map에서 현재 건드리는 영역 (L1~L5)
2. 관련 파일/함수/라인 제시
3. 재현 → 원인 → 수정 방향 → 검증(증거) 순서 준수
4. "완료" 조건: (입력/출력/로그/파일명) 4종 증거 중 최소 2개 제출
5. v2.1.3은 절대 수정 금지, v2.2 트랙에서만 작업
```

## 📂 폴더 구조

| 폴더 | 용도 | 주요 파일 |
|------|------|-----------|
| **foundation/** | 🏗️ 핵심 철학 (변하지 않는 기준) | project_memory.md, architecture.md |
| **status/** | 📊 진행 현황 (오늘 상태, 흐름) | current_work.md, progress_flow.md |
| **plans/** | 📋 계획/기획 (스프린트별 기획) | restructure_plan.md, phase별 계획들 |
| **reference/** | 📖 참고/가이드 (실행 가이드) | docs_guide.md, 각종 가이드 문서들 |
| **technical/** | ⚙️ 기술 문서 | 구현 상세, 완료 보고서들 |
| **ui/** | 🎨 UI/UX 관련 | UI 사양서, 디자인 문서들 |
| **meta/** | 🌍 범용 프레임워크 | AI 협업 워크플로우, 문서 정리 시스템 |

## 📜 문서 작성 규칙 (RFC 2119 스타일)

### **MUST 규칙 (필수)**
1. **파일명**: MUST use kebab-case (`current-work.md`, NOT `current_work.md`)
2. **백업파일**: MUST be moved to `archive/` folder immediately
3. **상태추적**: MUST include status in frontmatter (`draft/review/approved/deprecated`) 
4. **중복파일**: MUST NOT create duplicate files (merge or delete)

### **SHOULD 규칙 (강력 권장)**
1. **날짜 포맷**: SHOULD use ISO format `YYYY-MM-DD` in filenames
2. **카테고리 접두어**: SHOULD use prefixes (`project-`, `guide-`, `adr-`)
3. **링크**: SHOULD use relative paths for internal docs
4. **업데이트**: SHOULD update `current-work.md` when creating new plans

### **MAY 규칙 (선택)**
1. **템플릿**: MAY use document templates from `templates/` folder
2. **태그**: MAY include tags in frontmatter for categorization

### 파일 생명주기 관리
```
📄 새 문서 → draft상태 → review → approved → (필요시) deprecated → archive/
```

**백업 파일 규칙:**
- ✅ **자동백업**: `.backup_TIMESTAMP` 파일들은 즉시 `archive/` 이동
- ✅ **수동백업**: 중요 변경 시 `archive/YYYY-MM-DD-original-name.md` 형태로 저장
- ❌ **금지**: docs/ 루트에 백업파일 방치

**네이밍 일관성 강제:**
```bash
✅ 올바른 예시:
- adr-001-use-easyocr-engine.md
- project-book-profile-integration.md  
- guide-postprocessing-usage.md
- current-work.md

❌ 잘못된 예시:
- future_improvement_plan.md (snake_case 금지)
- 후처리_회귀_테스트_수정.md (한글 혼재 금지)
- current_work.backup_1772378572.md (백업파일 방치 금지)
```

### 새 문서 작성 절차
1. **[docs_guide.md](reference/docs_guide.md)**를 먼저 읽어 규칙 확인
2. Project Memory와 Architecture 확인
3. Current Work에서 현재 이슈 확인/업데이트
4. 적절한 폴더에 문서 작성
5. 이 README에 새 파일 추가

### 이름 짓기 규칙
- **기본 포맷**: `[카테고리]_[주제].md` 혹은 `YYYYMMDD_[주제].md`
- **계획 문서**: `plan_YYYYMM_topic.md`
- **가이드 문서**: `guide_topic.md`

## 📚 주요 문서 목록

### 🏗️ 핵심 기반 (Foundation)
- [Project Memory](foundation/project_memory.md) - 프로젝트 철학 및 기준
- [Architecture](foundation/architecture.md) - 시스템 구조 및 사용자 흐름

### 📊 진행 현황 (Status)  
- [Current Work](status/current_work.md) - 현재 작업 상황 및 우선순위
- [Progress Flow](status/progress_flow.md) - 프로젝트 히스토리 및 로드맵

### 📋 주요 계획 (Plans)
- [Restructure Plan](plans/restructure_plan.md) - 프로젝트 구조 개선 계획
- [Phase 1.8 Pattern Scope Policy](plans/phase1_8_pattern_scope_policy.md) - 패턴 범위 정책
- [Phase 2 Book Sense Engine](plans/phase2_book_sense_engine.md) - 책별 맞춤 교정 시스템
- [Future Improvement Plan](plans/future_improvement_plan.md) - 향후 개선 계획

### 📖 참고자료 (Reference)
- [Docs Guide](reference/docs_guide.md) - **📋 문서 작성 규칙 및 절차 (필수 읽기)**
- [AI Collaboration Framework](reference/ai_collaboration_framework.md) - AI 협업 프레임워크
- [Practical Guide](reference/practical_guide.md) - 실용 가이드
- [Rules Management](reference/rules_management.md) - 규칙 관리 가이드

### ⚙️ 기술 문서 (Technical)
- [Phase 1 MVP Pattern Engine](technical/phase1_mvp_pattern_engine.md) - 패턴 엔진 기술 사양
- [Phase 1.5 Session-aware Design](technical/phase1_5_session_aware_design.md) - 세션 인식 패턴 학습
- [Phase 3.1 INSERT Reverse Fix](technical/phase3_1_insert_reverse_fix.md) - INSERT 역변환 로직 수정 보고서
- [Context-Conditioned Replay Experiment](technical/context-conditioned-replay-experiment.md) - Context-aware vs Random 성능 비교 실험
- [Complete Achievement Report](technical/complete_achievement_report.md) - 완료 성과 보고서

### 🎨 UI/UX (User Interface)
- [Automated Book Profile UI Spec](ui/automated_book_profile_ui_spec.md) - 자동화된 북 프로필 UI 사양

### 🌍 범용 프레임워크 (Meta)
- [AI 워크플로우 자동화 시스템](meta/ai_workflow_automation.md) - **🚀 SnapTXT에서 검증된 AI 협업 자동화 기획서**
- [AI 협업 워크플로우 프레임워크](meta/ai_collaboration_framework.md) - **📚 다른 프로젝트 적용 가이드 및 범용 프레임워크**

## 🔄 유지보수 원칙

- 문서 변경 시 관련 링크 동기화 필수
- 새 문서 작성 시 이 README 업데이트  
- 오래된 문서는 `docs/archive/`로 이동
- start_work.bat/finish_work.bat 워크플로우 활용

## 💡 사용 팁

```bash
# 작업 세션 시작
.\start_work.bat

# 문서 상태 확인
.\check_docs.bat

# 작업 완료 및 GitHub 동기화  
.\finish_work.bat "커밋 메시지"
```

---

📌 **중요**: 새로운 작업을 시작하기 전에는 반드시 [docs_guide.md](reference/docs_guide.md)를 읽고 문서 작성 규칙을 확인하세요.