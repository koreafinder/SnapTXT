# Phase 1.8: Pattern Scope Policy 설계서

**프로젝트**: SnapTXT Phase 1.8 - Pattern Scope Policy  
**작성일**: 2026년 3월 2일  
**우선순위**: 긴급 (현재 시스템 위험 방지)  
**예상 기간**: 1-2일

## 🎯 프로젝트 목적

### 주요 목적
**Overfitting OCR 방지**: 패턴 잘못 적용으로 인한 품질 저하 방지

### 핵심 문제
```
책 A에서: "l" → "1" 패턴 발견  
책 B에서: "l" = 진짜 소문자 L  
→ 잘못 적용하면 품질 오히려 떨어짐
```

### 해결 전략
- **Pattern Risk Level 분류**: global/book/batch별 위험도 평가
- **Application Priority 정책**: 구체적 패턴 우선 적용
- **Safety Validation**: 패턴 적용 전 안전성 검증

## 🛠️ 기술적 설계

### 1. Pattern Risk Level 분류 시스템
```python
class PatternRiskLevel:
    GLOBAL_SAFE = "global"      # 가장 안전, 모든 컨텍스트에 적용 가능
    DOMAIN_MEDIUM = "domain"    # 도메인별 안전 (학술/소설 등)
    BOOK_HIGH = "book"          # 책별 안전 (특정 폰트/인쇄소)
    BATCH_CRITICAL = "batch"    # 가장 위험, 연속 촬영내에서만
```

### 2. Pattern Scope Definition
```yaml
pattern_scopes:
  # 전역 패턴 (가장 안전)
  - pattern: "SPACE_3 → SPACE_1"
    scope: global
    risk_level: safe
    confidence: 0.8
    
  - pattern: ".. → ."
    scope: global
    risk_level: safe  
    confidence: 0.8
    
  # 책별 패턴 (주의 필요)
  - pattern: "되엇 → 되었"
    scope: book
    risk_level: medium
    confidence: 0.82
    book_fingerprint: "korean_novel_font_a"
    
  # 배치별 패턴 (고위험)
  - pattern: "rn → m"
    scope: batch
    risk_level: high
    confidence: 0.75
    context_required: true
```

### 3. Application Priority System
```python
class PatternApplicationPolicy:
    PRIORITY_ORDER = [
        "batch",    # 가장 구체적, 최고 우선순위
        "book",     # 책별 특화
        "domain",   # 도메인별  
        "global"    # 가장 일반적, 최저 우선순위
    ]
    
    def apply_patterns(self, text, session_context):
        # 우선순위에 따른 패턴 적용
        # 캡처가 있으면 범위 좁은 규칙 적용 안함
```

### 4. Safety Validation Logic
```python
class PatternSafetyValidator:
    def validate_pattern_safety(self, pattern, context):
        # 1. 기본 안전성 검사
        if self._is_destructive_pattern(pattern):
            return ValidationResult.REJECT
            
        # 2. 맥락 적합성 검사  
        if not self._fits_context(pattern, context):
            return ValidationResult.CAUTION
            
        # 3. 빈도 임계값 검사
        if pattern.frequency < self.MIN_FREQUENCY:
            return ValidationResult.INSUFFICIENT_DATA
            
        return ValidationResult.SAFE
```

## 📋 구현 계획

### 단계 1: Pattern Risk Assessment (Day 1)
- [ ] **기존 패턴 위험도 평가**
  - Phase 1 패턴 2개 분석
  - Phase 1.5 패턴 3개 분석  
  - 위험도 라벨링 및 근거 정의
  
- [ ] **Risk Level 결정 기준 수립**
  - 글자 빈도 기반 위험도 
  - 문맥 의존성 기반 위험도
  - 단어 경계 전후 분석

### 단계 2: Policy Engine 구현 (Day 2)
- [ ] **PatternScopePolicy 클래스 개발**
  ```python
  class PatternScopePolicy:
      def get_applicable_patterns(self, context) -> List[Pattern]:
          # 컨텍스트에 따른 적용 가능 패턴 반환
          pass
  ```

- [ ] **Safety Validator 통합**
  - 기존 DiffCollector와 연결
  - PatternAnalyzer에 안전성 검증 추가
  - RuleGenerator에 모든 위험 라벨 정보 포함

### 단계 3: 테스트 및 검증 (Day 2)
- [ ] **안전성 테스트 스위트**
  - 위험한 패턴 상황 시뮬레이션
  - 오적용 감지 테스트  
  - 성능 저하 방지 검증

## 📊 기대 효과

### 주요 성과
- **안전성 향상**: Overfitting OCR 완전 방지
- **신뢰성 증대**: 패턴 적용에 대한 사용자 신뢰
- **확장성 확보**: Phase 2 Book Bootstrap의 안전한 기반

### 품질 영향
- **단기**: 위험한 패턴 적용 방지 → 0% 품질 저하 방지
- **장기**: 안전한 패턴만 축적 → 지속적 품질 향상

## 위험 요소 및 대응 방안

### 주요 위험
1. **성능 오버헤드**: 안전성 검증으로 인한 속도 저하
2. **오탐지**: 안전한 패턴도 차단
3. **완전성**: 모든 엣지 케이스 예측 어려움

### 대응 방안
- **성능**: 캐시 시스템 도입
- **오탐지**: 점진적 전개, A/B 테스트
- **완전성**: 모니터링 시스템 구축

## 다음 단계와의 연결

**Phase 2 Book Bootstrap Engine 준비**:
- 안전한 Pattern Scope Policy로 GPT 기반 패턴 안전성 보장
- 책별 특화 패턴 생성 시 자동 리스크 평가
- Book Ground Truth 생성 과정에서 안전성 검증 자동화

---

**작성**: GitHub Copilot (Claude Sonnet 4)  
**업데이트**: 2026년 3월 2일 오후 9시  
**상태**: 설계 완료, 구현 대기 중