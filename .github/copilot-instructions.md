```instructions
# SnapTXT Development Compass - AI Assistant Instructions

## 🧭 현재 위치 확인 (2026-03-06)
**📍 Single Source of Truth**: [docs/status/current-work.md](../docs/status/current-work.md)
**모든 현재 상황과 우선순위는 위 파일에서만 확인하세요**

**📍 v2.1.3 Stable Working Engine** - 고정점 (수정 금지)  
**🔄 v2.2 Learning System** - 작업 영역 (4주 집중)

## ⚡ 30초 현황 파악 원칙
1. **현재 Layer**: L1~L5 중 작업 영역 명시
2. **구체적 파일/함수/라인** 제시
3. **재현→원인→수정→검증** 순서
4. **증거 2개 이상** 제출 (로그/파일명/스크린샷)
5. **v2.1.3 수정 금지**, v2.2만 작업

## 🔒 철칙 3개
1. **v2.1.3는 고정점** - 안정버전 더 이상 수정 금지
2. **v2.2 트랙에서만 개선** 
3. **증거 있는 전진 우선** - 작동 1건 + 로그 + 문서

## 🎯 우선순위 작업 (2026-03-06):
- [x] v2.1.3 Stable Working Engine 확정 완료
- [ ] Ground Truth 파일명 매핑 문제 해결 (최우선)
  - ground_truth_map.json 파일명 패턴 수정 필요
  - sample_XX_IMG_4975.JPG → sample_XX_IMG_4789.JPG 형식으로 변경
- [ ] 샘플 복사 기능 완전 수정 (최우선)
  - book_profile_experiment_ui.py의 copy_samples_to_directory() 함수 개선
  - .snaptxt/samples/ 폴더가 비어있는 문제 해결
- [ ] "샘플 폴더 열기" 버튼 UI 추가 (높음)
  - GPT 업로드 워크플로우 개선
  - 사용자 편의성 향상

## 📐 작업 템플릿
```
[Claude, SnapTXT Development Compass 기준]
1. Layer Map 위치: L1~L5 중 작업 영역 명시
2. 파일/함수/라인 제시
3. 재현→원인→수정→검증 순서
4. 증거 2개 이상 제출 (입력/출력/로그/파일명)  
5. v2.1.3 수정 금지, v2.2만 작업
```
```