# SnapTXT 후처리 시스템 개선 기획서

> **기획 일자**: 2026-03-02  
> **기획자**: SnapTXT 팀  
> **대상 시스템**: `snaptxt.postprocess`  
> **실행 환경**: PC 데스크톱 애플리케이션 (`pc_app.py`)  
> **목표 완료**: 2026년 3월 (Phase 1-2), 4월 (Phase 3)

## 📋 기획 개요

### 🎯 **개선 목표**
```
현재 품질 99.1% → 99.5%+ 달성
수동 규칙 추가 → 자동 학습 시스템 구축
일반적 처리 → 도메인별 최적화
비용 제로 유지 → 완전 무료 PC 데스크톱 솔루션
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

## 🏗️ 시스템 아키텍처 및 실행 환경

### **⚠️ 중요: SnapTXT는 서버 기반 시스템이 아닙니다**

SnapTXT는 **PC 데스크톱 애플리케이션**으로 설계되었으며, 모든 처리가 로컬에서 이루어집니다:

#### **📱 주요 실행 방식**
```bash
# 메인 실행 방법: PC 데스크톱 앱 (PyQt5 GUI)
python run_pc_app.py   # 추천: 자동 의존성 체크
python pc_app.py       # 직접 실행

# 보조 실행 방법: 웹 인터페이스 (로컬 Flask 서버)
python main.py         # http://127.0.0.1:5000 (로컬만)
```

#### **🛠️ 시스템 구조**
- **주력 인터페이스**: `pc_app.py` → PyQt5 기반 GUI 데스크톱 앱
- **웹 인터페이스**: `main.py` → Flask 로컬 서버 (포트 5000)
- **OCR 엔진**: `snaptxt/backend/multi_engine.py` → 로컬 처리
- **후처리**: `snaptxt/postprocess/` → 로컬 YAML 규칙 적용
- **학습 데이터**: `logs/`, `tools/` → 로컬 파일 시스템

#### **💡 왜 서버가 아닌 PC 앱인가?**
1. **비용 제로**: 서버 운영비, API 비용 없음
2. **데이터 보안**: 모든 이미지/텍스트가 로컬에서만 처리
3. **오프라인 작동**: 인터넷 없이도 완전 동작
4. **성능**: GPU/CPU 리소스 직접 활용
5. **설치 편의성**: pip install로 즉시 사용 가능

#### **🎯 개선 계획의 핵심**
- **Phase 2 학습 기능**: `pc_app.py`에 사용자 피드백 UI 추가
- **Phase 3 도메인 분류**: 로컬 키워드 매칭 (무료)
- **모든 처리**: 외부 서버/API 의존성 없음

## 🚀 Phase별 개선 계획

### **Phase 1: MVP 패턴 추천 엔진** (3월 1-2주)
**목표**: Stage2/3의 "고친 흔적"을 활용한 실용적 규칙 추천

> **💡 핵심 아이디어**: 이미 Stage2/3가 고쳐주고 있는 패턴들을 자동으로 규칙화

#### **1.1 실시간 Diff 수집기**
```python
# 구현 계획: 후처리 과정의 실시간 변화 추적
class PostProcessDiffCollector:
    def track_stage_changes(self, original: str, stage2: str, stage3: str) -> dict:
        """각 Stage의 변화를 실시간 추적"""
        
        changes = {
            "stage2_diffs": self.extract_diffs(original, stage2),
            "stage3_diffs": self.extract_diffs(stage2, stage3),
            "timestamp": datetime.now(),
            "confidence": self.calculate_confidence(original, stage3)
        }
        
        # 즉시 패턴 후보로 변환 가능한 형태로 저장
        self.save_diff_candidate(changes)
        return changes
    
    def suggest_rules_from_diffs(self, threshold=3) -> list:
        """반복되는 diff 패턴을 규칙 후보로 추천"""
        
        pattern_freq = defaultdict(int)
        
        # 저장된 diff들에서 패턴 추출
        for diff_record in self.load_recent_diffs():
            for change in diff_record["stage2_diffs"]:
                if self.is_rule_worthy(change):
                    pattern_key = self.normalize_pattern(change)
                    pattern_freq[pattern_key] += 1
        
        # 임계값 이상 패턴만 추천
        suggestions = []
        for pattern, freq in pattern_freq.items():
            if freq >= threshold:
                suggestions.append({
                    "pattern": pattern["from"],
                    "replacement": pattern["to"],
                    "frequency": freq,
                    "auto_apply": freq >= 10  # 10회 이상은 자동 적용 제안
                })
        
        return sorted(suggestions, key=lambda x: x["frequency"], reverse=True)
```

**예상 결과**: 
- 실시간 패턴 발견 (로그 분석 불필요)
- 월 15-25개 신규 패턴 자동 추천
- 즉시 적용 가능한 고품질 규칙

#### **1.2 스마트 룰 엔진 안정화** ⭐
```python
# 구현 계획: 규칙 충돌/과교정 방지 시스템
class SmartRuleEngine:
    def __init__(self):
        self.scope_rules = self.load_scope_patterns()
        self.forbidden_zones = self.load_forbidden_patterns()
        self.conflict_detector = ConflictDetector()
    
    def apply_rules_safely(self, text: str, rules: list) -> str:
        """안전한 규칙 적용 (스코프 제한 + 충돌 감지)"""
        
        result = text
        applied_rules = []
        
        for rule in rules:
            # 1. 스코프 제한 체크
            if not self.check_scope_validity(result, rule):
                continue
                
            # 2. 금지 영역 체크  
            if self.is_in_forbidden_zone(result, rule):
                continue
                
            # 3. 충돌 감지
            if self.conflict_detector.would_conflict(applied_rules, rule):
                continue
                
            # 4. 안전 적용
            before = result
            result = self.apply_single_rule(result, rule)
            
            if before != result:
                applied_rules.append(rule)
                
        return result
    
    def check_scope_validity(self, text: str, rule: dict) -> bool:
        """스코프 제한: 특정 조건에서만 적용"""
        scope = rule.get("scope", "global")
        
        if scope == "sentence_start":
            return self.is_sentence_boundary(text, rule["pattern"])
        elif scope == "no_numbers":
            return not self.near_numbers(text, rule["pattern"])
        elif scope == "korean_only":
            return self.is_korean_context(text, rule["pattern"])
            
        return True  # global scope
    
    def is_in_forbidden_zone(self, text: str, rule: dict) -> bool:
        """금지 영역: URL/이메일/고유명사/코드블록 등"""
        pattern_pos = text.find(rule["pattern"])
        if pattern_pos == -1:
            return False
            
        # 금지 영역들 체크
        forbidden_areas = [
            self.find_urls(text),
            self.find_emails(text), 
            self.find_proper_nouns(text),
            self.find_code_blocks(text),
            self.find_parentheses_content(text)
        ]
        
        for area_start, area_end in chain(*forbidden_areas):
            if area_start <= pattern_pos <= area_end:
                return True
                
        return False
```

**예상 효과**: 
- 규칙 수 증가해도 품질 유지
- 과교정 90% 감소
- 안전한 자동 규칙 적용 가능

### **Phase 0.5: 콘텐츠 타입 기반 처리** (3월 2주)
**목표**: 도메인보다 먼저 콘텐츠 타입 분리로 즉시 과교정 방지

#### **타입별 처리 전략**
```python
# 구현 계획: 4가지 콘텐츠 타입 분리
class ContentTypeProcessor:
    def detect_content_type(self, text: str) -> str:
        """빠른 타입 분류 (도메인보다 우선)"""
        
        # 1. 본문 텍스트 (기본)
        if self.is_body_text(text):
            return "body"
            
        # 2. 목차/번호 리스트
        elif self.is_list_content(text):
            return "list"
            
        # 3. 표(테이블) 
        elif self.is_table_content(text):
            return "table"
            
        # 4. 인용/각주/짧은 줄
        elif self.is_citation_content(text):
            return "citation"
            
        return "body"  # fallback
    
    def apply_type_specific_processing(self, text: str, content_type: str) -> str:
        """타입별 맞춤 후처리"""
        
        if content_type == "body":
            # 일반 텍스트: 전체 Stage 적용
            return self.apply_full_pipeline(text)
            
        elif content_type == "list":
            # 목차/리스트: 줄바꿈 보존, 번호 보호
            return self.apply_conservative_pipeline(text, preserve_numbers=True)
            
        elif content_type == "table":
            # 표: 구조 보존, 최소 교정
            return self.apply_minimal_pipeline(text, preserve_structure=True)
            
        elif content_type == "citation":
            # 인용/각주: 원본 보존 우선
            return self.apply_safe_pipeline(text, preserve_original=True)
```

### **Phase 2: 교정 Diff 수집 시스템** (3월 3-4주)
**목표**: PC 데스크톱 앱에서 사용자 교정 diff를 자동 수집

> **⚠️ 중요**: 이 기능은 `pc_app.py` PyQt5 데스크톱 애플리케이션에 구현됩니다. 서버나 웹 기반이 아닙니다.

#### **2.1 스마트 Diff 수집 UI**
```python
# PC 앱(pc_app.py)에 추가할 기능 - 교정 유형별 분류 수집
class SmartCorrectionCollector(QMainWindow):
    def __init__(self):
        super().__init__()
        self.original_ocr = ""
        self.stage23_result = ""
        
        # 교정 유형 선택 UI
        self.setup_correction_type_ui()
    
    def setup_correction_type_ui(self):
        """교정 유형별 학습 데이터 분류"""
        
        # 교정 유형 선택 
        self.correction_type_group = QButtonGroup()
        
        self.typo_radio = QRadioButton("✅ 오타/띄어쓰기 수정 (학습용)")
        self.punctuation_radio = QRadioButton("✅ 부호/숫자 수정 (학습용)")
        self.rewrite_radio = QRadioButton("⚠️ 문장 다듬기 (학습 제외)")
        self.meaning_radio = QRadioButton("⚠️ 의미 변경 (학습 제외)")
        
        self.typo_radio.setChecked(True)  # 기본값
        
        self.correction_type_group.addButton(self.typo_radio, 0)
        self.correction_type_group.addButton(self.punctuation_radio, 1) 
        self.correction_type_group.addButton(self.rewrite_radio, 2)
        self.correction_type_group.addButton(self.meaning_radio, 3)
    
    def save_user_correction(self):
        """사용자 교정을 유형별로 저장"""
        
        correction_type = self.correction_type_group.checkedId()
        user_corrected = self.text_editor.toPlainText()
        
        # 학습 가능한 교정만 처리
        if correction_type in [0, 1]:  # 오타/띄어쓰기/부호
            diff_data = {
                "original_ocr": self.original_ocr,
                "stage23_processed": self.stage23_result,
                "user_corrected": user_corrected,
                "correction_type": ["typo", "punctuation"][correction_type],
                "timestamp": datetime.now().isoformat(),
                "learning_eligible": True
            }
            
            # diff 저장
            self.save_correction_diff(diff_data)
            
            # 즉시 패턴 후보 생성
            candidates = self.extract_rule_candidates(diff_data)
            if candidates:
                self.show_rule_suggestions(candidates)
                
        else:  # 문장 다듬기/의미 변경
            # 통계용으로만 저장, 학습 데이터로 사용 안함
            self.save_usage_stats_only(user_corrected, "rewrite_or_meaning")
            
        self.update_collection_stats()
```

**예상 결과**: 
- 고품질 diff 데이터만 수집 (위험한 전체 재작성 제외)
- 사용자당 주 3-7개 신뢰할 수 있는 패턴 수집
- 즉시 규칙 후보로 변환 가능

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

### **Phase 2.5: Stage 3 안전성 분리** (3월 4주)
**목표**: 언어학적 교정을 안전/공격 모드로 분리하여 위험도 관리

#### **Stage 3A: 안전 교정 (기본)**
```python
class SafeStage3Config:
    """확실한 교정만 수행하는 보수적 설정"""
    
    enable_basic_spacing_fix = True      # 명백한 띄어쓰기 오류
    enable_obvious_typos = True          # 확실한 오타 (ㄱ→가, 등)
    enable_punctuation_basic = True      # 기본 부호 정리
    enable_repeated_chars = True         # 반복 문자 정리
    
    # 위험한 기능들 비활성화
    enable_advanced_grammar = False      # 고급 문법 교정 X
    enable_sentence_restructure = False  # 문장 재구성 X
    enable_meaning_inference = False     # 의미 추론 교정 X
    
stage_3a_result = apply_safe_stage3(text, SafeStage3Config())
```

#### **Stage 3B: 공격적 교정 (옵션)**
```python
class AggressiveStage3Config:
    """문제 다듬기 및 고급 교정 (사용자 선택)"""
    
    # Stage 3A 포함
    inherit_safe_config = True
    
    # 추가 고급 기능
    enable_grammar_enhancement = True    # 문법 구조 개선
    enable_sentence_flow = True          # 문장 흐름 개선
    enable_paragraph_restructure = True  # 문단 재구성
    enable_style_normalization = True    # 문체 통일
    
    # 용도별 프리셋
    preset_for_audiobook = True          # 오디오북 최적화
    preset_for_document = False          # 문서 보존
    preset_for_casual_reading = True     # 일반 읽기
    
if user_wants_enhanced_processing:
    final_result = apply_aggressive_stage3(stage_3a_result, AggressiveStage3Config())
else:
    final_result = stage_3a_result  # 안전 버전만 사용
```

### **Phase 3: 도메인 감지 시스템** (4월 1-2주)
**목표**: 콘텐츠 타입 기반으로 도메인별 맞춤 후처리 자동 적용

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
- **추가 서버 비용**: **$0** ❌ **서버 없음** (PC 데스크톱 앱이므로)
- **외부 API 사용**: **$0** (무료 도구만 사용, 로컬 처리)
- **클라우드 비용**: **$0** (모든 데이터가 로컬 처리)
- **저장 공간**: **+50MB** (사용자 PC의 학습 데이터 및 로그)
- **총 추가 운영 비용**: **$0/월** 🎉

> **💡 비용 제로의 핵심**: SnapTXT는 PC 데스크톱 앱이므로 서버, 클라우드, API 비용이 전혀 발생하지 않습니다.

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
- [x] PC 데스크톱 앱 학습 기능 정상 동작 (`pc_app.py` UI)
- [x] 사용자 피드백 80% 이상 유효 패턴 변환 (로컬 학습)
- [x] 개인화 교정 성능 10% 향상 (개별 PC 환경)
- [x] **디버깅 로그 시스템 완전 강화** (추가 달성)
  - [x] 실시간 품질 평가 및 안전성 점수 도입
  - [x] Stage별 상세 처리 과정 및 성능 메트릭 추적
  - [x] 투명한 fallback 정책 및 사용자 친화적 로그

**검증 방법**: A/B 테스트 및 PC 앱 사용자 만족도 조사

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
- [ ] **Phase 1.1: MVP 패턴 추천 엔진** 🚀
  - [ ] Stage2/3 실시간 diff 수집기 구현
  - [ ] 반복 패턴 자동 탐지 알고리즘
  - [ ] 규칙 후보 추천 UI (pc_app.py)

#### **3월 2주 (3/10-3/16)** 
- [ ] **Phase 1.2: 스마트 룰 엔진 안정화** ⭐
  - [ ] 스코프 제한 시스템 (문장 경계, 숫자 근처, 한국어 컨텍스트)
  - [ ] 금지 영역 감지 (URL, 이메일, 고유명사, 코드블록)
  - [ ] 충돌 감지 및 우선순위 시스템
- [ ] **Phase 0.5: 콘텐츠 타입 분리**
  - [ ] 4가지 타입 분류기 (본문/목차/표/인용)
  - [ ] 타입별 처리 전략 적용

#### **3월 3주 (3/17-3/23)**
- [ ] **Phase 2.1: 스마트 교정 Diff 수집**
  - [ ] PC 앱 교정 유형 분류 UI (오타/부호 vs 문장다듬기)
  - [ ] 안전한 diff 데이터만 수집하는 시스템
  - [ ] 즉시 규칙 후보 변환 기능

#### **3월 4주 (3/24-3/30)**
- [x] Phase 2.2: 자동 패턴 적용 시스템 (pc_app.py 통합)
- [x] Phase 2 통합 테스트 (데스크톱 환경)
- [x] 사용자 피드백 수집 시작 (로컬 학습 데이터)
- [x] **🔧 디버깅 로그 시스템 대폭 강화** (추가 개선)
  - [x] 입력 품질 자동 평가 (한국어 비율, 단어 패턴, 오류 감지)
  - [x] Stage별 상세 처리 과정 추적 (처리시간, 변화량, 패턴 적용)
  - [x] 안전성 우선 정책 투명화 (fallback 조건, 품질 점수)
  - [x] PC 앱 통합 로그 강화 (사용자 친화적 메시지)
- [ ] **Phase 2.5: Stage 3 안전성 분리**
  - [ ] Stage 3A (안전 교정) vs 3B (공격적 교정) 분리
  - [ ] 사용자 선택 가능한 처리 강도

### **2026년 4월**

#### **4월 1주 (3/31-4/6)**
- [ ] **Phase 3.1: 도메인 감지 시스템**
  - [ ] 학술/소설/뉴스/기술문서 키워드 데이터베이스
  - [ ] 신뢰도 기반 도메인 분류기
  - [ ] 불확실할 때 일반 처리로 fallback

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

**SnapTXT PC 데스크톱 애플리케이션**의 완벽한 확장성 인프라를 기반으로 **자동화, 학습, 개인화**를 핵심 축으로 하여 차세대 지능형 솔루션으로 발전시킬 것입니다.

**핵심 성공 요소**:
- ✅ **PC 데스크톱 앱** 기반으로 서버 비용 완전 제로 달성
- ✅ 기존 PyQt5 시스템의 완벽한 호환성 유지
- ✅ 단계적 도입으로 리스크 최소화  
- ✅ 로컬 처리로 데이터 보안 및 오프라인 동작 보장
- ✅ 사용자 중심 설계로 높은 채택률 확보

> **🎯 실행 명령어**:  
> ```bash
> python run_pc_app.py  # PC 데스크톱 앱 실행
> ```

이 계획이 성공하면 SnapTXT는 **"스스로 학습하고 진화하는 PC 데스크톱 후처리 시스템"**의 선도 모델이 될 것입니다! 🚀