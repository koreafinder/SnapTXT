# ⚠️ 이 파일은 더 이상 사용되지 않습니다

**Development Compass 개념이 다음 위치로 통합되었습니다:**  
👉 **[docs/status/current-work.md](status/current-work.md)** ← **Single Source of Truth**

---

## ℹ️ 통합 이유
- **문서 분산 문제 해결**: "현재 상황" 문서가 너무 많았음
- **Single Source of Truth 원칙**: current-work.md 하나로 통일
- **규약 준수**: 기존 문서 체계 유지하면서 개선

## 📍 현재 상황 확인 방법
```bash
# 1. current-work.md 열기
code docs/status/current-work.md

# 2. 또는 start_work.bat 실행
.\start_work.bat
```

**Development Compass의 핵심 개념들은 모두 current-work.md에 포함되어 있습니다.**

---

*마지막 업데이트: 2026-03-06*  
*통합 완료: Development Compass → current-work.md*

2. **샘플 복사 기능 완전 수정** (최우선)
   - 문제: `.snaptxt/samples/` 폴더 비어있음
   - 목표: "버튼 한 번"으로 샘플 관리 자동화

3. **"샘플 폴더 열기" UI 추가** (높음)
   - 목표: "학습→overlay 생성→즉시 검증" 워크플로우

---

## 📐 작업 원칙

### 🔒 철칙 3개
1. **v2.1.3는 고정점** - 안정버전 더 이상 수정 금지
2. **v2.2 트랙에서만 개선**  
3. **증거 있는 전진 우선** - 작동 1건 + 로그 + 문서

### ⚡ 작업 시작 체크리스트
- [ ] 작업 폴더: `C:\dev\SnapTXT` 확인
- [ ] 현재 위치: v2.1.3 (고정점) vs v2.2 (작업영역) 구분  
- [ ] 오늘 목표: "작동 증거 1건" 정의

### 💡 Claude 작업 지시 템플릿  
```
[Claude, SnapTXT Development Compass 기준]
1. Layer Map 위치 명시: L1~L5 중 작업 영역
2. 파일/함수/라인 제시
3. 재현→원인→수정→검증 순서
4. 증거 2개 이상 제출 (입력/출력/로그/파일명)  
5. v2.1.3 수정 금지, v2.2만 작업
```

---

## ⚙️ 빠른 실행 명령

```bash
# 작업 시작
.\start_work.bat

# 메인 앱 실행  
python main.py

# PC 앱 실행
python pc_app.py

# 문서 확인
.\check_docs.bat
```

---

**마지막 업데이트**: 2026-03-06  
**다음 마일스톤**: v2.2 Learning System 실사용화 (4주)
