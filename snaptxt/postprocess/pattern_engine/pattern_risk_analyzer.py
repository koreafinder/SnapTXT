# -*- coding: utf-8 -*-
"""
Phase 1.8: Pattern Risk Analyzer
패턴의 위험도를 분석하여 안전한 적용을 보장하는 시스템
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set
import re
import logging

logger = logging.getLogger(__name__)


class PatternRiskLevel(Enum):
    """패턴 위험도 레벨"""
    GLOBAL_SAFE = "global"      # 가장 안전, 모든 컨텍스트에 적용 가능
    DOMAIN_MEDIUM = "domain"    # 도메인별 안전 (학술서/소설/잡지/일반)
    BOOK_HIGH = "book"          # 책별 안전 (특정 폰트/출간사)
    BATCH_CRITICAL = "batch"    # 가장 위험, 연속 촬영 내에서만


@dataclass
class PatternRiskAssessment:
    """패턴 위험도 평가 결과"""
    pattern: str
    replacement: str
    risk_level: PatternRiskLevel
    confidence: float
    risk_factors: List[str]
    context_dependency: float  # 0.0~1.0, 높을수록 맥락에 의존적
    destructive_potential: float  # 0.0~1.0, 높을수록 파괴적
    frequency_requirement: int  # 최소 필요한 빈도
    reasoning: str


class PatternRiskAnalyzer:
    """패턴의 위험도를 분석하는 시스템"""
    
    def __init__(self):
        # 고위험 패턴 특성 정의
        self.HIGH_RISK_PATTERNS = {
            # 단일 문자 → 다른 문자 (매우 위험)
            "single_char_replace": r"^[a-zA-Z0-9가-힣]$",
            # 숫자 변환 (위험)
            "number_transform": r"^[0-9]+$",
            # 단어 경계 무시 치환 (위험)
            "boundary_ignorant": r".*[a-zA-Z].*",
            # 완전 삭제 (고위험)
            "complete_deletion": r"^.+$",
        }
        
        # 안전한 패턴 특성
        self.SAFE_PATTERNS = {
            # 공백/구두점 정리 (안전)
            "whitespace_cleanup": r"^\s+$|^\.+$|^\s*\.\s*$",
            # 명백한 오타 (비교적 안전)
            "obvious_typo": r"^[ぁ-ゔ]+$|^[！？]{2,}$",
        }
        
        # 도메인별 위험 임계값
        self.DOMAIN_THRESHOLDS = {
            "textbook": {"min_frequency": 5, "min_confidence": 0.8},
            "novel": {"min_frequency": 4, "min_confidence": 0.75},
            "magazine": {"min_frequency": 3, "min_confidence": 0.7},
            "general": {"min_frequency": 6, "min_confidence": 0.85},
        }

    def analyze_pattern_risk(
        self, 
        pattern: str, 
        replacement: str,
        frequency: int,
        confidence: float,
        session_context: Optional[Dict] = None
    ) -> PatternRiskAssessment:
        """패턴의 위험도를 종합 분석"""
        
        risk_factors = []
        context_dependency = 0.0
        destructive_potential = 0.0
        
        # 1. 구조적 위험도 평가
        structural_risk = self._assess_structural_risk(pattern, replacement, risk_factors)
        
        # 2. 맥락 의존성 평가
        context_dependency = self._assess_context_dependency(pattern, replacement, risk_factors)
        
        # 3. 파괴 가능성 평가
        destructive_potential = self._assess_destructive_potential(pattern, replacement, risk_factors)
        
        # 4. 종합 위험도 결정
        risk_level = self._determine_risk_level(
            structural_risk, context_dependency, destructive_potential,
            frequency, confidence, session_context
        )
        
        # 5. 최소 빈도 요구사항 계산
        frequency_requirement = self._calculate_frequency_requirement(risk_level, session_context)
        
        # 6. 판정 근거 생성
        reasoning = self._generate_reasoning(
            structural_risk, context_dependency, destructive_potential,
            risk_factors, risk_level
        )
        
        return PatternRiskAssessment(
            pattern=pattern,
            replacement=replacement,
            risk_level=risk_level,
            confidence=confidence,
            risk_factors=risk_factors,
            context_dependency=context_dependency,
            destructive_potential=destructive_potential,
            frequency_requirement=frequency_requirement,
            reasoning=reasoning
        )

    def _assess_structural_risk(self, pattern: str, replacement: str, risk_factors: List[str]) -> float:
        """구조적 위험도 평가"""
        risk_score = 0.0
        
        # 단일 문자 변환은 고위험
        if len(pattern) == 1 and len(replacement) == 1 and pattern != replacement:
            risk_score += 0.7
            risk_factors.append("단일문자변환")
            
        # 숫자 변환은 고위험
        if pattern.isdigit() and replacement.isdigit():
            risk_score += 0.6
            risk_factors.append("숫자변환")
            
        # 완전 삭제는 고위험
        if replacement == "DELETE" or replacement == "":
            risk_score += 0.5
            risk_factors.append("완전삭제")
            
        # 길이 차이가 클수록 위험
        length_diff = abs(len(pattern) - len(replacement))
        if length_diff > 2:
            risk_score += min(0.3, length_diff * 0.1)
            risk_factors.append(f"길이차이{length_diff}")
            
        # 영어-한글 변환은 고위험
        if self._is_cross_language_pattern(pattern, replacement):
            risk_score += 0.5
            risk_factors.append("언어간변환")
            
        return min(1.0, risk_score)

    def _assess_context_dependency(self, pattern: str, replacement: str, risk_factors: List[str]) -> float:
        """맥락 의존성 평가 (높을수록 위험)"""
        dependency = 0.0
        
        # 동음이의어 가능성
        if self._is_potential_homophone(pattern, replacement):
            dependency += 0.6
            risk_factors.append("동음이의어위험")
            
        # 문맥에 따라 의미가 달라질 수 있는 패턴
        if pattern in ["l", "1", "0", "O", "o"]:  # I, l, 1 혼동
            dependency += 0.8
            risk_factors.append("문자혼동위험")
            
        # 단어 경계 무시 치환
        if re.match(r"[a-zA-Z]", pattern) and not pattern.isspace():
            dependency += 0.4
            risk_factors.append("단어경계위험")
            
        return min(1.0, dependency)

    def _assess_destructive_potential(self, pattern: str, replacement: str, risk_factors: List[str]) -> float:
        """파괴 가능성 평가"""
        potential = 0.0
        
        # 정보 손실 가능성
        if replacement == "DELETE" or len(replacement) < len(pattern):
            potential += 0.6
            risk_factors.append("정보손실위험")
            
        # 의미 변경 가능성
        if self._changes_meaning(pattern, replacement):
            potential += 0.7
            risk_factors.append("의미변경위험")
            
        # 가독성 저하 가능성
        if self._reduces_readability(pattern, replacement):
            potential += 0.3
            risk_factors.append("가독성저하")
            
        return min(1.0, potential)

    def _determine_risk_level(
        self, 
        structural_risk: float,
        context_dependency: float, 
        destructive_potential: float,
        frequency: int,
        confidence: float,
        session_context: Optional[Dict]
    ) -> PatternRiskLevel:
        """종합 위험도 결정"""
        
        # 위험 점수 계산 (0.0~1.0)
        overall_risk = (structural_risk + context_dependency + destructive_potential) / 3.0
        
        # 빈도와 신뢰도로 보정
        reliability_factor = min(1.0, (frequency / 10.0) * confidence)
        adjusted_risk = overall_risk * (1.0 - reliability_factor * 0.3)
        
        # 위험도 분류
        if adjusted_risk >= 0.7:
            return PatternRiskLevel.BATCH_CRITICAL
        elif adjusted_risk >= 0.5:
            return PatternRiskLevel.BOOK_HIGH
        elif adjusted_risk >= 0.3:
            return PatternRiskLevel.DOMAIN_MEDIUM
        else:
            return PatternRiskLevel.GLOBAL_SAFE

    def _calculate_frequency_requirement(
        self, 
        risk_level: PatternRiskLevel, 
        session_context: Optional[Dict]
    ) -> int:
        """위험도별 최소 빈도 요구사항 계산"""
        
        base_requirements = {
            PatternRiskLevel.GLOBAL_SAFE: 2,
            PatternRiskLevel.DOMAIN_MEDIUM: 3,
            PatternRiskLevel.BOOK_HIGH: 5,
            PatternRiskLevel.BATCH_CRITICAL: 8,
        }
        
        base_freq = base_requirements[risk_level]
        
        # 도메인별 조정
        if session_context and "book_domain" in session_context:
            domain = session_context["book_domain"]
            if domain in self.DOMAIN_THRESHOLDS:
                domain_min = self.DOMAIN_THRESHOLDS[domain]["min_frequency"]
                base_freq = max(base_freq, domain_min)
                
        return base_freq

    def _generate_reasoning(
        self,
        structural_risk: float,
        context_dependency: float, 
        destructive_potential: float,
        risk_factors: List[str],
        risk_level: PatternRiskLevel
    ) -> str:
        """위험도 판정 근거 생성"""
        
        reasoning_parts = [
            f"구조적위험: {structural_risk:.2f}",
            f"맥락의존: {context_dependency:.2f}", 
            f"파괴가능: {destructive_potential:.2f}",
        ]
        
        if risk_factors:
            reasoning_parts.append(f"위험요소: {', '.join(risk_factors)}")
            
        reasoning_parts.append(f"최종등급: {risk_level.value}")
        
        return " | ".join(reasoning_parts)

    def _is_cross_language_pattern(self, pattern: str, replacement: str) -> bool:
        """언어간 변환 패턴 체크"""
        korean_pattern = re.compile(r'[가-힣]')
        english_pattern = re.compile(r'[a-zA-Z]')
        
        pattern_has_korean = bool(korean_pattern.search(pattern))
        pattern_has_english = bool(english_pattern.search(pattern))
        replacement_has_korean = bool(korean_pattern.search(replacement))
        replacement_has_english = bool(english_pattern.search(replacement))
        
        return (pattern_has_korean and replacement_has_english) or (pattern_has_english and replacement_has_korean)

    def _is_potential_homophone(self, pattern: str, replacement: str) -> bool:
        """동음이의어 가능성 체크"""
        # 한글 동음이의어 패턴
        korean_homophones = {
            "되": ["되", "돼"], "됩": ["됩", "돼"], "했": ["했", "헀"],
            "데": ["데", "대"], "에": ["에", "애"], "의": ["의", "이"]
        }
        
        for sound, variants in korean_homophones.items():
            if pattern in variants and replacement in variants:
                return True
                
        return False

    def _changes_meaning(self, pattern: str, replacement: str) -> bool:
        """의미 변경 가능성 체크"""
        # 의미를 바꿀 수 있는 변환들
        meaning_changing_pairs = [
            ("안", "않"), ("되", "돼"), ("을", "를"),
            ("이", "가"), ("은", "는"), ("로", "으로")
        ]
        
        for p, r in meaning_changing_pairs:
            if (pattern == p and replacement == r) or (pattern == r and replacement == p):
                return True
                
        return False

    def _reduces_readability(self, pattern: str, replacement: str) -> bool:
        """가독성 저하 가능성 체크"""
        # 가독성을 저하시킬 수 있는 패턴들
        if replacement == "DELETE" and pattern in [".", ",", "!", "?", " "]:
            return True
            
        # 특수문자 삭제
        if pattern.strip() and replacement == "DELETE":
            return True
            
        return False


def create_pattern_risk_analyzer() -> PatternRiskAnalyzer:
    """PatternRiskAnalyzer 인스턴스 생성"""
    return PatternRiskAnalyzer()


if __name__ == "__main__":
    # 테스트 코드
    analyzer = create_pattern_risk_analyzer()
    
    test_patterns = [
        (".", "DELETE", 6, 0.4),
        ("셨", "세", 3, 0.45),
        ("l", "1", 2, 0.8),
        ("되엇", "되었", 4, 0.9),
        ("SPACE_3", "SPACE_1", 10, 0.95),
    ]
    
    print("🔍 패턴 위험도 분석 테스트")
    print("=" * 60)
    
    for pattern, replacement, freq, conf in test_patterns:
        assessment = analyzer.analyze_pattern_risk(pattern, replacement, freq, conf)
        print(f"\n패턴: '{pattern}' → '{replacement}'")
        print(f"위험도: {assessment.risk_level.value}")
        print(f"맥락의존: {assessment.context_dependency:.2f}")
        print(f"파괴가능: {assessment.destructive_potential:.2f}")
        print(f"최소빈도: {assessment.frequency_requirement}")
        print(f"근거: {assessment.reasoning}")