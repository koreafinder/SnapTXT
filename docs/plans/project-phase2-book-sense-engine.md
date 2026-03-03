# Phase 2: Book Sense Engine 설계서

**프로젝트**: SnapTXT Phase 2 - Book Sense Engine  
**작성일**: 2026년 3월 2일 (Phase 1.8 완료 후 재정립)  
**우선순위**: 메인 (품질 점프의 핵심)  
**예상 기간**: 3-5일  
**철학**: 비용 0, 로컬 진화, 사용자 제어

## 🔥 **핵심 패러다임 전환**

### **Before Phase 2**: 사후 학습 방식 ❌
```
OCR → 틀림 → 수정 → 학습 → 다음에 적용
(느리고, 수동적, 데이터 의존적)
```

### **After Phase 2**: 사전 기준 생성 ✅
```
샘플 → Book Fingerprint → GPT 정답 생성 → Book Profile → OCR 교정
(빠르고, 능동적, 책별 최적화)
```

## 🎯 **SnapTXT 철학 유지**

### **절대 원칙**
- ✅ **비용 0**: GPT 1회만 사용, 이후 로컬 진화
- ✅ **로컬 진화**: Book Profile 기반 자율 개선
- ✅ **사용자 제어**: GPT는 도구, SnapTXT가 주인

### **GPT 역할 명확화**
- 👉 **정답 생성기** (O): 책별 교정 기준 1회 제공
- ❌ **교정 엔진 아님**: 매번 호출하지 않음
- ❌ **의존성 없음**: GPT 없이도 기존 기능 유지

## 🏗️ **3단계 설계 구조**

### **1️⃣ Book Fingerprint System** (GPT 전에 필수)

**목적**: 같은 책 여부 판단하여 Book Profile 재사용

```python
class BookFingerprinter:
    def analyze_book_characteristics(self, ocr_results: List[str]) -> BookFingerprint:
        # OCR 결과만으로 책 특성 추출
        typography_style = self._extract_typography_patterns(ocr_results)
        spacing_patterns = self._extract_spacing_patterns(ocr_results)
        punctuation_style = self._extract_punctuation_patterns(ocr_results)
        language_style = self._extract_language_patterns(ocr_results)
        
        return BookFingerprint(
            typography=typography_style,  # 폰트 특성
            spacing=spacing_patterns,     # 행간/자간 특성
            punctuation=punctuation_style, # 인용부호/말줄임표 스타일
            language=language_style,      # 조사 사용/문장 구조
            book_hash=self._generate_book_hash(...)
        )
```

**추출 가능한 책 특성들**:
- **폰트 특성**: 'l'/1 혼동 패턴, 'rn'/m 패턴
- **행간/자간**: 줄 길이 패턴, 문단 구조
- **인용 스타일**: ", ', «», ..." 등
- **언어 스타일**: 조사 사용 빈도, 문어체/구어체
- **출판사 스타일**: 장평, 자간 특성

### **2️⃣ Google Vision API Integration** ✅ **완료 (2026-03-03)**

**목적**: OCR 자동화 + GPT 교정 기준 생성을 1회성 개입으로 통합

**✅ 달성된 성과 (Google Vision API 자동화):**
- 📊 **10개 샘플 OCR 완료**: 4,270글자 자동 추출 
- ⚡ **45분 → 2분 단축**: 완전 자동화 워크플로우 구축
- 🤖 **자동 Ground Truth 생성**: `auto_ground_truth.json` 완성
- 💰 **비용 최적화**: 월 1000장 무료 + 품질 향상

```python
class GoogleVisionBookAnalyzer:  # ✅ 이미 구현됨
    def generate_book_profile_from_vision_ocr(self, gcr_results: Dict[str, str], fingerprint: BookFingerprinter) -> dict:
        """Google Vision OCR 결과로부터 책 교정 기준 생성"""
        
        # Google Vision OCR 결과 활용
        ocr_samples = list(gcr_results.values())[:5]  # 최대 5페이지 활용
        
        책 특성:
        - 폰트 패턴: {fingerprint.typography}
        - 언어 스타일: {fingerprint.language}
        
        다음 형식으로 응답해주세요:
        {{
            "common_corrections": [
                {{"pattern": "되엇", "replacement": "되었", "confidence": 0.95}},
                {{"pattern": "잇다", "replacement": "있다", "confidence": 0.9}}
            ],
            "spacing_style": {{
                "dialog": "keep_original",  # 대화체 띄어쓰기 유지
                "narration": "normalize"    # 서술부 띄어쓰기 정규화
            }},
            "punctuation_style": {{
                "ellipsis": "…",           # 말줄임표 스타일
                "quote_style": "\\"...\\""   # 인용부호 스타일
            }},
            "typography_bias": [
                {{"error_type": "l_to_1", "threshold": 0.8}},
                {{"error_type": "rn_to_m", "threshold": 0.7}}
            ]
        }}
        """
        
        # GPT 호출 (1회만!)
        response = self.call_gpt_once(prompt)
        return parse_gpt_response(response)
```

### **3️⃣ Book Profile Generation** (SnapTXT 내부 규칙화)

**목적**: GPT 결과를 PatternScopePolicy 내부의 book scope으로 변환

```python
class BookProfileGenerator:
    def generate_book_profile(self, gpt_response: dict, fingerprint: BookFingerprinter) -> BookProfile:
        """GPT 결과 → SnapTXT 내부 YAML 규칙"""
        
        book_profile = BookProfile(
            book_id=fingerprint.book_hash,
            fingerprint=fingerprint,
            
            # SnapTXT 내부 규칙으로 변환
            correction_rules=self._convert_to_pattern_rules(gpt_response["common_corrections"]),
            spacing_rules=self._convert_to_spacing_rules(gpt_response["spacing_style"]),
            typography_rules=self._convert_to_typography_rules(gpt_response["typography_bias"]),
            
            # 안전 장치
            strength="weak",  # weak/medium/strong (창작 왜곡 방지)
            confidence=self._calculate_overall_confidence(gpt_response),
            created_at=datetime.now(),
            usage_count=0
        )
        
        return book_profile
```

## 🧪 **Book Profile YAML 구조**

```yaml
# book_profile_a1b2c3d4.yaml
book_id: "a1b2c3d4e5f6"
created_at: "2026-03-02"
strength: "weak"  # weak/medium/strong
usage_count: 0
confidence: 0.85

fingerprint:
  typography: ["font_modern", "l_1_confusion", "rn_m_pattern"]
  spacing: ["narrow_line", "compact_paragraph"]
  punctuation: ["korean_quotes", "ellipsis_dots"]
  language: ["formal_tone", "literary_style"]

correction_rules:
  - pattern: "되엇"
    replacement: "되었"
    scope: "book"
    confidence: 0.95
    priority: "high"
    
  - pattern: "잇다"
    replacement: "있다" 
    scope: "book"
    confidence: 0.9
    priority: "medium"

spacing_rules:
  dialog:
    strategy: "keep_original"
    reason: "creative_expression"
  
  narration:
    strategy: "normalize"
    reason: "readability"

typography_rules:
  - error_type: "l_to_1"
    threshold: 0.8
    scope: "book"
    
  - error_type: "rn_to_m"  
    threshold: 0.7
    scope: "book"

safety_limits:
  max_corrections_per_text: 20
  min_confidence_threshold: 0.7
  overfitting_prevention: true
```

## 📈 **예상 효과 (현실적 평가)**

### **체감 품질 개선 요소**
| 개선 영역 | 영향도 | 설명 |
|----------|---------|------|
| **띄어쓰기 안정화** | 크다 | 책별 띄어쓰기 스타일 일관성 |
| **조사 오류 감소** | 중간 | 은/는, 을/를 등 맞춤형 교정 |
| **문장 흐름 자연화** | 크다 | 책의 문체에 맞는 자연스러운 교정 |
| **TTS 읽기 품질** | 매우 큼 | 웹 읽기 + 오디오북 품질 향상 |

### **기존 vs Phase 2 비교**
```
기존: "일반적인 OCR 후처리"
      SPACE_3→SPACE_1, ..→. 등

Phase 2: "책 맞춤형 교정"
         이 책에서는 '되엇→되었'
         이 책 대화체는 띄어쓰기 유지
         이 책 서술부는 띄어쓰기 정규화
```

## ⚠️ **리스크 관리**

### **창작 왜곡 방지**
```python
class SafetyController:
    def validate_book_profile_strength(self, profile: BookProfile, content_type: str):
        if content_type == "creative_writing":
            profile.strength = "weak"  # 창작물은 최소 개입
        elif content_type == "technical":
            profile.strength = "medium"  # 기술서는 중간 개입
        elif content_type == "reference":
            profile.strength = "strong"  # 참고서는 적극 교정
```

### **GPT 의존성 최소화**
- GPT 호출은 책당 1회만
- GPT 없이도 기존 기능 100% 유지
- Book Profile은 SnapTXT 내부 포맷으로 변환 후 사용

### **성능 및 비용 제어**
- Book Profile 캐싱으로 재사용
- 동일 책 감지시 GPT 재호출 없음
- 로컬 진화로 품질 지속 개선

## 🔄 **Phase 1.8과의 통합**

**Book Sense Engine → PatternScopePolicy 연동**

```python
# Book Profile의 패턴들이 PatternScopePolicy의 "book" scope으로 등록
book_patterns = book_profile.correction_rules

for pattern in book_patterns:
    pattern_app = PatternApplication(
        pattern=pattern.pattern,
        replacement=pattern.replacement,
        priority=ApplicationPriority.BOOK_HIGH,  # 책별 우선순위
        risk_level=PatternRiskLevel.BOOK_HIGH,   # 책별 위험도
        applicable_contexts=[f"book:{book_profile.book_id}"]  # 적용 컨텍스트
    )
    
    # PatternScopePolicy가 안전성 검증 후 적용
```

## 📅 **구현 계획**

### **Day 1-2: Book Fingerprint System** 🔄 **현재 진행 중**
- [x] **BookFingerprinter 클래스 구현** ✅ (513줄, 이미 완성)
- [x] **Typography/Spacing/Punctuation 패턴 추출기** ✅
- [x] **Book Hash 생성 알고리즘** ✅  
- [ ] **테스트: Google Vision OCR 결과로 Fingerprint 생성**
- [ ] **검증: 동일 책 감지 정확도 (4,270글자 활용)**

### **Day 3: Google Vision + GPT Integration** ✅ **Google Vision 완료**
- [x] **Google Vision API 자동화 완성** (2026-03-03)
- [x] **OCR 결과 4,270글자 확보** (10개 샘플)
- [x] **자동 Ground Truth 생성** (`auto_ground_truth.json`)
- [ ] GPT 1회 호출로 교정 기준 생성 (기존 OCR 결과 활용)
- [ ] Google Vision + GPT 통합 파이프라인 완성

### **Day 4-5: Book Profile System**
- [ ] BookProfileGenerator 클래스 구현  
- [ ] YAML 저장/로드 시스템
- [ ] PatternScopePolicy 통합
- [ ] 테스트: 전체 파이프라인 검증

## 🎯 **성공 지표**

### **기술적 지표**
- Book Fingerprint 정확도: 95% 이상
- GPT 정답 생성 품질: 85% 이상  
- Book Profile 적용 성공율: 90% 이상

### **사용자 경험**
- 동일 책 재촬영시 즉시 개선 체감
- TTS 읽기 품질 향상 확인
- 창작 왜곡 없는 자연스러운 교정

---

## 🚀 **Book Sense Engine = SnapTXT의 차별화 지점**

**"책을 이해하는 OCR"**에서 **"책별 맞춤 교정 엔진"**으로!

**SnapTXT만의 혁신**: 
- 📚 Book-aware Intelligence
- 🔬 Pattern-based Adaptation  
- 🛡️ Safety-first Evolution
- 💝 Zero-cost Local Learning