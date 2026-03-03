"""패턴 추천 엔진 - Phase 1.8 Pattern Scope Policy 완료

Phase 1 MVP: 기본 패턴 학습 시스템
Phase 1.5: Session-aware Pattern Learning  
Phase 1.8: Pattern Scope Policy (Overfitting OCR 방지)
"""

# Phase 1 MVP - 기본 패턴 엔진
from .diff_collector import DiffCollector, TextDiff, StageResult
from .pattern_analyzer import PatternAnalyzer, PatternCandidate
from .rule_generator import RuleGenerator

# Phase 1.5 - Session-aware Pattern Learning  
from .session_context import SessionContextGenerator, SessionContext
from .session_aware_analyzer import SessionAwarePatternAnalyzer, SessionAwarePatternCandidate

# Phase 1.8 - Pattern Scope Policy (Overfitting OCR 방지)
from .pattern_risk_analyzer import PatternRiskAnalyzer, PatternRiskLevel, PatternRiskAssessment
from .safety_validator import PatternSafetyValidator, ValidationResult, SafetyValidationReport
from .pattern_scope_policy import PatternScopePolicy, ApplicationPriority, PatternApplication, PolicyDecision

__all__ = [
    # Phase 1 MVP
    "DiffCollector",
    "TextDiff", 
    "StageResult",
    "PatternAnalyzer",
    "PatternCandidate",
    "RuleGenerator",
    
    # Phase 1.5 Session-aware
    "SessionContextGenerator", 
    "SessionContext",
    "SessionAwarePatternAnalyzer", 
    "SessionAwarePatternCandidate",
    
    # Phase 1.8 Pattern Scope Policy
    "PatternRiskAnalyzer", 
    "PatternRiskLevel", 
    "PatternRiskAssessment",
    "PatternSafetyValidator", 
    "ValidationResult", 
    "SafetyValidationReport", 
    "PatternScopePolicy", 
    "ApplicationPriority", 
    "PatternApplication", 
    "PolicyDecision",
]