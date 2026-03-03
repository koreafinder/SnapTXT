"""패턴 분석기 - PatternAnalyzer

수집된 diff 데이터를 분석하여 규칙 후보를 생성합니다.
반복되는 패턴을 탐지하고 신뢰도를 계산하여 추천 우선순위를 결정합니다.
"""

from collections import defaultdict, Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
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
    stage: str        # "stage2" or "stage3"
    
    
class PatternAnalyzer:
    """수집된 diff들을 분석하여 규칙 후보를 생성"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_path = Path(log_dir) / "pattern_collection.jsonl"
        
        # 분석 설정 - 더 관대한 기준으로 조정
        self.min_frequency = 2    # 최소 2회 이상 발생 (3→2)
        self.min_confidence = 0.5 # 최소 신뢰도 50% (60%→50%)
        self.max_pattern_length = 20  # 최대 패턴 길이
        
    def analyze_recent_patterns(self, days: int = 7, stage_filter: str = None) -> List[PatternCandidate]:
        """최근 N일간의 패턴을 분석하여 후보들을 추출"""
        
        if not self.log_path.exists():
            return []
            
        # 최근 로그 데이터 로드
        recent_diffs = self._load_recent_diffs(days, stage_filter)
        
        if not recent_diffs:
            return []
        
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
                    last_seen=stats['last_seen'],
                    stage=stats['stage']
                )
                candidates.append(candidate)
                
        # 빈도 × 신뢰도 순으로 정렬
        candidates.sort(key=lambda x: x.frequency * x.confidence, reverse=True)
        return candidates
        
    def _load_recent_diffs(self, days: int, stage_filter: str = None) -> List[Dict]:
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
                            # stage 필터링
                            diffs = entry.get('diffs', [])
                            if stage_filter:
                                diffs = [d for d in diffs if d.get('stage') == stage_filter]
                            
                            recent_diffs.extend(diffs)
                            
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
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
            'last_seen': None,
            'stage': 'unknown'
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
            stats['confidences'].append(diff.get('confidence', 0.5))
            stats['stage'] = diff.get('stage', 'unknown')
            
            # 예시 추가 (중복 제거)
            example = f"'{diff['before']}' → '{diff['after']}'"
            if example not in stats['examples'] and len(stats['examples']) < 10:
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
        
    def _normalize_pattern(self, before: str, after: str) -> Optional[Tuple[str, str]]:
        """패턴을 정규화하여 일반적인 규칙으로 변환 - OCR 후처리에 맞게 개선"""
        
        # OCR 후처리에서는 삭제 패턴도 중요하므로 빈 문자열 허용
        # 길이 검증 - after가 빈 문자열인 삭제 패턴도 허용
        if (len(before) < 1 or 
            len(before) > self.max_pattern_length or len(after) > self.max_pattern_length):
            return None
        
        # 공백 패턴 특별 처리 - 공백 정리는 매우 유용한 패턴
        if before.isspace() and after.isspace():
            # 공백 → 다른 공백 패턴은 "SPACE_N" → "SPACE_M" 형태로 정규화
            return (f"SPACE_{len(before)}", f"SPACE_{len(after)}")
        elif before.isspace():
            # 공백 → 텍스트 패턴
            return (f"SPACE_{len(before)}", after.strip())
        elif after.isspace():
            # 텍스트 → 공백 패턴  
            return (before.strip(), f"SPACE_{len(after)}")
        
        # 삭제 패턴 (after가 빈 문자열) 허용
        if after == "":
            # 삭제 패턴은 before 내용을 그대로 보존
            return (before, "DELETE")
        
        # 추가 패턴 (before가 빈 문자열) 허용  
        if before == "":
            return ("INSERT", after)
            
        # 일반 텍스트 패턴
        before_clean = before.strip()
        after_clean = after.strip()
        
        # 빈 문자열 체크 - 하지만 양쪽 모두 빈 문자열인 경우만 제외
        if not before_clean and not after_clean:
            return None
            
        # 동일한 패턴 제외
        if before_clean == after_clean:
            return None
            
        # 숫자가 포함된 경우 컨텍스트 고려
        before_pattern = self._generalize_with_context(before_clean)
        after_pattern = self._generalize_with_context(after_clean)
        
        # 유의미한 패턴인지 검증 - 더 관대한 기준 적용
        if not self._is_valid_pattern_relaxed(before_pattern, after_pattern):
            return None
            
        return (before_pattern, after_pattern)
        
    def _generalize_with_context(self, text: str) -> str:
        """컨텍스트를 고려하여 패턴을 일반화"""
        
        # 단순한 숫자 패턴화는 위험하므로 조심스럽게 적용
        # 예: "1번" → "N번" 은 안전하지만, "2020년" → "N년" 은 위험
        
        # 순서/번호 패턴 (1번, 2장, 3절 등)
        number_with_unit = re.sub(r'\b\d+([번장절항목])\b', r'N\1', text)
        
        # 간단한 횟수 표현 (1회, 2번째 등) 
        count_pattern = re.sub(r'\b\d+([회번])째?\b', r'N\1째', number_with_unit)
        
        return count_pattern
        
    def _is_valid_pattern(self, before: str, after: str) -> bool:
        """유효한 패턴인지 검증"""
        
        # 동일한 경우 제외
        if before == after:
            return False
            
        # 너무 짧은 패턴 제외 (1글자)
        if len(before.replace(' ', '')) < 2 and len(after.replace(' ', '')) < 2:
            return False
        
        # 한글, 영문, 숫자 중 하나 이상 포함되어야 함
        has_meaningful_content = any(
            '가' <= c <= '힣' or c.isalpha() or c.isdigit() 
            for c in before + after
        )
        if not has_meaningful_content:
            return False
            
        # 특수문자만으로 구성된 경우 제외 (단, 문장부호는 허용)
        special_only = all(
            not c.isalnum() and not '가' <= c <= '힣' and c not in ' .,!?;:"\'-()[]{}'
            for c in before.replace(' ', '') + after.replace(' ', '')
        )
        if special_only:
            return False
            
        return True
        
    def _is_valid_pattern_relaxed(self, before: str, after: str) -> bool:
        """유효한 패턴인지 검증 - OCR 후처리에 맞게 완화된 기준"""
        
        # 특수 패턴들 허용
        if before == "DELETE" or after == "DELETE" or before == "INSERT" or after == "INSERT":
            return True
        
        # SPACE 패턴 허용    
        if "SPACE_" in before or "SPACE_" in after:
            return True
            
        # 동일한 경우만 제외
        if before == after:
            return False
            
        # OCR에서 자주 발생하는 1글자 교정도 허용
        # 길이 제한 완화
        
        # 완전히 빈 경우만 제외
        if not before.replace(' ', '') and not after.replace(' ', ''):
            return False
        
        # 한글, 영문, 숫자, 문장부호 중 하나라도 있으면 허용
        has_content = any(
            '가' <= c <= '힣' or c.isalpha() or c.isdigit() or c in '.,!?;:"\'-()[]{}'
            for c in before + after
        )
        
        return has_content
        
    def get_pattern_statistics(self, days: int = 30) -> Dict:
        """패턴 수집 통계 정보 반환"""
        
        recent_diffs = self._load_recent_diffs(days)
        
        if not recent_diffs:
            return {
                "total_diffs": 0,
                "stage2_diffs": 0,
                "stage3_diffs": 0,
                "unique_patterns": 0,
                "high_frequency_patterns": 0
            }
            
        # 통계 계산
        total_diffs = len(recent_diffs)
        stage2_diffs = len([d for d in recent_diffs if d.get('stage') == 'stage2'])
        stage3_diffs = len([d for d in recent_diffs if d.get('stage') == 'stage3'])
        
        # 유니크 패턴 수
        patterns = set()
        for diff in recent_diffs:
            norm = self._normalize_pattern(diff['before'], diff['after'])
            if norm:
                patterns.add(norm)
                
        pattern_stats = self._calculate_pattern_frequencies(recent_diffs)
        high_freq = len([stats for stats in pattern_stats.values() 
                        if stats['frequency'] >= self.min_frequency])
        
        return {
            "total_diffs": total_diffs,
            "stage2_diffs": stage2_diffs, 
            "stage3_diffs": stage3_diffs,
            "unique_patterns": len(patterns),
            "high_frequency_patterns": high_freq,
            "analysis_period_days": days
        }