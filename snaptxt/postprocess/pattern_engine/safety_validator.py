# -*- coding: utf-8 -*-
"""
Phase 1.8: Safety Validator 
패턴 적용 전 안전성을 검증하는 시스템
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
import re
import logging
from .pattern_risk_analyzer import PatternRiskAnalyzer, PatternRiskLevel, PatternRiskAssessment

logger = logging.getLogger(__name__)


class ValidationResult(Enum):
    """검증 결과"""
    SAFE = "safe"                    # 안전, 적용 가능
    CAUTION = "caution"              # 주의, 조건부 적용
    REJECT = "reject"                # 거부, 적용 불가
    INSUFFICIENT_DATA = "insufficient"  # 데이터 부족


@dataclass
class SafetyValidationReport:
    """안전성 검증 리포트"""
    pattern: str
    replacement: str
    validation_result: ValidationResult
    risk_assessment: PatternRiskAssessment
    safety_score: float  # 0.0~1.0, 높을수록 안전
    blocking_reasons: List[str]
    recommendations: List[str]
    required_conditions: List[str]
    fallback_suggestions: List[str]


class PatternSafetyValidator:
    """패턴 적용 안전성을 검증하는 시스템"""
    
    def __init__(self):
        self.risk_analyzer = PatternRiskAnalyzer()
        
        # 절대 금지 패턴 (블랙리스트)
        self.FORBIDDEN_PATTERNS = {
            # 중요 단어 삭제
            "important_word_deletion": [r"^(the|and|of|to|a|in|is|it|you|that|he|was|for|on|are|as|with|his|they)$"],
            # 숫자 완전 변경
            "number_corruption": [r"^\d+$"],
            # 한글 조사 삭제
            "korean_particle_deletion": [r"^(은|는|이|가|을|를|에|의|로|으로|와|과|도|만|부터|까지)$"],
        }
        
        # 강제 승인 패턴 (화이트리스트)
        self.ALWAYS_SAFE_PATTERNS = {
            # 명백한 OCR 오류
            "obvious_ocr_errors": [
                r"^\s+$",  # 공백 정리
                r"^\.{2,}$",  # 다중 점 정리
                r"^[ぁ-ゔ]+$",  # 일본어 잘못 인식
                r"^[！？]{2,}$",  # 중복 문장부호
            ],
            # 안전한 공백/구두점 정리
            "safe_punctuation": [
                r"^\s*\.\s*$",  # 점 주변 공백
                r"^\s*,\s*$",  # 쉼표 주변 공백
                r"^\s*!\s*$",  # 느낌표 주변 공백
                r"^\s*\?\s*$", # 물음표 주변 공백
            ]
        }
        
        # 맥락별 안전 임계값
        self.CONTEXT_THRESHOLDS = {
            PatternRiskLevel.GLOBAL_SAFE: {
                "min_frequency": 2, "min_confidence": 0.6, "min_safety_score": 0.8
            },
            PatternRiskLevel.DOMAIN_MEDIUM: {
                "min_frequency": 3, "min_confidence": 0.7, "min_safety_score": 0.7
            },
            PatternRiskLevel.BOOK_HIGH: {
                "min_frequency": 5, "min_confidence": 0.8, "min_safety_score": 0.6
            },
            PatternRiskLevel.BATCH_CRITICAL: {
                "min_frequency": 8, "min_confidence": 0.85, "min_safety_score": 0.5
            }
        }

    def validate_pattern_safety(
        self,
        pattern: str,
        replacement: str,
        frequency: int,
        confidence: float,
        session_context: Optional[Dict] = None
    ) -> SafetyValidationReport:
        """패턴의 안전성을 종합 검증"""
        
        # 1. 위험도 평가 수행
        risk_assessment = self.risk_analyzer.analyze_pattern_risk(
            pattern, replacement, frequency, confidence, session_context
        )
        
        # 2. 블랙리스트 검사
        blacklist_result = self._check_blacklist(pattern, replacement)
        if blacklist_result[0] != ValidationResult.SAFE:
            return self._create_rejection_report(pattern, replacement, risk_assessment, blacklist_result[1])
        
        # 3. 화이트리스트 검사
        whitelist_result = self._check_whitelist(pattern, replacement)
        if whitelist_result[0] == ValidationResult.SAFE:
            return self._create_approval_report(pattern, replacement, risk_assessment, whitelist_result[1])
        
        # 4. 임계값 기반 검증
        threshold_result = self._check_thresholds(risk_assessment, frequency, confidence)
        
        # 5. 맥락 적합성 검증
        context_result = self._check_context_fitness(risk_assessment, session_context)
        
        # 6. 종합 판정
        final_result = self._make_final_judgment(
            risk_assessment, threshold_result, context_result,
            frequency, confidence, session_context
        )
        
        return final_result

    def _check_blacklist(self, pattern: str, replacement: str) -> Tuple[ValidationResult, List[str]]:
        """블랙리스트 패턴 검사"""
        reasons = []
        
        for category, pattern_list in self.FORBIDDEN_PATTERNS.items():
            for forbidden_pattern in pattern_list:
                if re.match(forbidden_pattern, pattern, re.IGNORECASE):
                    reasons.append(f"금지패턴: {category}")
                    return ValidationResult.REJECT, reasons
                    
        # 완전 삭제 특별 검사
        if replacement in ["DELETE", ""] and len(pattern.strip()) > 0:
            if pattern.strip() in [".", ",", "!", "?", ":", ";"]:
                pass  # 구두점 삭제는 허용
            else:
                reasons.append("중요문자완전삭제")
                return ValidationResult.REJECT, reasons
                
        return ValidationResult.SAFE, reasons

    def _check_whitelist(self, pattern: str, replacement: str) -> Tuple[ValidationResult, List[str]]:
        """화이트리스트 패턴 검사"""
        reasons = []
        
        for category, pattern_list in self.ALWAYS_SAFE_PATTERNS.items():
            for safe_pattern in pattern_list:
                if re.match(safe_pattern, pattern, re.IGNORECASE):
                    reasons.append(f"안전패턴: {category}")
                    return ValidationResult.SAFE, reasons
                    
        return ValidationResult.CAUTION, reasons

    def _check_thresholds(
        self, 
        risk_assessment: PatternRiskAssessment,
        frequency: int,
        confidence: float
    ) -> Tuple[ValidationResult, List[str]]:
        """임계값 기반 검증"""
        
        reasons = []
        risk_level = risk_assessment.risk_level
        thresholds = self.CONTEXT_THRESHOLDS[risk_level]
        
        # 빈도 검사
        if frequency < thresholds["min_frequency"]:
            reasons.append(f"빈도부족: {frequency}<{thresholds['min_frequency']}")
            
        # 신뢰도 검사
        if confidence < thresholds["min_confidence"]:
            reasons.append(f"신뢰도부족: {confidence:.2f}<{thresholds['min_confidence']}")
            
        # 안전점수 계산 및 검사
        safety_score = self._calculate_safety_score(risk_assessment, frequency, confidence)
        if safety_score < thresholds["min_safety_score"]:
            reasons.append(f"안전점수부족: {safety_score:.2f}<{thresholds['min_safety_score']}")
            
        if reasons:
            if len(reasons) >= 2:
                return ValidationResult.REJECT, reasons
            else:
                return ValidationResult.CAUTION, reasons
        else:
            return ValidationResult.SAFE, reasons

    def _check_context_fitness(
        self,
        risk_assessment: PatternRiskAssessment,
        session_context: Optional[Dict]
    ) -> Tuple[ValidationResult, List[str]]:
        """맥락 적합성 검증"""
        
        reasons = []
        
        if not session_context:
            reasons.append("세션컨텍스트없음")
            return ValidationResult.CAUTION, reasons
            
        # 도메인별 적합성 검사
        domain = session_context.get("book_domain")
        if domain and self._is_domain_inappropriate(risk_assessment.pattern, risk_assessment.replacement, domain):
            reasons.append(f"도메인부적합: {domain}")
            
        # 이미지 품질 검사
        image_quality = session_context.get("image_quality", 1.0)
        if image_quality < 0.5 and risk_assessment.risk_level in [PatternRiskLevel.BOOK_HIGH, PatternRiskLevel.BATCH_CRITICAL]:
            reasons.append(f"저품질이미지: {image_quality:.2f}")
            
        # 세션 연속성 검사  
        session_id = session_context.get("book_session_id")
        if not session_id and risk_assessment.risk_level == PatternRiskLevel.BATCH_CRITICAL:
            reasons.append("배치세션없음")
            
        if reasons:
            return ValidationResult.CAUTION, reasons
        else:
            return ValidationResult.SAFE, reasons

    def _make_final_judgment(
        self,
        risk_assessment: PatternRiskAssessment,
        threshold_result: Tuple[ValidationResult, List[str]],
        context_result: Tuple[ValidationResult, List[str]],
        frequency: int,
        confidence: float,
        session_context: Optional[Dict]
    ) -> SafetyValidationReport:
        """종합 판정"""
        
        # 모든 검증 결과 수집
        all_results = [threshold_result[0], context_result[0]]
        all_reasons = threshold_result[1] + context_result[1]
        
        # 최종 판정 로직
        if ValidationResult.REJECT in all_results:
            final_result = ValidationResult.REJECT
        elif all_results.count(ValidationResult.CAUTION) >= 2:
            final_result = ValidationResult.REJECT
        elif ValidationResult.CAUTION in all_results:
            final_result = ValidationResult.CAUTION
        else:
            final_result = ValidationResult.SAFE
            
        # 안전점수 계산
        safety_score = self._calculate_safety_score(risk_assessment, frequency, confidence)
        
        # 권장사항 생성
        recommendations = self._generate_recommendations(risk_assessment, final_result, all_reasons)
        
        # 필요조건 생성
        required_conditions = self._generate_required_conditions(risk_assessment, final_result)
        
        # 대안 제안  
        fallback_suggestions = self._generate_fallback_suggestions(risk_assessment, final_result)
        
        return SafetyValidationReport(
            pattern=risk_assessment.pattern,
            replacement=risk_assessment.replacement,
            validation_result=final_result,
            risk_assessment=risk_assessment,
            safety_score=safety_score,
            blocking_reasons=all_reasons,
            recommendations=recommendations,
            required_conditions=required_conditions,
            fallback_suggestions=fallback_suggestions
        )

    def _calculate_safety_score(
        self, 
        risk_assessment: PatternRiskAssessment,
        frequency: int,
        confidence: float
    ) -> float:
        """안전점수 계산 (0.0~1.0)"""
        
        # 기본 안전점수 = 1.0 - 위험점수
        base_safety = 1.0 - (
            risk_assessment.context_dependency * 0.4 +
            risk_assessment.destructive_potential * 0.6
        )
        
        # 빈도 보정 (더 많이 관찰될수록 안전)
        frequency_factor = min(1.0, frequency / 10.0)
        
        # 신뢰도 보정
        confidence_factor = confidence
        
        # 종합 안전점수
        safety_score = base_safety * 0.6 + frequency_factor * 0.2 + confidence_factor * 0.2
        
        return max(0.0, min(1.0, safety_score))

    def _is_domain_inappropriate(self, pattern: str, replacement: str, domain: str) -> bool:
        """도메인별 부적합 패턴 체크"""
        
        # 학술서에서는 약어/수식 변경 금지
        if domain == "textbook":
            if re.match(r"^[A-Z]{1,3}$", pattern) or re.match(r"^\d+$", pattern):
                return True
                
        # 소설에서는 대화체 변경 주의
        if domain == "novel":
            if pattern in ["요", "죠", "네", "예"]:
                return True
                
        return False

    def _generate_recommendations(
        self,
        risk_assessment: PatternRiskAssessment,
        result: ValidationResult,
        reasons: List[str]
    ) -> List[str]:
        """권장사항 생성"""
        
        recommendations = []
        
        if result == ValidationResult.REJECT:
            recommendations.append("패턴 적용 금지")
            if "빈도부족" in reasons:
                recommendations.append(f"최소 {risk_assessment.frequency_requirement}회 이상 관찰 필요")
            if "신뢰도부족" in reasons:
                recommendations.append("더 높은 신뢰도 데이터 수집 필요")
                
        elif result == ValidationResult.CAUTION:
            recommendations.append("제한적 적용")
            recommendations.append("수동 검토 후 적용")
            if risk_assessment.risk_level == PatternRiskLevel.BATCH_CRITICAL:
                recommendations.append("현재 세션에서만 적용")
                
        else:
            recommendations.append("안전한 적용 가능")
            
        return recommendations

    def _generate_required_conditions(
        self,
        risk_assessment: PatternRiskAssessment,
        result: ValidationResult
    ) -> List[str]:
        """필요조건 생성"""
        
        conditions = []
        
        if result in [ValidationResult.CAUTION, ValidationResult.SAFE]:
            if risk_assessment.risk_level == PatternRiskLevel.BATCH_CRITICAL:
                conditions.append("동일 세션 내에서만 적용")
            elif risk_assessment.risk_level == PatternRiskLevel.BOOK_HIGH:
                conditions.append("동일 책에서만 적용")
            elif risk_assessment.risk_level == PatternRiskLevel.DOMAIN_MEDIUM:
                conditions.append("동일 도메인에서만 적용")
                
            if risk_assessment.context_dependency > 0.7:
                conditions.append("맥락 확인 후 적용")
                
        return conditions

    def _generate_fallback_suggestions(
        self,
        risk_assessment: PatternRiskAssessment,
        result: ValidationResult
    ) -> List[str]:
        """대안 제안"""
        
        suggestions = []
        
        if result == ValidationResult.REJECT:
            if risk_assessment.destructive_potential > 0.5:
                suggestions.append("원본 텍스트 유지")
            else:
                suggestions.append("더 안전한 대체 패턴 탐색")
                
        return suggestions

    def _create_rejection_report(
        self,
        pattern: str,
        replacement: str,
        risk_assessment: PatternRiskAssessment,
        reasons: List[str]
    ) -> SafetyValidationReport:
        """거부 리포트 생성"""
        
        return SafetyValidationReport(
            pattern=pattern,
            replacement=replacement,
            validation_result=ValidationResult.REJECT,
            risk_assessment=risk_assessment,
            safety_score=0.0,
            blocking_reasons=reasons,
            recommendations=["패턴 적용 금지", "블랙리스트 패턴"],
            required_conditions=[],
            fallback_suggestions=["원본 텍스트 유지"]
        )

    def _create_approval_report(
        self,
        pattern: str,
        replacement: str,
        risk_assessment: PatternRiskAssessment,
        reasons: List[str]
    ) -> SafetyValidationReport:
        """승인 리포트 생성"""
        
        return SafetyValidationReport(
            pattern=pattern,
            replacement=replacement,
            validation_result=ValidationResult.SAFE,
            risk_assessment=risk_assessment,
            safety_score=1.0,
            blocking_reasons=[],
            recommendations=["안전한 적용 가능", "화이트리스트 패턴"],
            required_conditions=[],
            fallback_suggestions=[]
        )


def create_safety_validator() -> PatternSafetyValidator:
    """PatternSafetyValidator 인스턴스 생성"""
    return PatternSafetyValidator()


if __name__ == "__main__":
    # 테스트 코드
    validator = create_safety_validator()
    
    test_patterns = [
        (".", "DELETE", 6, 0.4),
        ("셨", "세", 3, 0.45),
        ("the", "DELETE", 2, 0.9),  # 위험한 패턴
        ("SPACE_3", "SPACE_1", 10, 0.95),  # 안전한 패턴
        ("l", "1", 2, 0.8),  # 고위험 패턴
    ]
    
    print("🛡️ 패턴 안전성 검증 테스트")
    print("=" * 60)
    
    for pattern, replacement, freq, conf in test_patterns:
        report = validator.validate_pattern_safety(pattern, replacement, freq, conf)
        print(f"\n패턴: '{pattern}' → '{replacement}'")
        print(f"검증결과: {report.validation_result.value}")
        print(f"안전점수: {report.safety_score:.2f}")
        print(f"위험등급: {report.risk_assessment.risk_level.value}")
        if report.blocking_reasons:
            print(f"차단사유: {', '.join(report.blocking_reasons)}")
        if report.recommendations:
            print(f"권장사항: {', '.join(report.recommendations)}")