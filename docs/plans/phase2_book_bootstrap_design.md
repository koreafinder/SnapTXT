# Phase 2: Book Bootstrap Engine 설계서

**프로젝트**: SnapTXT Phase 2 - Book Bootstrap Engine  
**작성일**: 2026년 3월 2일  
**우선순위**: 메인 (진짜 품질 점프 목표)  
**예상 기간**: 1주일

## 🎯 프로젝트 목적

### 핵심 비전
**"패턴 발견 기다리기"에서 "교정 기준 생성"으로 전환**

### 주요 목적
- **Book Ground Truth 생성**: GPT 기반 책별 맞춤형 교정 기준 생성
- **Book-aware OCR**: 책의 특성을 이해하는 지능형 OCR 완성
- **진짜 품질 점프**: +3~6% 체감 품질 향상 달성

### 패러다임 전환
```
Before: 패턴이 쌓일 때까지 기다린다
After: 처음부터 책별 교정 기준을 만든다

Before: 되엇→되었 패턴이 5회 나타나면 학습
After: 책 샘플 5개 → GPT "이 책에서 되엇은 되었이 맞습니다"
```

## 🚀 핵심 혁신점

### 1. Book Ground Truth Bootstrap
**개념**: 적은 샘플로 책 전체의 교정 기준 생성

```python
class BookBootstrapEngine:
    def bootstrap_book_standards(self, book_samples: List[str]) -> BookProfile:
        # 샘플 5개만으로 책 전체 교정 기준 생성
        book_profile = self.gpt_analyze_book_characteristics(book_samples)
        correction_rules = self.generate_book_specific_rules(book_profile)
        return BookProfile(rules=correction_rules, confidence=book_profile.confidence)
```

### 2. GPT 기반 언어 모델 활용
**핵심**: 책의 장르, 시대, 문체, 전문성을 이해하는 교정

```python
def gpt_analyze_book_characteristics(self, samples):
    prompt = f"""
    다음 텍스트 샘플들을 분석해주세요:
    {samples}
    
    이 책의 특성을 파악하고 다음을 제공해주세요:
    1. 장르 (소설/학술/교양/기술서 등)
    2. 언어 특성 (문어체/구어체, 전문용어 빈도 등)
    3. 예상되는 OCR 오류 패턴
    4. 이 책에 특화된 교정 규칙 5개
    """
```

### 3. Context-Aware 패턴 생성
**혁신**: 책의 맥락을 이해하는 지능형 교정

```xml
<book_profile id="novel_korean_romance_2020s">
    <genre>로맨스 소설</genre>
    <language_style>현대 구어체, 감정 표현 풍부</language_style>
    <correction_rules>
        <rule pattern="되엇" replacement="되었" confidence="0.95" context="감정 표현"/>
        <rule pattern="잇다" replacement="있다" confidence="0.93" context="상태 표현"/>
        <rule pattern="않으" replacement="않은" confidence="0.87" context="부정 표현"/>
    </correction_rules>
</book_profile>
```

## 🏗️ 시스템 아키텍처

### 1. Book Fingerprinting System
```python
class BookFingerprinter:
    def generate_book_fingerprint(self, text: str) -> BookFingerprint:
        """텍스트 샘플로부터 책 고유 특성 추출"""
        return BookFingerprint(
            genre=self._detect_genre(text),
            language_style=self._analyze_language_style(text),
            vocabulary_level=self._assess_vocabulary(text),
            writing_period=self._estimate_writing_period(text),
            specialty_domain=self._detect_domain(text)
        )
```

### 2. GPT Integration Layer  
```python
class GPTBookAnalyzer:
    def analyze_book_language_patterns(self, fingerprint, samples):
        """GPT를 활용한 책별 언어 패턴 분석"""
        analysis_prompt = self._build_analysis_prompt(fingerprint, samples)
        gpt_response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": analysis_prompt}]
        )
        return self._parse_gpt_analysis(gpt_response)
```

### 3. Book-Specific Rule Generator
```python
class BookSpecificRuleGenerator:
    def generate_book_rules(self, book_analysis) -> List[BookRule]:
        """책별 특화 교정 규칙 생성"""
        return [
            BookRule(
                pattern=rule.pattern,
                replacement=rule.replacement,
                confidence=rule.confidence,
                context=rule.context,
                book_scope=True,
                applicable_genres=[book_analysis.genre]
            )
            for rule in book_analysis.suggested_rules
        ]
```

## 📊 구현 단계별 계획

### Phase 2.1: Core Bootstrap Engine (Day 1-2)
- [ ] **BookFingerprinter 개발**
  - 장르 자동 감지 (소설/학술/교양/기술서/뉴스)
  - 언어 스타일 분석 (문어체/구어체, 전문성 수준)
  - 어휘 수준 평가 (고급/일반/전문용어 빈도)

- [ ] **GPT Integration 구현**
  - OpenAI API 연동
  - Book-specific prompt engineering
  - 응답 파싱 및 규칙 추출

### Phase 2.2: Rule Generation & Validation (Day 3-4)
- [ ] **BookSpecificRuleGenerator**
  - GPT 분석 결과 → 교정 규칙 변환
  - Pattern Scope Policy와 통합
  - 안전성 검증 자동화

- [ ] **Quality Assessment System**  
  - 생성된 규칙의 품질 평가
  - A/B 테스트 자동화
  - 효과 측정 및 피드백

### Phase 2.3: Integration & Testing (Day 5-6)
- [ ] **기존 시스템과 통합**
  - SessionAwarePatternAnalyzer와 연동
  - DiffCollector에 Book Bootstrap 정보 추가
  - 실시간 책 분석 파이프라인 구축

- [ ] **Comprehensive Testing**
  - 다양한 장르별 테스트 (소설/학술/뉴스/기술서)  
  - 품질 향상 정량 측정
  - 안전성 검증 (Overfitting 방지)

### Phase 2.4: Production Deployment (Day 7)
- [ ] **Production Ready**
  - 성능 최적화 (캐싱, 배치 처리)
  - 모니터링 시스템 구축
  - 문서화 완료

## 🎯 예상 성과

### 품질 향상 목표
```
현재: Session 패턴 +1~2% 품질 향상
Phase 2 목표: +3~6% 체감 품질 향상

구체적 개선:
- 책별 특화 오타 교정: +2~3%
- 맥락 기반 용어 정리: +1~2%  
- 장르별 문체 최적화: +1~1.5%
```

### 사용자 경험 혁신
```
Before: "OCR 잘하는 앱"
- 일반적인 오타만 수정
- 모든 책에 동일한 처리

After: "책을 이해하는 OCR"  
- 이 책의 특성을 파악하여 맞춤형 교정
- 장르/시대/문체를 고려한 지능형 처리
```

## 💡 혁신적 활용 사례

### 사례 1: 클래식 소설 처리
```
책: "레미제라블" (19세기 번역 소설)
GPT 분석: "고전문학, 문어체, 한자어 다수"
특화 규칙: 
- "되엿다" → "되었다" (구식 표기)
- "잇슴" → "있음" (옛 표기)
- "조선" → "조선" (고유명사 보호)
```

### 사례 2: 현대 기술서 처리
```
책: "딥러닝 실전 가이드"
GPT 분석: "기술서, 전문용어 다수, 영어 혼용"  
특화 규칙:
- "하이퍼파라미터" 단어 보호
- "epoch" → "epoch" (전문용어 보호)
- "데이즈셋" → "데이터셋" (기술 용어 교정)
```

### 사례 3: 학술 논문 처리  
```
책: "한국사 연구 논문집"
GPT 분석: "학술 문어체, 한자어/고유명사 다수"
특화 규칙:
- 인명/지명 자동 보호
- "~에 대하여" 문어체 보존  
- "~이다" → "~이다" (학술 문체 유지)
```

## ⚠️ 위험 요소 및 대응

### 주요 리스크
1. **GPT API 비용**: 책마다 분석 비용 발생
2. **품질 불안정**: GPT 응답의 일관성 문제
3. **오버엔지니어링**: 복잡성 증가로 인한 버그 위험

### 대응 방안
- **비용**: 캐싱 + 비슷한 책 재활용
- **품질**: Prompt engineering + 검증 시스템  
- **복잡성**: 단계적 도입 + A/B 테스트

## 🔄 다음 단계 연결

### Phase 3: Community Validation
- Book Bootstrap으로 생성된 교정 기준을 사용자들이 검증
- 동일 책 읽는 사용자들의 패턴 공유 및 개선

### Phase 4: Adaptive OCR Engine
- Book Bootstrap Engine의 분석 결과를 OCR 단계부터 활용
- 책 종류 예측을 통한 사전 최적화

---

**작성**: GitHub Copilot (Claude Sonnet 4)  
**업데이트**: 2026년 3월 2일 오후 9시  
**상태**: 설계 완료, Phase 1.8 완료 후 구현 예정  
**목표**: SnapTXT를 진정한 "책을 이해하는 OCR"로 진화 📚🚀