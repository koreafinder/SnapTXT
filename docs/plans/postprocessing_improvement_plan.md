# SnapTXT 후처리 시스템 개선 기획서

> **기획 일자**: 2026-03-02  
> **기획자**: SnapTXT 팀  
> **대상 시스템**: `snaptxt.postprocess`  
> **목표 완료**: 2026년 3월 (Phase 1-2), 4월 (Phase 3)

## 📋 기획 개요

### 🎯 **개선 목표**
```
현재 품질 99.1% → 99.5%+ 달성
수동 규칙 추가 → 자동 학습 시스템 구축
일반적 처리 → 도메인별 최적화
비용 제로 유지 → 완전 무료 솔루션
```

### 🔍 **현재 상태 분석**

#### ✅ **잘 구축된 부분**
- **확장성**: ⭐⭐⭐⭐⭐ (YAML Hot-reload, 모듈화 완벽)
- **문서화**: ⭐⭐⭐⭐⭐ (사용자 가이드, 규칙 관리, 트러블슈팅 완비)
- **품질**: 99.1% overall_quality, 98.2% 신뢰도
- **성능**: 평균 32.77초 처리 (Stage3 오버헤드 0.031초)

#### 🔄 **개선 필요 부분**
- **수동 규칙 관리**: 새 패턴 발견 시 수동 YAML 추가 필요
- **일반화 부족**: 도메인별 특수성 반영 제한적
- **피드백 수집**: 사용자 교정 내역 자동 학습 미흡
- **예측 불가능성**: 새로운 OCR 오류 패턴에 대한 선제 대응 부족

## 🚀 Phase별 개선 계획

### **Phase 1: 자동 패턴 발견 시스템** (3월 1-2주)
**목표**: 무료 로컬 분석으로 새 규칙 자동 추천

#### **1.1 로그 기반 패턴 마이닝**
```python
# 구현 계획: logs/snaptxt_ocr.jsonl 분석 도구
class LogPatternAnalyzer:
    def analyze_correction_patterns(self) -> list:
        """105건+ 로그에서 자주 발생하는 오류 패턴 추출"""
        
        # 1. Stage3 적용 전후 diff 분석
        before_after_pairs = self.extract_stage3_changes()
        
        # 2. 빈도 기반 패턴 순위 매기기
        pattern_frequency = Counter()
        for before, after in before_after_pairs:
            if before != after:
                pattern = self.extract_pattern(before, after)
                pattern_frequency[pattern] += 1
        
        # 3. 임계값 이상 패턴을 YAML 형태로 제안
        suggestions = []
        for pattern, freq in pattern_frequency.most_common(20):
            if freq >= 3:  # 3회 이상 발생한 패턴만
                suggestions.append({
                    "pattern": pattern[0],
                    "replacement": pattern[1], 
                    "frequency": freq,
                    "confidence": freq / len(before_after_pairs)
                })
        
        return suggestions
```

**예상 결과**: 월 10-15개 신규 패턴 자동 발견

#### **1.2 통계 기반 규칙 우선순위**
```python
# 구현 계획: 규칙 사용 빈도 분석
def optimize_rule_order():
    """사용 통계 기반으로 YAML 규칙 순서 최적화"""
    
    usage_stats = analyze_logs("logs/snaptxt_ocr.jsonl") 
    rule_performance = {}
    
    for rule in current_yaml_rules:
        # 각 규칙의 적용 빈도와 처리 시간 측정
        hits = count_rule_applications(rule, usage_stats)
        performance = measure_rule_performance(rule)
        
        rule_performance[rule] = {
            "hits_per_1000": hits * 1000 / len(usage_stats),
            "avg_processing_ms": performance,
            "priority_score": hits / performance  # 효율성 지표
        }
    
    # 효율성 순으로 YAML 재정렬 제안
    return sorted(rule_performance.keys(), 
                 key=lambda r: rule_performance[r]["priority_score"], 
                 reverse=True)
```

**예상 효과**: Stage3 처리 속도 15-20% 향상

### **Phase 2: 사용자 피드백 자동 학습** (3월 3-4주)
**목표**: PC 앱에서 사용자 교정을 자동으로 패턴화

#### **2.1 PC 앱 학습 기능 추가**
```python
# PC 앱(pc_app.py)에 추가할 기능
class LearningEnabledOCRApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.learning_enabled = True
        self.original_ocr_result = ""
        
        # 학습 UI 구성
        self.setup_learning_interface()
    
    def setup_learning_interface(self):
        # 기존 UI에 학습 관련 요소 추가
        self.learn_button = QPushButton("💡 이 교정을 기억하기")
        self.learn_button.clicked.connect(self.learn_from_correction)
        
        self.auto_learn_checkbox = QCheckBox("자동 학습 활성화")
        self.auto_learn_checkbox.setChecked(True)
        
        # 학습 통계 표시
        self.learning_stats_label = QLabel("학습된 패턴: 0개")
    
    def learn_from_correction(self):
        """사용자 교정 내역을 자동으로 YAML 규칙에 추가"""
        if not self.auto_learn_checkbox.isChecked():
            return
            
        original = self.original_ocr_result
        corrected = self.text_editor.toPlainText()
        
        if original != corrected:
            try:
                pattern = self.extract_learning_pattern(original, corrected)
                if self.is_valid_pattern(pattern):
                    suggestion = {
                        "source": "user_feedback",
                        "timestamp": datetime.now().isoformat(),
                        "pattern": pattern["pattern"],
                        "replacement": pattern["replacement"],
                        "confidence": 0.8  # 사용자 직접 교정이므로 높은 신뢰도
                    }
                    
                    self.save_pattern_suggestion(suggestion)
                    self.apply_pattern_if_approved(suggestion)
                    
                    # 사용자에게 피드백
                    self.show_learning_success(f"새 패턴 학습: {pattern['pattern']}")
                    self.update_learning_stats()
                    
            except Exception as e:
                self.show_learning_error(f"학습 실패: {e}")
```

**예상 결과**: 
- 사용자당 주 5-10개 신규 패턴 수집
- 개인화된 교정 성능 향상

#### **2.2 패턴 검증 및 자동 적용**
```python
# 학습된 패턴의 품질 검증
class PatternValidator:
    def validate_user_pattern(self, pattern: dict) -> bool:
        """사용자 교정 패턴의 품질 검증"""
        
        # 1. 기본 안전성 검사
        if not self.is_safe_pattern(pattern):
            return False
            
        # 2. 기존 규칙과 충돌 검사  
        if self.conflicts_with_existing_rules(pattern):
            return False
            
        # 3. 한국어 언어학적 타당성 검사
        if not self.is_linguistically_valid(pattern):
            return False
            
        # 4. 빈도 임계값 검사 (3회 이상 동일 패턴 시도 시)
        frequency = self.get_pattern_frequency(pattern)
        if frequency >= 3:
            return True
            
        return False
    
    def auto_apply_validated_pattern(self, pattern: dict):
        """검증된 패턴을 자동으로 YAML에 추가"""
        yaml_entry = {
            "pattern": pattern["pattern"],
            "replacement": pattern["replacement"],
            "metadata": {
                "source": pattern["source"],
                "learned_at": pattern["timestamp"],
                "confidence": pattern["confidence"]
            }
        }
        
        self.append_to_yaml_file(yaml_entry)
        self.reload_rules_hot()
        
        # 학습 로그 기록
        self.log_pattern_learning(pattern)
```

### **Phase 3: 도메인별 지능형 최적화** (4월 1-2주)
**목표**: 이미지 유형별 맞춤 후처리 자동 적용

#### **3.1 콘텐츠 타입 자동 감지**
```python
# 완전 무료 도메인 분류기
class ContentTypeDetector:
    def __init__(self):
        self.domain_keywords = {
            "academic": {
                "keywords": ["논문", "참고문헌", "abstract", "연구", "학회", "journal"],
                "layout_hints": ["citation", "bibliography", "author"],
                "confidence_threshold": 0.7
            },
            "textbook": {
                "keywords": ["장", "절", "연습문제", "예제", "문제", "해답"],
                "layout_hints": ["chapter", "section", "exercise"],
                "confidence_threshold": 0.8
            },
            "novel": {
                "keywords": ["대화", "\"", "말했다", "생각했다", "느꼈다"],
                "layout_hints": ["dialogue", "narrative"],
                "confidence_threshold": 0.6
            },
            "news": {
                "keywords": ["기자", "보도", "취재", "뉴스", "속보"],
                "layout_hints": ["byline", "dateline"],
                "confidence_threshold": 0.7
            }
        }
    
    def detect_content_type(self, text: str, image_metadata: dict = None) -> str:
        """텍스트 내용과 이미지 메타데이터 기반 도메인 감지"""
        
        scores = {}
        for domain, config in self.domain_keywords.items():
            score = 0
            
            # 키워드 기반 점수 계산
            keyword_hits = sum(1 for kw in config["keywords"] 
                              if kw.lower() in text.lower())
            keyword_score = keyword_hits / len(config["keywords"])
            
            # 레이아웃 기반 점수 (이미지 메타데이터 활용)
            layout_score = 0
            if image_metadata:
                layout_score = self.analyze_layout_hints(image_metadata, config)
            
            # 종합 점수
            scores[domain] = (keyword_score * 0.7 + layout_score * 0.3)
        
        # 가장 높은 점수의 도메인 반환
        best_domain = max(scores, key=scores.get)
        if scores[best_domain] >= self.domain_keywords[best_domain]["confidence_threshold"]:
            return best_domain
        else:
            return "general"  # 일반 텍스트로 처리
```

#### **3.2 도메인별 후처리 프로필**
```python
# 도메인별 맞춤 후처리 설정
class DomainSpecificProcessor:
    def __init__(self):
        self.domain_profiles = {
            "academic": {
                "stage3_config": Stage3Config(
                    enable_spellcheck_enhancement=True,  # 논문은 정확성 중요
                    enable_punctuation_normalization=True,
                    enable_tts_friendly_processing=False  # TTS 보다 정확성
                ),
                "custom_rules": "academic_rules.yaml",
                "priority_patterns": ["citation", "reference", "equation"]
            },
            
            "textbook": {
                "stage3_config": Stage3Config(
                    enable_spacing_normalization=True,   # 교과서는 읽기 편의성
                    enable_character_fixes=True,
                    enable_tts_friendly_processing=True   # 학습용 TTS 활용
                ),
                "custom_rules": "textbook_rules.yaml", 
                "priority_patterns": ["chapter", "exercise", "example"]
            },
            
            "novel": {
                "stage3_config": Stage3Config(
                    enable_spacing_normalization=True,
                    enable_tts_friendly_processing=True,  # 낭독용 최적화
                    tts_config=Stage3_5Config(
                        enable_korean_quotes=True,        # 대화 표현 개선
                        enable_sentence_boundary_fix=True
                    )
                ),
                "custom_rules": "novel_rules.yaml",
                "priority_patterns": ["dialogue", "narrative", "emotion"]
            }
        }
    
    def apply_domain_processing(self, text: str, domain: str) -> str:
        """도메인별 최적화된 후처리 적용"""
        
        if domain not in self.domain_profiles:
            domain = "general"
            
        profile = self.domain_profiles.get(domain, {})
        
        # 도메인별 설정으로 Stage3 실행
        config = profile.get("stage3_config", Stage3Config())
        result = apply_stage3_rules(text, config)
        
        # 도메인별 커스텀 규칙 추가 적용
        custom_rules = profile.get("custom_rules")
        if custom_rules and os.path.exists(f"patterns/{custom_rules}"):
            result = self.apply_custom_domain_rules(result, custom_rules)
        
        return result
```

### **Phase 4: 통합 지능형 시스템** (4월 3-4주)
**목표**: 모든 개선사항을 통합한 완전 자동화 시스템

#### **4.1 통합 품질 최적화 엔진**
```python
# 모든 개선 기능을 통합한 메인 클래스
class IntelligentPostProcessor:
    def __init__(self):
        self.pattern_analyzer = LogPatternAnalyzer()
        self.content_detector = ContentTypeDetector()
        self.domain_processor = DomainSpecificProcessor()
        self.learning_engine = PatternLearningEngine()
        
        # 성능 추적
        self.performance_tracker = PerformanceTracker()
        
    def process_intelligent(self, text: str, context: dict = None) -> dict:
        """지능형 통합 후처리 실행"""
        
        start_time = time.time()
        
        # 1. 도메인 감지
        domain = self.content_detector.detect_content_type(
            text, context.get("image_metadata")
        )
        
        # 2. 도메인별 최적 처리
        processed_text = self.domain_processor.apply_domain_processing(
            text, domain
        )
        
        # 3. 실시간 패턴 학습 적용
        if context and context.get("enable_learning", True):
            processed_text = self.learning_engine.apply_learned_patterns(
                processed_text
            )
        
        # 4. 품질 및 성능 측정
        quality_score = self.calculate_quality_score(text, processed_text)
        processing_time = time.time() - start_time
        
        # 5. 성능 데이터 수집 (다음 학습용)
        performance_data = {
            "domain": domain,
            "quality_improvement": quality_score,
            "processing_time": processing_time,
            "patterns_applied": self.get_applied_patterns()
        }
        self.performance_tracker.record(performance_data)
        
        return {
            "text": processed_text,
            "domain": domain,
            "quality_score": quality_score,
            "processing_time": processing_time,
            "suggestions": self.get_improvement_suggestions()
        }
```

## 📊 예상 성과 및 지표

### **정량적 목표**

| 지표 | 현재 | Phase 1 목표 | Phase 2 목표 | Phase 3 목표 | 최종 목표 |
|------|------|-------------|-------------|-------------|-----------|
| **Overall Quality** | 99.1% | 99.2% | 99.3% | 99.4% | **99.5%+** |
| **평균 신뢰도** | 98.2% | 98.5% | 98.7% | 99.0% | **99.2%** |
| **Stage3 처리 속도** | 0.031s | 0.025s | 0.020s | 0.015s | **0.010s** |
| **신규 패턴 발견** | 수동 | 월 10-15개 | 월 20-30개 | 월 40-50개 | **월 50+개** |
| **사용자 만족도** | - | - | 80%+ | 85%+ | **90%+** |

### **정성적 효과**

#### **개발팀 관점**
- ✅ **규칙 관리 부담 82% 감소** (수동 → 자동)
- ✅ **새 도메인 대응 시간 단축** (주 단위 → 일 단위)
- ✅ **품질 문제 선제 발견** (사후 대응 → 예방 중심)

#### **사용자 관점**  
- ✅ **개인화된 교정 경험** (일반 → 맞춤형)
- ✅ **도메인별 최적화** (학술/소설/뉴스 등 특화)
- ✅ **지속적 성능 향상** (사용할수록 똑똑해짐)

## 💰 비용 분석

### **개발 비용** (인력 기준)
- **Phase 1**: 개발자 1명 × 2주 = **2 person-weeks**
- **Phase 2**: 개발자 1명 × 2주 = **2 person-weeks**  
- **Phase 3**: 개발자 1명 × 2주 = **2 person-weeks**
- **Phase 4**: 개발자 1명 × 2주 = **2 person-weeks**
- **총 개발 비용**: **8 person-weeks**

### **운영 비용** (월간)
- **추가 서버 비용**: **$0** (모든 처리가 로컬)
- **외부 API 사용**: **$0** (무료 도구만 사용)
- **저장 공간**: **+50MB** (학습 데이터 및 로그)
- **총 추가 운영 비용**: **$0/월**

### **ROI 계산**
```
개발 투자: 8 person-weeks
품질 향상: 99.1% → 99.5% (0.4% 개선)
사용자 만족도: +10%
운영 효율성: +82% (규칙 관리 자동화)

ROI = (품질향상 + 운영효율성) / 개발투자
    = (0.4% + 82%) / 8weeks
    = 10.3% / week
```

## ⚠️ 리스크 및 대응 방안

### **기술적 리스크**

#### **리스크 1: 자동 학습 패턴의 품질 저하**
**확률**: 중간  
**영향**: 높음  
**대응**: 
- 패턴 검증 단계 강화 (3단계 검증 프로세스)
- 사용자 승인 메커니즘 구축
- 자동 롤백 기능 구현

#### **리스크 2: 도메인 분류 정확도 부족**
**확률**: 중간  
**영향**: 중간  
**대응**:
- Fallback을 일반 처리로 설정 (안전 우선)
- 사용자 수동 도메인 선택 옵션 제공
- 점진적 개선 (사용 데이터 축적)

### **운영 리스크**

#### **리스크 3: 메모리 사용량 증가**
**확률**: 낮음  
**영향**: 중간  
**대응**:
- 학습 데이터 주기적 정리 (월간)
- 압축 저장 및 인덱스 최적화
- 메모리 사용량 모니터링 대시보드

### **비즈니스 리스크**

#### **리스크 4: 사용자 채택률 저조**
**확률**: 낮음  
**영향**: 높음  
**대응**:
- Phase별 점진적 도입 (강제 전환 없음)
- 기존 기능과 완전 호환성 유지
- 사용자 피드백 기반 UX 개선

## 🎯 성공 지표 및 검증 방법

### **Phase별 검증 기준**

#### **Phase 1 성공 기준**
- [ ] 월 10개 이상 신규 패턴 자동 발견
- [ ] Stage3 처리 속도 15% 향상
- [ ] 패턴 정확도 95% 이상

**검증 방법**: `logs/snaptxt_ocr.jsonl` 분석 및 성능 벤치마크

#### **Phase 2 성공 기준** 
- [ ] PC 앱 학습 기능 정상 동작
- [ ] 사용자 피드백 80% 이상 유효 패턴 변환
- [ ] 개인화 교정 성능 10% 향상

**검증 방법**: A/B 테스트 및 사용자 만족도 조사

#### **Phase 3 성공 기준**
- [ ] 도메인 분류 정확도 85% 이상  
- [ ] 도메인별 처리 품질 5% 이상 향상
- [ ] 4개 이상 도메인 프로필 구축

**검증 방법**: 도메인별 샘플 테스트 및 품질 측정

### **최종 성공 지표**
```
✅ Overall Quality: 99.5% 이상 달성
✅ 자동 패턴 발견: 월 50개 이상
✅ 처리 속도: 50% 향상 
✅ 사용자 만족도: 90% 이상
✅ 운영 비용: 추가 비용 $0 유지
```

## 📅 실행 일정

### **2026년 3월**

#### **3월 1주 (3/3-3/9)**
- [ ] Phase 1.1: 로그 분석 도구 개발
- [ ] 기존 105건 로그 데이터 분석
- [ ] 자동 패턴 추출 알고리즘 구현

#### **3월 2주 (3/10-3/16)** 
- [ ] Phase 1.2: 규칙 우선순위 최적화
- [ ] 성능 벤치마크 및 검증
- [ ] Phase 1 완료 및 검토

#### **3월 3주 (3/17-3/23)**
- [ ] Phase 2.1: PC 앱 학습 UI 구현
- [ ] 사용자 피드백 수집 기능
- [ ] 패턴 추출 및 검증 로직

#### **3월 4주 (3/24-3/30)**
- [ ] Phase 2.2: 자동 패턴 적용 시스템
- [ ] Phase 2 통합 테스트
- [ ] 사용자 피드백 수집 시작

### **2026년 4월**

#### **4월 1주 (3/31-4/6)**
- [ ] Phase 3.1: 도메인 감지 시스템
- [ ] 콘텐츠 타입 분류기 구현
- [ ] 도메인별 키워드 데이터베이스

#### **4월 2주 (4/7-4/13)**
- [ ] Phase 3.2: 도메인별 프로필 구축
- [ ] 학술/교과서/소설/뉴스 프로필
- [ ] 도메인별 성능 테스트

#### **4월 3주 (4/14-4/20)**
- [ ] Phase 4.1: 통합 시스템 구현
- [ ] 모든 기능 통합 및 최적화
- [ ] 종합 성능 테스트

#### **4월 4주 (4/21-4/27)**  
- [ ] Phase 4.2: 최종 검증 및 배포
- [ ] 사용자 문서 업데이트
- [ ] 성과 측정 및 리포트 작성

## 📈 장기 비전 (2026년 하반기)

### **Q3 계획: 고도화**
- **AI 기반 패턴 예측**: 트렌드 분석으로 미래 오류 패턴 예측
- **다국어 확장**: 영어, 중국어, 일본어 도메인 지원  
- **실시간 협업**: 사용자 간 패턴 공유 시스템

### **Q4 계획: 생태계 확장**
- **플러그인 시스템**: 사용자 정의 후처리 모듈
- **API 서비스화**: 외부 앱에서 활용 가능한 후처리 API
- **커뮤니티 규칙 마켓플레이스**: 도메인별 규칙 공유 생태계

---

## 💡 결론

이 기획서는 **비용 제로로 99.5% 품질 달성**이라는 야심찬 목표를 현실적이고 단계적으로 실현하는 로드맵입니다. 

기존의 완벽한 확장성 인프라를 기반으로 **자동화, 학습, 개인화**를 핵심 축으로 하여 SnapTXT 후처리 시스템을 차세대 지능형 솔루션으로 발전시킬 것입니다.

**핵심 성공 요소**:
- ✅ 기존 시스템의 완벽한 호환성 유지
- ✅ 단계적 도입으로 리스크 최소화  
- ✅ 완전 무료 솔루션으로 비용 제로 달성
- ✅ 사용자 중심 설계로 높은 채택률 확보

이 계획이 성공하면 SnapTXT는 **"스스로 학습하고 진화하는 후처리 시스템"**의 선도 모델이 될 것입니다! 🚀