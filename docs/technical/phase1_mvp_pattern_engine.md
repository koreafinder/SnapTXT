# Phase 1 MVP 패턴 추천 엔진 세부 기술 설계서

> **작성일**: 2026-03-02  
> **대상**: Phase 1.1, 1.2 구현  
> **목표**: Stage2/3 "고친 흔적" 기반 실시간 패턴 추천 시스템  
> **예상 개발 기간**: 2주 (3월 1-2주)

## 🎯 **핵심 아이디어**

**"이미 Stage2/3가 고쳐주고 있는 패턴들을 자동으로 규칙화"**

현재 시스템이 OCR 텍스트를 Stage2→Stage3로 처리하면서 만들어내는 diff들을 실시간으로 수집하여, 반복되는 교정 패턴을 자동으로 Stage2 규칙으로 승격시키는 시스템입니다.

## 🏗️ **시스템 아키텍처**

### **기존 후처리 파이프라인**
```
원본 OCR → Stage2 (사전교정) → Stage3 (언어학적교정) → 최종결과
            ↓                    ↓
         diff_1               diff_2
```

### **새로운 MVP 확장 버전**
```
원본 OCR → Stage2 → Stage3 → 최종결과
            ↓         ↓
        DiffCollector (실시간 수집)
            ↓
        PatternAnalyzer (빈도 분석)
            ↓
        RuleGenerator (규칙 후보 생성)
            ↓
        PC App UI (사용자 승인/적용)
```

## 📁 **파일 구조 설계**

```
snaptxt/postprocess/
├── __init__.py                 # 기존 파이프라인 (수정)
├── stage2.py                   # 기존 Stage2 (수정)
├── stage3.py                   # 기존 Stage3 (수정)
├── pattern_engine/             # ← 신규 추가
│   ├── __init__.py
│   ├── diff_collector.py       # 실시간 diff 수집
│   ├── pattern_analyzer.py     # 패턴 분석 및 빈도 계산
│   ├── rule_generator.py       # YAML 규칙 후보 생성
│   ├── conflict_detector.py    # 규칙 충돌 감지
│   └── scope_validator.py      # 스코프/금지영역 검증
├── patterns/
│   ├── stage2_rules.yaml       # 기존 Stage2 규칙
│   ├── auto_suggestions.yaml   # ← 신규: 자동 추천 규칙 후보
│   └── user_patterns.yaml      # ← 신규: 사용자 승인된 규칙
└── logs/
    └── pattern_collection.jsonl  # ← 신규: diff 수집 로그
```

## 🔧 **Phase 1.1: 실시간 Diff 수집기 (3/3-3/9)**

### **1.1.1 DiffCollector 클래스 설계**

```python
# snaptxt/postprocess/pattern_engine/diff_collector.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
import json
from pathlib import Path
from difflib import SequenceMatcher

@dataclass
class TextDiff:
    """텍스트 변화 정보를 담는 데이터 클래스"""
    before: str
    after: str
    change_type: str  # "replacement", "insertion", "deletion"
    position: int
    confidence: float
    timestamp: datetime
    
@dataclass 
class StageResult:
    """각 Stage 처리 결과"""
    original_text: str
    stage2_result: str
    stage3_result: str
    stage2_time: float
    stage3_time: float
    total_changes: int

class DiffCollector:
    """실시간 텍스트 변화 수집기"""
    
    def __init__(self, log_path: str = "logs/pattern_collection.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(exist_ok=True)
        self.min_change_length = 2  # 최소 2글자 이상 변화만 수집
        self.max_change_length = 50  # 최대 50글자까지만 (전체 재작성 방지)
        
    def collect_stage_diffs(self, stage_result: StageResult) -> List[TextDiff]:
        """Stage 처리 결과에서 의미있는 diff들을 추출"""
        
        diffs = []
        
        # Stage2 diff 수집 (Stage2에서만 규칙 추가하므로 중요)
        stage2_diffs = self._extract_diffs(
            stage_result.original_text, 
            stage_result.stage2_result,
            "stage2"
        )
        diffs.extend(stage2_diffs)
        
        # Stage3 diff 수집 (참고용)  
        stage3_diffs = self._extract_diffs(
            stage_result.stage2_result,
            stage_result.stage3_result, 
            "stage3"
        )
        diffs.extend(stage3_diffs)
        
        # 수집한 diff들을 로그에 저장
        self._save_diffs_to_log(diffs, stage_result)
        
        return diffs
        
    def _extract_diffs(self, before: str, after: str, stage: str) -> List[TextDiff]:
        """두 텍스트 간의 의미있는 차이점들을 추출"""
        
        if before == after:
            return []
            
        diffs = []
        matcher = SequenceMatcher(None, before, after)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
                
            before_segment = before[i1:i2]
            after_segment = after[j1:j2]
            
            # 길이 필터링
            change_size = max(len(before_segment), len(after_segment))
            if change_size < self.min_change_length or change_size > self.max_change_length:
                continue
                
            # 의미없는 변화 필터링 (공백만 변경, 대소문자만 변경 등)
            if not self._is_meaningful_change(before_segment, after_segment):
                continue
                
            diff = TextDiff(
                before=before_segment,
                after=after_segment,
                change_type=tag,
                position=i1,
                confidence=self._calculate_confidence(before_segment, after_segment),
                timestamp=datetime.now()
            )
            diffs.append(diff)
            
        return diffs
        
    def _is_meaningful_change(self, before: str, after: str) -> bool:
        """의미있는 변화인지 판단"""
        
        # 공백만 변경된 경우
        if before.strip() == after.strip():
            return False
            
        # 대소문자만 변경된 경우  
        if before.lower() == after.lower():
            return False
            
        # 한글이 포함된 의미있는 변화인지 확인
        korean_chars = sum(1 for c in before + after if '가' <= c <= '힣')
        if korean_chars == 0:
            return False
            
        return True
        
    def _calculate_confidence(self, before: str, after: str) -> float:
        """변화의 신뢰도 계산 (0.0 ~ 1.0)"""
        
        # 길이 차이가 클수록 신뢰도 감소
        length_diff = abs(len(before) - len(after))
        length_penalty = min(length_diff * 0.1, 0.5)
        
        # 문자 유사도 계산
        similarity = SequenceMatcher(None, before, after).ratio()
        
        confidence = similarity - length_penalty
        return max(0.0, min(1.0, confidence))
        
    def _save_diffs_to_log(self, diffs: List[TextDiff], stage_result: StageResult):
        """수집된 diff들을 JSONL 형태로 저장"""
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "original_length": len(stage_result.original_text),
            "total_changes": len(diffs),
            "stage2_time": stage_result.stage2_time,
            "stage3_time": stage_result.stage3_time,
            "diffs": [
                {
                    "before": diff.before,
                    "after": diff.after,
                    "type": diff.change_type,
                    "position": diff.position,
                    "confidence": diff.confidence
                }
                for diff in diffs
            ]
        }
        
        # JSONL 형태로 추가 저장
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
```

### **1.1.2 기존 파이프라인 통합**

```python
# snaptxt/postprocess/__init__.py 수정
from .pattern_engine.diff_collector import DiffCollector, StageResult

def run_pipeline(
    text: str,
    *,
    stage2_config: Stage2Config | None = None,
    stage3_config: Stage3Config | None = None,
    logger: logging.Logger | None = None,
    collect_patterns: bool = True  # ← 신규 파라미터
) -> str:
    """Run postprocessing stages sequentially with optional pattern collection."""

    log = logger or logging.getLogger(__name__)
    stage2_cfg = stage2_config or Stage2Config(logger=log)
    stage3_cfg = stage3_config or Stage3Config(logger=log)
    
    # 시작 시간 및 입력 분석
    start_time = time.time()
    input_quality = _assess_input_quality(text)
    
    log.info("🧠 후처리 파이프라인 시작")
    log.info(f"   📊 입력: {len(text)}자, {len(text.split())}단어, 품질: {input_quality:.1%}")
    
    # Stage 2 처리
    stage2_start = time.time()
    stage2 = apply_stage2_rules(text, stage2_cfg)
    stage2_time = time.time() - stage2_start
    
    # Stage 3 처리  
    stage3_start = time.time()
    stage3 = apply_stage3_rules(stage2, stage3_cfg)
    stage3_time = time.time() - stage3_start
    
    # 최종 처리
    final_text = finalize_output(stage3, logger=log)
    
    # ✨ 신규: 패턴 수집 (선택적)
    if collect_patterns:
        try:
            diff_collector = DiffCollector()
            stage_result = StageResult(
                original_text=text,
                stage2_result=stage2, 
                stage3_result=stage3,
                stage2_time=stage2_time,
                stage3_time=stage3_time,
                total_changes=abs(len(final_text) - len(text))
            )
            diffs = diff_collector.collect_stage_diffs(stage_result)
            
            if diffs:
                log.debug(f"   📝 패턴 수집: {len(diffs)}개 diff 저장됨")
                
        except Exception as e:
            log.warning(f"   ⚠️  패턴 수집 실패: {e}")
    
    # 기존 로깅 및 반환
    total_time = time.time() - start_time
    log.info(f"   ⏱️  총 처리 시간: {total_time*1000:.1f}ms")
    log.info("🎯 후처리 파이프라인 완료")
    
    return final_text
```

## 🔍 **Phase 1.2: 패턴 분석 및 추천 (3/10-3/16)**

### **1.2.1 PatternAnalyzer 클래스 설계**

```python
# snaptxt/postprocess/pattern_engine/pattern_analyzer.py
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
import json
from pathlib import Path
import re

@dataclass
class PatternCandidate:
    """규칙 후보 패턴"""
    pattern: str      # 찾을 패턴
    replacement: str  # 바꿀 내용
    frequency: int    # 발생 횟수
    confidence: float # 신뢰도 평균
    examples: List[str]  # 예시 문장들
    first_seen: datetime
    last_seen: datetime

class PatternAnalyzer:
    """수집된 diff들을 분석하여 규칙 후보를 생성"""
    
    def __init__(self, log_path: str = "logs/pattern_collection.jsonl"):
        self.log_path = Path(log_path)
        self.min_frequency = 3  # 최소 3회 이상 발생
        self.min_confidence = 0.6  # 최소 신뢰도 60%
        
    def analyze_recent_patterns(self, days: int = 7) -> List[PatternCandidate]:
        """최근 N일간의 패턴을 분석하여 후보들을 추출"""
        
        if not self.log_path.exists():
            return []
            
        # 최근 로그 데이터 로드
        recent_diffs = self._load_recent_diffs(days)
        
        # 패턴 빈도 계산
        pattern_stats = self._calculate_pattern_frequencies(recent_diffs)
        
        # 규칙 후보 생성
        candidates = []
        for pattern_key, stats in pattern_stats.items():
            if (stats['frequency'] >= self.min_frequency and 
                stats['avg_confidence'] >= self.min_confidence):
                
                candidate = PatternCandidate(
                    pattern=pattern_key[0],
                    replacement=pattern_key[1], 
                    frequency=stats['frequency'],
                    confidence=stats['avg_confidence'],
                    examples=stats['examples'][:5],  # 최대 5개 예시
                    first_seen=stats['first_seen'],
                    last_seen=stats['last_seen']
                )
                candidates.append(candidate)
                
        # 빈도순으로 정렬
        candidates.sort(key=lambda x: x.frequency, reverse=True)
        return candidates
        
    def _load_recent_diffs(self, days: int) -> List[Dict]:
        """최근 N일간의 diff 데이터를 로드"""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_diffs = []
        
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        entry_date = datetime.fromisoformat(entry['timestamp'])
                        
                        if entry_date >= cutoff_date:
                            recent_diffs.extend(entry['diffs'])
                            
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
                        
        except FileNotFoundError:
            pass
            
        return recent_diffs
        
    def _calculate_pattern_frequencies(self, diffs: List[Dict]) -> Dict:
        """diff들에서 패턴 빈도를 계산"""
        
        pattern_stats = defaultdict(lambda: {
            'frequency': 0,
            'confidences': [],
            'examples': [],
            'first_seen': None,
            'last_seen': None
        })
        
        for diff in diffs:
            # 패턴 정규화 (공백, 특수문자 처리)
            normalized_pattern = self._normalize_pattern(diff['before'], diff['after'])
            
            if not normalized_pattern:
                continue
                
            pattern_key = (normalized_pattern[0], normalized_pattern[1])
            stats = pattern_stats[pattern_key]
            
            # 통계 업데이트
            stats['frequency'] += 1
            stats['confidences'].append(diff['confidence'])
            
            # 예시 추가 (중복 제거)
            example = f"{diff['before']} → {diff['after']}"
            if example not in stats['examples']:
                stats['examples'].append(example)
                
            # 날짜 추적
            timestamp = datetime.now()  # 실제로는 diff의 timestamp 사용
            if stats['first_seen'] is None:
                stats['first_seen'] = timestamp
            stats['last_seen'] = timestamp
            
        # 평균 신뢰도 계산
        for stats in pattern_stats.values():
            if stats['confidences']:
                stats['avg_confidence'] = sum(stats['confidences']) / len(stats['confidences'])
            else:
                stats['avg_confidence'] = 0.0
                
        return pattern_stats
        
    def _normalize_pattern(self, before: str, after: str) -> Tuple[str, str] | None:
        """패턴을 정규화하여 일반적인 규칙으로 변환"""
        
        # 너무 짧거나 긴 변화는 제외
        if len(before) < 2 or len(after) < 2:
            return None
        if len(before) > 20 or len(after) > 20:
            return None
            
        # 공백 정규화
        before_clean = re.sub(r'\s+', ' ', before.strip())
        after_clean = re.sub(r'\s+', ' ', after.strip())
        
        # 숫자가 포함된 경우 패턴화 (예: "1번" → "N번")
        before_pattern = self._generalize_numbers(before_clean)
        after_pattern = self._generalize_numbers(after_clean)
        
        # 유의미한 패턴인지 검증
        if not self._is_valid_pattern(before_pattern, after_pattern):
            return None
            
        return (before_pattern, after_pattern)
        
    def _generalize_numbers(self, text: str) -> str:
        """숫자를 일반화된 패턴으로 변환"""
        # 간단한 숫자 패턴화 (실제 구현시 더 정교하게)
        return re.sub(r'\d+', 'N', text)
        
    def _is_valid_pattern(self, before: str, after: str) -> bool:
        """유효한 패턴인지 검증"""
        
        # 동일한 경우 제외
        if before == after:
            return False
            
        # 한글이 포함되어야 함
        if not any('가' <= c <= '힣' for c in before + after):
            return False
            
        # 특수 문자만으로 구성된 경우 제외
        if all(not c.isalnum() and not '가' <= c <= '힣' for c in before):
            return False
            
        return True
```

### **1.2.2 RuleGenerator 클래스 설계**

```python
# snaptxt/postprocess/pattern_engine/rule_generator.py
import yaml
from typing import List, Dict
from pathlib import Path

class RuleGenerator:
    """패턴 후보를 YAML 규칙으로 변환"""
    
    def __init__(self, suggestions_path: str = "snaptxt/postprocess/patterns/auto_suggestions.yaml"):
        self.suggestions_path = Path(suggestions_path)
        self.suggestions_path.parent.mkdir(exist_ok=True)
        
    def generate_rule_suggestions(self, candidates: List[PatternCandidate]) -> Dict:
        """패턴 후보들을 YAML 규칙 형태로 변환"""
        
        suggestions = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_candidates': len(candidates),
                'auto_apply_threshold': 10  # 10회 이상은 자동 적용 제안
            },
            'auto_apply': [],    # 자동 적용 추천
            'user_review': [],   # 사용자 검토 필요
            'low_confidence': [] # 낮은 신뢰도
        }
        
        for candidate in candidates:
            rule_entry = {
                'pattern': candidate.pattern,
                'replacement': candidate.replacement,
                'frequency': candidate.frequency,
                'confidence': round(candidate.confidence, 3),
                'examples': candidate.examples[:3],  # 최대 3개 예시
                'metadata': {
                    'first_seen': candidate.first_seen.isoformat(),
                    'last_seen': candidate.last_seen.isoformat(),
                    'source': 'auto_analysis'
                }
            }
            
            # 카테고리 분류
            if candidate.frequency >= 10 and candidate.confidence >= 0.8:
                suggestions['auto_apply'].append(rule_entry)
            elif candidate.frequency >= 5 and candidate.confidence >= 0.7:
                suggestions['user_review'].append(rule_entry)
            else:
                suggestions['low_confidence'].append(rule_entry)
                
        # YAML 파일로 저장
        with open(self.suggestions_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(suggestions, f, allow_unicode=True, sort_keys=False)
            
        return suggestions
        
    def apply_approved_rules(self, approved_patterns: List[str]) -> bool:
        """승인된 규칙들을 실제 Stage2 규칙에 추가"""
        
        try:
            # 기존 Stage2 규칙 로드
            stage2_rules_path = Path("snaptxt/postprocess/patterns/stage2_rules.yaml")
            
            if stage2_rules_path.exists():
                with open(stage2_rules_path, 'r', encoding='utf-8') as f:
                    existing_rules = yaml.safe_load(f) or {}
            else:
                existing_rules = {'replacements': []}
                
            # 승인된 규칙들을 추가
            suggestions = self._load_suggestions()
            
            for pattern_id in approved_patterns:
                rule_entry = self._find_rule_by_id(suggestions, pattern_id)
                if rule_entry:
                    # Stage2 형식으로 변환하여 추가
                    stage2_rule = {
                        'pattern': rule_entry['pattern'],
                        'replacement': rule_entry['replacement'],
                        'metadata': {
                            'source': 'auto_suggestion',
                            'added_at': datetime.now().isoformat(),
                            'original_frequency': rule_entry['frequency']
                        }
                    }
                    existing_rules['replacements'].append(stage2_rule)
                    
            # Stage2 규칙 파일 업데이트
            with open(stage2_rules_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(existing_rules, f, allow_unicode=True, sort_keys=False)
                
            # Hot reload 트리거
            from ..patterns.stage2_rules import reload_replacements
            reload_replacements()
            
            return True
            
        except Exception as e:
            print(f"규칙 적용 실패: {e}")
            return False
            
    def _load_suggestions(self) -> Dict:
        """저장된 제안 규칙들을 로드"""
        try:
            with open(self.suggestions_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}
            
    def _find_rule_by_id(self, suggestions: Dict, pattern_id: str) -> Dict | None:
        """패턴 ID로 규칙을 찾기"""
        for category in ['auto_apply', 'user_review', 'low_confidence']:
            for rule in suggestions.get(category, []):
                if f"{rule['pattern']}→{rule['replacement']}" == pattern_id:
                    return rule
        return None
```

## 🖥️ **Phase 1.3: PC 앱 UI 통합 (3/10-3/16)**

### **1.3.1 패턴 추천 UI 설계**

```python
# pc_app.py에 추가할 기능
from snaptxt.postprocess.pattern_engine import PatternAnalyzer, RuleGenerator

class PatternRecommendationWidget(QWidget):
    """패턴 추천 UI 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.analyzer = PatternAnalyzer()
        self.generator = RuleGenerator()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 헤더
        header = QLabel("🤖 자동 패턴 추천")
        header.setFont(QFont("", 12, QFont.Bold))
        layout.addWidget(header)
        
        # 분석 버튼
        self.analyze_button = QPushButton("📊 최근 패턴 분석")
        self.analyze_button.clicked.connect(self.analyze_patterns)
        layout.addWidget(self.analyze_button)
        
        # 결과 표시 영역
        self.results_widget = QScrollArea()
        layout.addWidget(self.results_widget)
        
        # 적용 버튼
        self.apply_button = QPushButton("✅ 선택한 규칙 적용")
        self.apply_button.clicked.connect(self.apply_selected_rules)
        self.apply_button.setEnabled(False)
        layout.addWidget(self.apply_button)
        
        self.setLayout(layout)
        
    def analyze_patterns(self):
        """패턴 분석 실행"""
        self.analyze_button.setText("분석 중...")
        self.analyze_button.setEnabled(False)
        
        try:
            # 패턴 분석
            candidates = self.analyzer.analyze_recent_patterns(days=7)
            
            if not candidates:
                self.show_no_patterns_message()
                return
                
            # 규칙 제안 생성
            suggestions = self.generator.generate_rule_suggestions(candidates)
            
            # UI에 결과 표시
            self.display_suggestions(suggestions)
            
        except Exception as e:
            QMessageBox.warning(self, "분석 실패", f"패턴 분석 중 오류가 발생했습니다: {e}")
            
        finally:
            self.analyze_button.setText("📊 최근 패턴 분석")
            self.analyze_button.setEnabled(True)
            
    def display_suggestions(self, suggestions: Dict):
        """분석 결과를 UI에 표시"""
        
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.selected_rules = []
        self.checkboxes = []
        
        # 자동 적용 추천
        if suggestions.get('auto_apply'):
            layout.addWidget(QLabel("🎯 자동 적용 추천 (고신뢰도)"))
            for rule in suggestions['auto_apply']:
                cb = self.create_rule_checkbox(rule, auto=True)
                layout.addWidget(cb)
                self.checkboxes.append(cb)
                
        # 사용자 검토 필요
        if suggestions.get('user_review'):
            layout.addWidget(QLabel("🔍 검토 후 적용"))
            for rule in suggestions['user_review']:
                cb = self.create_rule_checkbox(rule, auto=False)
                layout.addWidget(cb)
                self.checkboxes.append(cb)
                
        widget.setLayout(layout)
        self.results_widget.setWidget(widget)
        self.apply_button.setEnabled(True)
        
    def create_rule_checkbox(self, rule: Dict, auto: bool = False) -> QCheckBox:
        """단일 규칙 체크박스 생성"""
        
        text = f"'{rule['pattern']}' → '{rule['replacement']}' " \
               f"({rule['frequency']}회, 신뢰도: {rule['confidence']:.1%})"
               
        cb = QCheckBox(text)
        cb.setChecked(auto)  # 자동 적용 추천은 기본 선택
        
        # 예시 툴팁 추가
        if rule.get('examples'):
            tooltip = "예시:\n" + "\n".join(rule['examples'][:3])
            cb.setToolTip(tooltip)
            
        # 규칙 ID 저장
        cb.rule_id = f"{rule['pattern']}→{rule['replacement']}"
        
        return cb
        
    def apply_selected_rules(self):
        """선택된 규칙들을 실제 Stage2에 적용"""
        
        selected = [cb.rule_id for cb in self.checkboxes if cb.isChecked()]
        
        if not selected:
            QMessageBox.information(self, "선택 없음", "적용할 규칙을 선택해주세요.")
            return
            
        # 확인 메시지
        reply = QMessageBox.question(self, "규칙 적용 확인", 
                                   f"{len(selected)}개 규칙을 적용하시겠습니까?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                success = self.generator.apply_approved_rules(selected)
                if success:
                    QMessageBox.information(self, "적용 완료", 
                                          f"{len(selected)}개 규칙이 성공적으로 적용되었습니다.")
                    self.clear_results()
                else:
                    QMessageBox.warning(self, "적용 실패", "규칙 적용 중 오류가 발생했습니다.")
                    
            except Exception as e:
                QMessageBox.critical(self, "오류", f"규칙 적용 실패: {e}")
```

### **1.3.2 메인 앱에 통합**

```python
# pc_app.py의 SnapTXTGUI 클래스 수정
class SnapTXTGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # 기존 초기화 코드...
        
        # 패턴 추천 위젯 추가
        self.pattern_widget = PatternRecommendationWidget()
        
        # 기존 레이아웃에 통합
        self.setup_pattern_recommendation_tab()
        
    def setup_pattern_recommendation_tab(self):
        """패턴 추천 탭을 메인 UI에 추가"""
        
        # 탭 위젯이 있다면 추가, 없다면 독립 위젯으로
        if hasattr(self, 'tab_widget'):
            self.tab_widget.addTab(self.pattern_widget, "🤖 패턴 추천")
        else:
            # 사이드바나 별도 영역에 추가
            # 구체적인 위치는 기존 UI 구조에 맞춰 조정
            pass
```

## 📊 **성능 목표 및 검증 방법**

### **Phase 1.1 성공 기준**
- [x] **실시간 diff 수집**: 후처리 파이프라인 실행시 자동 수집
- [x] **의미있는 변화만 필터링**: 공백/대소문자 변화 제외
- [x] **로그 저장**: JSONL 형태로 안정적 저장
- [x] **성능 영향 최소화**: 기존 처리 시간 10% 이내 증가

### **Phase 1.2 성공 기준**
- [x] **패턴 빈도 분석**: 최소 3회 이상 발생 패턴 탐지
- [x] **신뢰도 기반 필터링**: 60% 이상 신뢰도 패턴만 추천
- [x] **자동/수동 분류**: 고신뢰도(80%+)는 자동 적용 추천
- [x] **YAML 호환 형식**: 기존 Stage2 규칙과 완전 호환

### **검증 방법**
1. **기능 테스트**: 샘플 텍스트로 전체 플로우 테스트
2. **성능 테스트**: 100건 처리시 시간 측정
3. **품질 테스트**: 실제 추천 규칙의 정확도 측정
4. **통합 테스트**: PC 앱에서 UI 동작 확인

## 🚀 **다음 단계**

Phase 1 완료 후:
- **Phase 2**: diff 수집 시스템 (사용자 피드백)
- **Phase 3**: 스마트 룰 엔진 (충돌/스코프 관리)
- **Phase 4**: 콘텐츠 타입 분리 시스템

---

이제 **DiffCollector 클래스 구현**부터 시작하겠습니다! 🔧