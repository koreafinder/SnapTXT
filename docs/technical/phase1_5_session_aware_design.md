# Phase 1.5: Session-aware Pattern Learning 설계

## 📋 프로젝트 개요
- **목표**: 책별, 세션별 특화 패턴 학습으로 실질적 OCR 품질 개선
- **배경**: Phase 1 MVP는 일반화 패턴만 학습하여 실제 품질 개선 효과 제한적
- **핵심**: Book Session Layer 추가로 컨텍스트별 패턴 분리

## 🎯 핵심 아이디어

### 현재 Phase 1의 한계
```
전체 OCR 데이터 → 일반화 패턴 학습 → 보편적이지만 효과적이지 않은 규칙
예: "SPACE_3 → SPACE_1", ".. → ."
```

### Phase 1.5의 접근법
```
OCR 데이터 → Session 분리 → 책별 특화 패턴 학습 → 실질적 품질 개선
예: "되엇 → 되었", "잇다 → 있다", "rn → m"
```

## 🏗️ 시스템 구조 개선

### 기존 DiffCollector 확장
```python
@dataclass
class SessionAwareTextDiff:
    # 기존 필드들
    before: str
    after: str
    change_type: str
    position: int
    confidence: float
    timestamp: datetime
    stage: str
    
    # 새로운 세션 컨텍스트 필드들
    book_session_id: str      # "20260302_bookA_batch1" 
    device_id: str            # "iphone12_user1"
    capture_batch_id: str     # 연속 촬영 세션 ID
    book_domain: str          # "novel", "textbook", "magazine"
    font_family: str          # 추론된 폰트 패밀리
    image_quality: float      # 이미지 품질 지표
```

### 계층화된 패턴 분석
```
Global Patterns (기존) - 모든 OCR에 공통
    ↓
Book Domain Patterns - 소설/교재/잡지별
    ↓  
Book Session Patterns - 특정 책의 특정 촬영 세션
    ↓
Capture Batch Patterns - 연속 촬영의 일관된 오류
```

## 🧠 Session-aware PatternAnalyzer 설계

### 패턴 분석 우선순위
```python
class SessionAwarePatternAnalyzer:
    def analyze_patterns(self, session_id: str) -> List[PatternCandidate]:
        # 1. Batch-specific patterns (최고 우선순위)
        batch_patterns = self._analyze_batch_patterns(session_id)
        
        # 2. Book-specific patterns  (중간 우선순위)
        book_patterns = self._analyze_book_patterns(session_id)
        
        # 3. Domain-specific patterns (낮은 우선순위)
        domain_patterns = self._analyze_domain_patterns(session_id)
        
        # 4. Global patterns (최저 우선순위)
        global_patterns = self._analyze_global_patterns()
        
        return self._merge_with_priority(batch_patterns, book_patterns, 
                                       domain_patterns, global_patterns)
```

### 실질적 패턴 발견 로직
```python
def _analyze_batch_patterns(self, session_id: str) -> List[PatternCandidate]:
    """연속 촬영에서 일관되게 발생하는 오류 패턴 분석"""
    
    # 동일 배치에서 3회 이상 반복되는 패턴
    # 예: "되엇 → 되었" 패턴이 같은 책 촬영에서 계속 발생
    batch_diffs = self._load_batch_diffs(session_id)
    
    # 폰트 특화 오인식 패턴 우선 감지
    font_specific_patterns = self._detect_font_patterns(batch_diffs)
    
    return font_specific_patterns
```

## 📘 Book Profile Engine 설계

### GPT 기반 Book Profiling
```python
class BookProfileEngine:
    def create_book_profile(self, sample_pages: List[str]) -> BookProfile:
        """샘플 페이지로 책 프로파일 생성"""
        
        # 1. GPT로 정답 텍스트 생성
        ground_truths = []
        for page_ocr in sample_pages:
            corrected = self.gpt_corrector.correct_text(page_ocr)
            ground_truths.append(corrected)
        
        # 2. OCR vs GPT 차이 분석
        book_patterns = []
        for ocr, truth in zip(sample_pages, ground_truths):
            patterns = self.analyze_ocr_vs_truth(ocr, truth)
            book_patterns.extend(patterns)
        
        # 3. 책 전용 규칙 생성
        return BookProfile(
            book_id=self.generate_book_id(),
            patterns=book_patterns,
            font_family=self.detect_font_family(sample_pages),
            quality_baseline=self.calculate_baseline_quality(sample_pages)
        )
```

### BookProfile 적용
```python
@dataclass
class BookProfile:
    book_id: str
    patterns: List[BookSpecificPattern]
    font_family: str
    quality_baseline: float
    created_at: datetime
    
    def apply_book_specific_corrections(self, text: str) -> str:
        """책 전용 패턴 적용"""
        corrected = text
        
        for pattern in self.patterns:
            if pattern.confidence > 0.8:  # 높은 신뢰도만
                corrected = pattern.apply(corrected)
        
        return corrected
```

## 🔄 업그레이드된 데이터 플로우

### 기존 플로우
```
OCR 텍스트 → 후처리 → 패턴 수집 → 전역 분석 → 일반 규칙
```

### 새로운 플로우  
```
OCR 텍스트 → 세션 감지 → 후처리 + 세션별 패턴 수집
    ↓
세션별 분석 → 책별 분석 → 도메인별 분석 → 전역 분석
    ↓
계층화된 규칙 적용 (구체적 → 일반적 순)
```

## 📊 예상 품질 개선 효과

### 현재 Phase 1 (일반화 패턴)
- 공백 정리, 문장부호 정리
- **예상 개선**: +0.3~0.5%

### 제안 Phase 1.5 (세션별 패턴)
- 폰트 특화 오인식 교정
- 책별 일관된 오류 패턴 교정  
- **예상 개선**: +2~5%

## 🛡️ 구현 전략

### 1단계: Session Context 추가 (이번 주)
- DiffCollector에 세션 필드 추가
- 기존 코드 영향 최소화
- 점진적 데이터 수집 시작

### 2단계: Session-aware Analysis (다음 주)  
- PatternAnalyzer 계층화 분석 추가
- 우선순위 기반 패턴 적용
- 세션별 성능 모니터링

### 3단계: Book Profile Engine (2주차)
- GPT 기반 샘플 교정 시스템
- 책별 프로파일 생성 및 적용
- A/B 테스트로 효과 검증

## 🎯 성공 기준

### 정량적 지표
- **패턴 품질**: 실질적 읽기 개선 패턴 비율 > 80%
- **적용 효과**: 세션별 OCR 품질 개선 > 2%
- **사용자 만족도**: 책 읽기 경험 개선 체감도

### 정성적 지표
- 폰트 특화 오인식 교정 성공
- 책별 일관된 오류 해결
- 사용할수록 더 정확해지는 경험

## 🚀 다음 액션 플랜

**즉시 실행 (오늘)**:
1. DiffCollector에 세션 컨텍스트 필드 추가
2. 세션 ID 생성 로직 구현
3. 기존 패턴 수집에 세션 정보 추가

**Phase 1.5 완성 (1주)**:
1. SessionAwarePatternAnalyzer 구현
2. 계층화된 패턴 분석 로직
3. 실제 세션별 패턴 검증

**Book Profile Engine (2주)**:
1. GPT 기반 샘플 교정 시스템
2. BookProfile 생성 및 적용
3. 전체 시스템 통합

---

**결론**: Phase 1.5는 SnapTXT를 "단순한 OCR 앱"에서 "책을 이해하는 지능형 OCR"로 진화시키는 핵심 단계입니다.