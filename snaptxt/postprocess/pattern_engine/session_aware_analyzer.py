"""Session-aware Pattern Analyzer - Phase 1.5

세션별, 책별, 도메인별 계층화된 패턴 분석
실질적인 OCR 품질 개선을 위한 특화 패턴 발견
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import json
from pathlib import Path
from .pattern_analyzer import PatternAnalyzer, PatternCandidate


@dataclass
class SessionAwarePatternCandidate(PatternCandidate):
    """세션 인식 패턴 후보"""
    # 기존 필드 상속: pattern, replacement, frequency, confidence, examples, 
    #                first_seen, last_seen, stage, predicted_category
    
    # Phase 1.5 추가 필드들
    session_contexts: List[str]       # 발생한 세션들
    book_domains: List[str]           # 발생한 도메인들
    device_ids: List[str]             # 발생한 디바이스들
    pattern_scope: str                # "batch", "book", "domain", "global"
    impact_score: float               # 실제 품질 개선 예상 점수 (0.0~1.0)


class SessionAwarePatternAnalyzer:
    """세션 인식 패턴 분석기 - 계층화된 패턴 학습"""
    
    def __init__(self, log_dir: str = "logs"):
        self.base_analyzer = PatternAnalyzer(log_dir)
        self.log_path = self.base_analyzer.log_path
        
        # 세션별 분석 설정
        self.batch_min_frequency = 2     # 배치 패턴 최소 빈도
        self.book_min_frequency = 3      # 책 패턴 최소 빈도  
        self.domain_min_frequency = 5    # 도메인 패턴 최소 빈도
        self.global_min_frequency = 10   # 전역 패턴 최소 빈도
        
        # 품질 개선 임계값
        self.high_impact_threshold = 0.8
        self.medium_impact_threshold = 0.5
    
    def analyze_session_aware_patterns(self, 
                                     target_session_id: Optional[str] = None,
                                     days: int = 7) -> List[SessionAwarePatternCandidate]:
        """세션 인식 패턴 분석 - 계층화된 우선순위"""
        
        # 1. 최근 diff 데이터 로드
        recent_diffs = self._load_recent_session_diffs(days)
        
        if not recent_diffs:
            return []
        
        # 2. 계층별 패턴 분석
        batch_patterns = self._analyze_batch_patterns(recent_diffs, target_session_id)
        book_patterns = self._analyze_book_patterns(recent_diffs, target_session_id) 
        domain_patterns = self._analyze_domain_patterns(recent_diffs)
        global_patterns = self._analyze_global_patterns(recent_diffs)
        
        # 3. 우선순위로 병합 (구체적 → 일반적)
        all_candidates = self._merge_patterns_by_priority(
            batch_patterns, book_patterns, domain_patterns, global_patterns
        )
        
        # 4. 실제 품질 개선 효과 순으로 정렬
        sorted_candidates = sorted(all_candidates, 
                                 key=lambda x: (x.impact_score, x.frequency, x.confidence), 
                                 reverse=True)
        
        return sorted_candidates[:20]  # 상위 20개만
    
    def _load_recent_session_diffs(self, days: int) -> List[Dict]:
        """세션 컨텍스트가 포함된 diff 데이터 로드"""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        session_diffs = []
        
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        entry_date = datetime.fromisoformat(entry['timestamp'])
                        
                        if entry_date >= cutoff_date:
                            diffs = entry.get('diffs', [])
                            
                            # 세션 컨텍스트가 있는 diff만 처리
                            for diff in diffs:
                                if diff.get('book_session_id'):  # 세션 정보가 있는 경우만
                                    session_diffs.append({
                                        **diff,
                                        'timestamp': entry_date,
                                        # 세션 정보 추출
                                        'session_id': diff.get('book_session_id'),
                                        'book_domain': diff.get('book_domain', 'unknown'),
                                        'device_id': diff.get('device_id', 'unknown'),
                                        'image_quality': diff.get('image_quality', 0.5)
                                    })
                            
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
                        
        except FileNotFoundError:
            pass
            
        return session_diffs
    
    def _analyze_batch_patterns(self, 
                               diffs: List[Dict], 
                               target_session_id: Optional[str] = None) -> List[SessionAwarePatternCandidate]:
        """배치별 특화 패턴 분석 (최고 우선순위)"""
        
        if target_session_id:
            # 특정 세션의 배치 패턴만 분석
            session_diffs = [d for d in diffs if d.get('session_id') == target_session_id]
        else:
            session_diffs = diffs
            
        # 배치별로 그룹핑
        batch_groups = defaultdict(list)
        for diff in session_diffs:
            batch_id = diff.get('capture_batch_id', 'unknown')
            batch_groups[batch_id].append(diff)
        
        candidates = []
        
        for batch_id, batch_diffs in batch_groups.items():
            if len(batch_diffs) < self.batch_min_frequency:
                continue
                
            # 배치 내 패턴 빈도 계산
            batch_patterns = self._calculate_pattern_frequencies_session(batch_diffs)
            
            for pattern_key, stats in batch_patterns.items():
                if stats['frequency'] >= self.batch_min_frequency:
                    
                    # 실제 품질 개선 효과 계산
                    impact_score = self._calculate_impact_score(
                        pattern_key, stats, scope="batch"
                    )
                    
                    candidate = SessionAwarePatternCandidate(
                        pattern=pattern_key[0],
                        replacement=pattern_key[1],
                        frequency=stats['frequency'],
                        confidence=stats['avg_confidence'],
                        examples=stats['examples'][:3],
                        first_seen=stats['first_seen'],
                        last_seen=stats['last_seen'], 
                        stage=stats['stage'],
                        # 세션 관련 필드들
                        session_contexts=[batch_id],
                        book_domains=list(set(d.get('book_domain', 'unknown') for d in batch_diffs)),
                        device_ids=list(set(d.get('device_id', 'unknown') for d in batch_diffs)),
                        pattern_scope="batch", 
                        impact_score=impact_score
                    )
                    candidates.append(candidate)
        
        return candidates
    
    def _analyze_book_patterns(self, 
                              diffs: List[Dict], 
                              target_session_id: Optional[str] = None) -> List[SessionAwarePatternCandidate]:
        """책별 특화 패턴 분석 (중간 우선순위)"""
        
        # 책별로 그룹핑 (세션 ID에서 책 정보 추출)
        book_groups = defaultdict(list)
        for diff in diffs:
            session_id = diff.get('session_id', '')
            # 세션 ID 형태: "20260302_book_abc123_session01"
            if '_book_' in session_id:
                book_id = session_id.split('_book_')[1].split('_')[0]
            else:
                book_id = 'unknown'
            book_groups[book_id].append(diff)
        
        candidates = []
        
        for book_id, book_diffs in book_groups.items():
            if len(book_diffs) < self.book_min_frequency:
                continue
                
            # 책별 패턴 빈도 계산
            book_patterns = self._calculate_pattern_frequencies_session(book_diffs)
            
            for pattern_key, stats in book_patterns.items():
                if stats['frequency'] >= self.book_min_frequency:
                    
                    # 폰트 특화 오인식 패턴 감지
                    impact_score = self._calculate_impact_score(
                        pattern_key, stats, scope="book"
                    )
                    
                    # 책 특화 패턴은 더 중요하게 취급
                    if self._is_font_specific_pattern(pattern_key):
                        impact_score += 0.2
                    
                    candidate = SessionAwarePatternCandidate(
                        pattern=pattern_key[0],
                        replacement=pattern_key[1],
                        frequency=stats['frequency'],
                        confidence=stats['avg_confidence'],
                        examples=stats['examples'][:3],
                        first_seen=stats['first_seen'],
                        last_seen=stats['last_seen'],
                        stage=stats['stage'],
                        session_contexts=list(set(d.get('session_id', '') for d in book_diffs)),
                        book_domains=list(set(d.get('book_domain', 'unknown') for d in book_diffs)),
                        device_ids=list(set(d.get('device_id', 'unknown') for d in book_diffs)),
                        pattern_scope="book",
                        impact_score=impact_score
                    )
                    candidates.append(candidate)
        
        return candidates
    
    def _analyze_domain_patterns(self, diffs: List[Dict]) -> List[SessionAwarePatternCandidate]:
        """도메인별 패턴 분석 (낮은 우선순위)"""
        
        # 도메인별로 그룹핑
        domain_groups = defaultdict(list)
        for diff in diffs:
            domain = diff.get('book_domain', 'unknown')
            domain_groups[domain].append(diff)
        
        candidates = []
        
        for domain, domain_diffs in domain_groups.items():
            if len(domain_diffs) < self.domain_min_frequency:
                continue
                
            domain_patterns = self._calculate_pattern_frequencies_session(domain_diffs)
            
            for pattern_key, stats in domain_patterns.items():
                if stats['frequency'] >= self.domain_min_frequency:
                    
                    impact_score = self._calculate_impact_score(
                        pattern_key, stats, scope="domain"
                    )
                    
                    candidate = SessionAwarePatternCandidate(
                        pattern=pattern_key[0],
                        replacement=pattern_key[1],
                        frequency=stats['frequency'],
                        confidence=stats['avg_confidence'],
                        examples=stats['examples'][:3],
                        first_seen=stats['first_seen'],
                        last_seen=stats['last_seen'],
                        stage=stats['stage'],
                        session_contexts=list(set(d.get('session_id', '') for d in domain_diffs)),
                        book_domains=[domain],
                        device_ids=list(set(d.get('device_id', 'unknown') for d in domain_diffs)),
                        pattern_scope="domain",
                        impact_score=impact_score
                    )
                    candidates.append(candidate)
        
        return candidates
    
    def _analyze_global_patterns(self, diffs: List[Dict]) -> List[SessionAwarePatternCandidate]:
        """전역 패턴 분석 (최저 우선순위)"""
        
        global_patterns = self._calculate_pattern_frequencies_session(diffs)
        candidates = []
        
        for pattern_key, stats in global_patterns.items():
            if stats['frequency'] >= self.global_min_frequency:
                
                impact_score = self._calculate_impact_score(
                    pattern_key, stats, scope="global"
                )
                
                candidate = SessionAwarePatternCandidate(
                    pattern=pattern_key[0],
                    replacement=pattern_key[1],
                    frequency=stats['frequency'],
                    confidence=stats['avg_confidence'],
                    examples=stats['examples'][:3],
                    first_seen=stats['first_seen'],
                    last_seen=stats['last_seen'],
                    stage=stats['stage'],
                    session_contexts=list(set(d.get('session_id', '') for d in diffs if d.get('session_id'))),
                    book_domains=list(set(d.get('book_domain', 'unknown') for d in diffs)),
                    device_ids=list(set(d.get('device_id', 'unknown') for d in diffs)),
                    pattern_scope="global",
                    impact_score=impact_score
                )
                candidates.append(candidate)
        
        return candidates
    
    def _calculate_pattern_frequencies_session(self, diffs: List[Dict]) -> Dict:
        """세션 정보가 포함된 패턴 빈도 계산"""
        
        pattern_stats = defaultdict(lambda: {
            'frequency': 0,
            'confidences': [],
            'examples': [], 
            'first_seen': None,
            'last_seen': None,
            'stage': 'unknown'
        })
        
        for diff in diffs:
            # 기존 패턴 정규화 사용
            normalized = self.base_analyzer._normalize_pattern(
                diff.get('before', ''), 
                diff.get('after', '')
            )
            
            if not normalized:
                continue
                
            pattern_key = normalized
            stats = pattern_stats[pattern_key]
            
            # 통계 업데이트
            stats['frequency'] += 1
            stats['confidences'].append(diff.get('confidence', 0.5))
            stats['examples'].append(f"{diff.get('before', '')} → {diff.get('after', '')}")
            stats['stage'] = diff.get('stage', 'unknown')
            
            # 시간 정보
            timestamp = diff.get('timestamp')
            if timestamp:
                if not stats['first_seen'] or timestamp < stats['first_seen']:
                    stats['first_seen'] = timestamp
                if not stats['last_seen'] or timestamp > stats['last_seen']:
                    stats['last_seen'] = timestamp
        
        # 평균 신뢰도 계산
        for stats in pattern_stats.values():
            stats['avg_confidence'] = sum(stats['confidences']) / len(stats['confidences'])
        
        return dict(pattern_stats)
    
    def _calculate_impact_score(self, pattern_key: Tuple[str, str], stats: Dict, scope: str) -> float:
        """실제 품질 개선 효과 점수 계산"""
        
        before, after = pattern_key
        
        # 기본점수 - 신뢰도와 빈도 기반
        base_score = (stats['avg_confidence'] * 0.7) + (min(stats['frequency'] / 10, 1.0) * 0.3)
        
        # 패턴 타입별 가중치
        type_bonus = 0.0
        
        # 폰트 특화 오인식 (최고 중요도)
        if self._is_font_specific_pattern(pattern_key):
            type_bonus += 0.4
        
        # 한국어 특화 교정
        elif self._is_korean_specific_pattern(pattern_key):
            type_bonus += 0.3
        
        # 문맥 기반 띄어쓰기 교정
        elif self._is_spacing_pattern(pattern_key): 
            type_bonus += 0.2
        
        # 문장부호 정리 (낮은 중요도)
        elif self._is_punctuation_pattern(pattern_key):
            type_bonus += 0.1
        
        # 범위별 가중치
        scope_multiplier = {
            "batch": 1.0,   # 배치 패턴 최고
            "book": 0.9,    # 책 패턴
            "domain": 0.7,  # 도메인 패턴
            "global": 0.5   # 전역 패턴 최저
        }.get(scope, 0.5)
        
        final_score = (base_score + type_bonus) * scope_multiplier
        return min(final_score, 1.0)
    
    def _is_font_specific_pattern(self, pattern_key: Tuple[str, str]) -> bool:
        """폰트 특화 오인식 패턴 감지"""
        before, after = pattern_key
        
        # 일반적인 폰트 오인식 패턴들
        font_patterns = [
            ('rn', 'm'), ('cl', 'd'), ('l', '1'), ('I', 'l'), 
            ('되엇', '되었'), ('잇다', '있다'), ('되엇습니다', '되었습니다'),
            ('자아 을', '자아를'), ('마음 의', '마음의')
        ]
        
        for wrong, correct in font_patterns:
            if (before == wrong and after == correct) or (wrong in before and correct in after):
                return True
        
        return False
    
    def _is_korean_specific_pattern(self, pattern_key: Tuple[str, str]) -> bool:
        """한국어 특화 교정 패턴 감지"""
        before, after = pattern_key
        
        # 한국어가 포함되고 의미있는 교정인지 확인
        has_korean = any('가' <= c <= '힣' for c in before + after)
        has_meaningful_change = len(before) >= 2 and len(after) >= 2
        
        return has_korean and has_meaningful_change
    
    def _is_spacing_pattern(self, pattern_key: Tuple[str, str]) -> bool:
        """띄어쓰기 교정 패턴 감지"""
        before, after = pattern_key
        
        # 공백 변화가 포함되어 있고 한국어가 있는 경우
        has_space_change = before.replace(' ', '') != after.replace(' ', '')
        has_korean = any('가' <= c <= '힣' for c in before + after)
        
        return has_space_change and has_korean
    
    def _is_punctuation_pattern(self, pattern_key: Tuple[str, str]) -> bool:
        """문장부호 정리 패턴 감지"""
        before, after = pattern_key
        
        punctuation_chars = '.,!?;:"\'()[]{}""''—–-'
        
        return any(c in punctuation_chars for c in before + after)
    
    def _merge_patterns_by_priority(self, 
                                   batch_patterns: List[SessionAwarePatternCandidate],
                                   book_patterns: List[SessionAwarePatternCandidate], 
                                   domain_patterns: List[SessionAwarePatternCandidate],
                                   global_patterns: List[SessionAwarePatternCandidate]) -> List[SessionAwarePatternCandidate]:
        """우선순위로 패턴 병합 (중복 제거)"""
        
        seen_patterns = set()
        merged_candidates = []
        
        # 우선순위: batch → book → domain → global
        for pattern_list in [batch_patterns, book_patterns, domain_patterns, global_patterns]:
            for candidate in pattern_list:
                pattern_signature = (candidate.pattern, candidate.replacement)
                
                if pattern_signature not in seen_patterns:
                    seen_patterns.add(pattern_signature)
                    merged_candidates.append(candidate)
        
        return merged_candidates
    
    def get_session_specific_recommendations(self, session_id: str) -> List[SessionAwarePatternCandidate]:
        """특정 세션에 대한 맞춤 패턴 추천"""
        
        return self.analyze_session_aware_patterns(target_session_id=session_id)
    
    def get_book_learning_profile(self, book_id: str) -> Dict:
        """책별 학습 프로파일 생성"""
        
        # 해당 책의 모든 세션 패턴 분석
        book_patterns = []  # TODO: 책 ID로 패턴 필터링
        
        return {
            "book_id": book_id,
            "learned_patterns": len(book_patterns),
            "high_impact_patterns": len([p for p in book_patterns if p.impact_score > self.high_impact_threshold]),
            "domains": list(set(p.book_domains[0] for p in book_patterns if p.book_domains)),
            "pattern_categories": list(set(p.pattern_scope for p in book_patterns))
        }