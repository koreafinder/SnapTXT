# -*- coding: utf-8 -*-
"""
Phase 1.8: Pattern Scope Policy
패턴의 적용 범위와 우선순위를 관리하는 정책 엔진
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
import logging
from .pattern_risk_analyzer import PatternRiskAnalyzer, PatternRiskLevel
from .safety_validator import PatternSafetyValidator, ValidationResult, SafetyValidationReport

logger = logging.getLogger(__name__)


class ApplicationPriority(Enum):
    """패턴 적용 우선순위"""
    BATCH_HIGHEST = "batch"      # 배치별 - 최우선
    BOOK_HIGH = "book"          # 책별 - 높음  
    DOMAIN_MEDIUM = "domain"    # 도메인별 - 중간
    GLOBAL_LOWEST = "global"    # 전역 - 최하위


@dataclass
class PatternApplication:
    """패턴 적용 정보"""
    pattern: str
    replacement: str
    priority: ApplicationPriority
    risk_level: PatternRiskLevel
    validation_report: SafetyValidationReport
    applicable_contexts: List[str]
    frequency: int
    confidence: float
    last_applied: Optional[str] = None
    success_count: int = 0
    failure_count: int = 0


@dataclass
class PolicyDecision:
    """정책 결정 결과"""
    approved_patterns: List[PatternApplication]
    rejected_patterns: List[PatternApplication]
    conditional_patterns: List[PatternApplication]
    decision_reasoning: str
    safety_summary: str
    performance_impact: str


class PatternScopePolicy:
    """패턴 적용 범위와 우선순위를 관리하는 정책 엔진"""
    
    def __init__(self):
        self.risk_analyzer = PatternRiskAnalyzer()
        self.safety_validator = PatternSafetyValidator()
        
        # 우선순위 순서 (높음 → 낮음)  
        self.PRIORITY_ORDER = [
            ApplicationPriority.BATCH_HIGHEST,
            ApplicationPriority.BOOK_HIGH,
            ApplicationPriority.DOMAIN_MEDIUM,
            ApplicationPriority.GLOBAL_LOWEST,
        ]
        
        # 컨텍스트별 적용 정책
        self.CONTEXT_POLICIES = {
            "same_batch": {
                "allowed_priorities": [ApplicationPriority.BATCH_HIGHEST],
                "max_patterns": 5,
                "require_high_confidence": True
            },
            "same_book": {
                "allowed_priorities": [ApplicationPriority.BATCH_HIGHEST, ApplicationPriority.BOOK_HIGH],
                "max_patterns": 10,
                "require_high_confidence": False
            },
            "same_domain": {
                "allowed_priorities": [
                    ApplicationPriority.BATCH_HIGHEST,
                    ApplicationPriority.BOOK_HIGH,
                    ApplicationPriority.DOMAIN_MEDIUM
                ],
                "max_patterns": 15,
                "require_high_confidence": False
            },
            "global": {
                "allowed_priorities": self.PRIORITY_ORDER,
                "max_patterns": 20,
                "require_high_confidence": False
            }
        }
        
        # 성능 임계값
        self.PERFORMANCE_LIMITS = {
            "max_total_patterns": 20,
            "max_high_risk_patterns": 3,
            "max_processing_time_ms": 50
        }

    def evaluate_patterns(
        self,
        pattern_candidates: List[Tuple[str, str, int, float]],  # (pattern, replacement, frequency, confidence)
        session_context: Optional[Dict] = None
    ) -> PolicyDecision:
        """패턴들을 평가하고 적용 정책을 결정"""
        
        logger.info(f"🔍 {len(pattern_candidates)}개 패턴 정책 평가 시작")
        
        # 1. 모든 패턴에 대해 안전성 검증 수행
        validated_patterns = []
        for pattern, replacement, frequency, confidence in pattern_candidates:
            validation_report = self.safety_validator.validate_pattern_safety(
                pattern, replacement, frequency, confidence, session_context
            )
            
            # 우선순위 결정
            priority = self._determine_application_priority(
                validation_report.risk_assessment.risk_level, session_context
            )
            
            # 적용 가능한 컨텍스트 결정
            applicable_contexts = self._determine_applicable_contexts(
                priority, validation_report, session_context
            )
            
            validated_patterns.append(PatternApplication(
                pattern=pattern,
                replacement=replacement,
                priority=priority,
                risk_level=validation_report.risk_assessment.risk_level,
                validation_report=validation_report,
                applicable_contexts=applicable_contexts,
                frequency=frequency,
                confidence=confidence
            ))
        
        # 2. 정책에 따른 분류
        approved, rejected, conditional = self._classify_patterns(
            validated_patterns, session_context
        )
        
        # 3. 우선순위 정렬
        approved.sort(key=lambda x: (self.PRIORITY_ORDER.index(x.priority), -x.confidence))
        conditional.sort(key=lambda x: (self.PRIORITY_ORDER.index(x.priority), -x.confidence))
        
        # 4. 성능 제한 적용
        approved = self._apply_performance_limits(approved)
        
        # 5. 결정 근거 생성
        decision_reasoning = self._generate_decision_reasoning(approved, rejected, conditional)
        safety_summary = self._generate_safety_summary(approved, rejected, conditional)
        performance_impact = self._estimate_performance_impact(approved)
        
        decision = PolicyDecision(
            approved_patterns=approved,
            rejected_patterns=rejected,
            conditional_patterns=conditional,
            decision_reasoning=decision_reasoning,
            safety_summary=safety_summary,
            performance_impact=performance_impact
        )
        
        logger.info(f"✅ 정책 평가 완료: 승인 {len(approved)}, 거부 {len(rejected)}, 조건부 {len(conditional)}")
        return decision

    def get_applicable_patterns(
        self,
        current_context: Dict,
        pattern_applications: List[PatternApplication]
    ) -> List[PatternApplication]:
        """현재 컨텍스트에 적용 가능한 패턴들 반환"""
        
        applicable = []
        
        # 컨텍스트 분석
        context_type = self._analyze_context_type(current_context)
        policy = self.CONTEXT_POLICIES.get(context_type, self.CONTEXT_POLICIES["global"])
        
        for app in pattern_applications:
            # 우선순위 검사
            if app.priority not in policy["allowed_priorities"]:
                continue
                
            # 컨텍스트 적합성 검사
            if not self._is_context_compatible(app, current_context):
                continue
                
            # 신뢰도 검사
            if policy["require_high_confidence"] and app.confidence < 0.8:
                continue
                
            # 검증 결과 검사
            if app.validation_report.validation_result == ValidationResult.REJECT:
                continue
                
            applicable.append(app)
        
        # 우선순위 정렬 및 개수 제한
        applicable.sort(key=lambda x: (self.PRIORITY_ORDER.index(x.priority), -x.confidence))
        
        return applicable[:policy["max_patterns"]]

    def _determine_application_priority(
        self,
        risk_level: PatternRiskLevel,
        session_context: Optional[Dict]
    ) -> ApplicationPriority:
        """위험도에 따른 적용 우선순위 결정"""
        
        # 위험도가 높을수록 우선순위도 높아짐 (더 제한적 적용)
        if risk_level == PatternRiskLevel.BATCH_CRITICAL:
            return ApplicationPriority.BATCH_HIGHEST
        elif risk_level == PatternRiskLevel.BOOK_HIGH:
            return ApplicationPriority.BOOK_HIGH
        elif risk_level == PatternRiskLevel.DOMAIN_MEDIUM:
            return ApplicationPriority.DOMAIN_MEDIUM
        else:  # GLOBAL_SAFE
            return ApplicationPriority.GLOBAL_LOWEST

    def _determine_applicable_contexts(
        self,
        priority: ApplicationPriority,
        validation_report: SafetyValidationReport,
        session_context: Optional[Dict]
    ) -> List[str]:
        """적용 가능한 컨텍스트 결정"""
        
        contexts = []
        
        # 우선순위에 따른 기본 컨텍스트
        if priority == ApplicationPriority.BATCH_HIGHEST:
            if session_context and "capture_batch_id" in session_context:
                contexts.append(f"batch:{session_context['capture_batch_id']}")
        elif priority == ApplicationPriority.BOOK_HIGH:
            if session_context and "book_session_id" in session_context:
                contexts.append(f"book:{session_context['book_session_id']}")
        elif priority == ApplicationPriority.DOMAIN_MEDIUM:
            if session_context and "book_domain" in session_context:
                contexts.append(f"domain:{session_context['book_domain']}")
        else:  # GLOBAL_LOWEST
            contexts.append("global:all")
        
        # 추가 제약조건 적용
        for condition in validation_report.required_conditions:
            if "동일 세션" in condition:
                contexts = [ctx for ctx in contexts if "batch:" in ctx]
            elif "동일 책" in condition:
                contexts = [ctx for ctx in contexts if "batch:" in ctx or "book:" in ctx]
            elif "동일 도메인" in condition:
                contexts = [ctx for ctx in contexts if "global:" not in ctx]
                
        return contexts

    def _classify_patterns(
        self,
        validated_patterns: List[PatternApplication],
        session_context: Optional[Dict]
    ) -> Tuple[List[PatternApplication], List[PatternApplication], List[PatternApplication]]:
        """패턴을 승인/거부/조건부로 분류"""
        
        approved = []
        rejected = []
        conditional = []
        
        for pattern_app in validated_patterns:
            validation_result = pattern_app.validation_report.validation_result
            
            if validation_result == ValidationResult.SAFE:
                approved.append(pattern_app)
            elif validation_result == ValidationResult.REJECT:
                rejected.append(pattern_app)
            elif validation_result == ValidationResult.CAUTION:
                # 조건부 승인 여부 추가 검토
                if self._should_conditionally_approve(pattern_app, session_context):
                    conditional.append(pattern_app)
                else:
                    rejected.append(pattern_app)
            else:  # INSUFFICIENT_DATA
                rejected.append(pattern_app)
                
        return approved, rejected, conditional

    def _should_conditionally_approve(
        self,
        pattern_app: PatternApplication,
        session_context: Optional[Dict]
    ) -> bool:
        """조건부 승인 여부 결정"""
        
        # 높은 신뢰도면 조건부 승인
        if pattern_app.confidence >= 0.8:
            return True
            
        # 충분한 빈도면 조건부 승인
        if pattern_app.frequency >= pattern_app.validation_report.risk_assessment.frequency_requirement:
            return True
            
        # 배치 레벨이고 세션이 있으면 조건부 승인
        if (pattern_app.priority == ApplicationPriority.BATCH_HIGHEST and 
            session_context and "capture_batch_id" in session_context):
            return True
            
        return False

    def _apply_performance_limits(
        self,
        approved_patterns: List[PatternApplication]
    ) -> List[PatternApplication]:
        """성능 제한 적용"""
        
        # 총 패턴 수 제한
        if len(approved_patterns) > self.PERFORMANCE_LIMITS["max_total_patterns"]:
            approved_patterns = approved_patterns[:self.PERFORMANCE_LIMITS["max_total_patterns"]]
            
        # 고위험 패턴 수 제한
        high_risk_count = 0
        filtered_patterns = []
        
        for pattern in approved_patterns:
            if pattern.risk_level in [PatternRiskLevel.BOOK_HIGH, PatternRiskLevel.BATCH_CRITICAL]:
                if high_risk_count >= self.PERFORMANCE_LIMITS["max_high_risk_patterns"]:
                    continue
                high_risk_count += 1
                
            filtered_patterns.append(pattern)
            
        return filtered_patterns

    def _analyze_context_type(self, context: Dict) -> str:
        """현재 컨텍스트 타입 분석"""
        
        if "capture_batch_id" in context:
            return "same_batch"
        elif "book_session_id" in context:
            return "same_book"
        elif "book_domain" in context:
            return "same_domain"
        else:
            return "global"

    def _is_context_compatible(
        self,
        pattern_app: PatternApplication,
        current_context: Dict
    ) -> bool:
        """패턴이 현재 컨텍스트와 호환되는지 확인"""
        
        for applicable_context in pattern_app.applicable_contexts:
            context_type, context_value = applicable_context.split(":", 1)
            
            if context_type == "batch":
                if current_context.get("capture_batch_id") == context_value:
                    return True
            elif context_type == "book":
                if current_context.get("book_session_id") == context_value:
                    return True
            elif context_type == "domain":
                if current_context.get("book_domain") == context_value:
                    return True
            elif context_type == "global":
                return True
                
        return False

    def _generate_decision_reasoning(
        self,
        approved: List[PatternApplication],
        rejected: List[PatternApplication], 
        conditional: List[PatternApplication]
    ) -> str:
        """결정 근거 생성"""
        
        reasoning_parts = [
            f"승인: {len(approved)}개 패턴",
            f"거부: {len(rejected)}개 패턴",
            f"조건부: {len(conditional)}개 패턴",
        ]
        
        if approved:
            priority_dist = {}
            for app in approved:
                priority_dist[app.priority.value] = priority_dist.get(app.priority.value, 0) + 1
            priority_str = ", ".join([f"{k}: {v}개" for k, v in priority_dist.items()])
            reasoning_parts.append(f"우선순위분포: {priority_str}")
            
        if rejected:
            reject_reasons = set()
            for app in rejected:
                reject_reasons.update(app.validation_report.blocking_reasons)
            if reject_reasons:
                reasoning_parts.append(f"거부사유: {', '.join(list(reject_reasons)[:3])}")
                
        return " | ".join(reasoning_parts)

    def _generate_safety_summary(
        self,
        approved: List[PatternApplication],
        rejected: List[PatternApplication],
        conditional: List[PatternApplication]
    ) -> str:
        """안전성 요약 생성"""
        
        if not approved:
            return "적용할 안전한 패턴 없음"
            
        avg_safety = sum(app.validation_report.safety_score for app in approved) / len(approved)
        high_risk_count = len([app for app in approved if app.risk_level in [PatternRiskLevel.BOOK_HIGH, PatternRiskLevel.BATCH_CRITICAL]])
        
        summary_parts = [
            f"평균안전도: {avg_safety:.2f}",
            f"고위험패턴: {high_risk_count}개",
        ]
        
        if high_risk_count > 0:
            summary_parts.append("주의깊은 모니터링 필요")
        else:
            summary_parts.append("안전한 적용 가능")
            
        return " | ".join(summary_parts)

    def _estimate_performance_impact(self, approved: List[PatternApplication]) -> str:
        """성능 영향 추정"""
        
        if not approved:
            return "성능영향없음"
            
        # 패턴 복잡도 기반 예상 처리시간
        total_complexity = sum(len(app.pattern) + len(app.replacement) for app in approved)
        estimated_time_ms = min(total_complexity * 0.1, self.PERFORMANCE_LIMITS["max_processing_time_ms"])
        
        impact_parts = [
            f"예상처리시간: {estimated_time_ms:.1f}ms",
            f"패턴수: {len(approved)}개",
        ]
        
        if estimated_time_ms > 30:
            impact_parts.append("성능영향있음")
        else:
            impact_parts.append("성능영향미미")
            
        return " | ".join(impact_parts)


def create_pattern_scope_policy() -> PatternScopePolicy:
    """PatternScopePolicy 인스턴스 생성"""
    return PatternScopePolicy()


if __name__ == "__main__":
    # 테스트 코드
    policy = create_pattern_scope_policy()
    
    test_patterns = [
        (".", "DELETE", 6, 0.4),
        ("셨", "세", 3, 0.45),
        ("SPACE_3", "SPACE_1", 10, 0.95),
        ("되엇", "되었", 4, 0.9),
        ("l", "1", 2, 0.8),
    ]
    
    test_context = {
        "book_session_id": "20260302_book_test_session01",
        "book_domain": "textbook",
        "capture_batch_id": "batch_001",
        "image_quality": 0.8
    }
    
    print("🎯 패턴 범위 정책 테스트")
    print("=" * 60)
    
    decision = policy.evaluate_patterns(test_patterns, test_context)
    
    print(f"\n📊 정책 결정 결과:")
    print(f"승인된 패턴: {len(decision.approved_patterns)}개")
    print(f"거부된 패턴: {len(decision.rejected_patterns)}개")  
    print(f"조건부 패턴: {len(decision.conditional_patterns)}개")
    
    print(f"\n🔍 결정 근거: {decision.decision_reasoning}")
    print(f"🛡️ 안전성 요약: {decision.safety_summary}")
    print(f"⚡ 성능 영향: {decision.performance_impact}")
    
    print(f"\n✅ 승인된 패턴들:")
    for app in decision.approved_patterns:
        print(f"  '{app.pattern}' → '{app.replacement}' ({app.priority.value}, 신뢰도: {app.confidence:.2f})")