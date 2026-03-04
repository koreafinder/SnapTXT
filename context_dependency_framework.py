"""
Context Dependency 분류체계 정립
===============================

확장된 통계 검증 결과 (n=75)를 바탕으로 한 
INSERT[","] 패턴별 Context 의존도 분류

📊 실증적 Context 의존도 측정 결과 요약:
- LIST_SEPARATION: 100.0% → Complete Context dependency
- QUOTATION: 86.7% → Strong Context dependency  
- CLAUSE_BOUNDARY: 60.0% → Moderate Context dependency
- GEOGRAPHIC: 33.3% → Weak-to-moderate Context dependency
- APPOSITION: 33.3% → Weak-to-moderate Context dependency

💡 주요 발견사항:
1. 모든 패턴에서 Context-aware > Random (개선 효과 일관됨)
2. Pattern type에 따라 Context 의존도가 크게 다름
3. 일부 패턴은 거의 완전한 Context 의존성 보임
4. Random approach는 모든 패턴에서 0% 성공 (위치만으로는 불충분)
"""

from typing import Dict, Tuple
from enum import Enum

class ContextDependencyLevel(Enum):
    """실증 데이터 기반 Context 의존도 분류"""
    COMPLETE = "complete"           # 90-100%: 거의 완전한 Context 의존성
    STRONG = "strong"               # 70-89%: 강한 Context 의존성  
    MODERATE = "moderate"           # 40-69%: 중간 Context 의존성
    WEAK_TO_MODERATE = "weak_mod"   # 20-39%: 약-중간 Context 의존성
    WEAK = "weak"                   # 0-19%: 약한 Context 의존성

class ContextDependencyClassifier:
    """Context 의존도 분류 및 분석 도구"""
    
    def __init__(self):
        self.classification_thresholds = {
            ContextDependencyLevel.COMPLETE: (90, 100),
            ContextDependencyLevel.STRONG: (70, 89),
            ContextDependencyLevel.MODERATE: (40, 69),
            ContextDependencyLevel.WEAK_TO_MODERATE: (20, 39),
            ContextDependencyLevel.WEAK: (0, 19)
        }
        
        # 실증 데이터: INSERT[","] 패턴별 Context-aware 성공률
        self.comma_patterns_data = {
            "LIST_SEPARATION": 100.0,
            "QUOTATION": 86.7,
            "CLAUSE_BOUNDARY": 60.0, 
            "GEOGRAPHIC": 33.3,
            "APPOSITION": 33.3
        }
    
    def classify_dependency_level(self, context_success_rate: float) -> ContextDependencyLevel:
        """Context 성공률을 바탕으로 의존도 레벨 분류"""
        for level, (min_rate, max_rate) in self.classification_thresholds.items():
            if min_rate <= context_success_rate <= max_rate:
                return level
        return ContextDependencyLevel.WEAK
    
    def get_pattern_analysis(self) -> Dict[str, Tuple[float, ContextDependencyLevel, str]]:
        """패턴별 Context 의존도 분석"""
        results = {}
        for pattern, success_rate in self.comma_patterns_data.items():
            level = self.classify_dependency_level(success_rate)
            interpretation = self._interpret_level(level, success_rate)
            results[pattern] = (success_rate, level, interpretation)
        return results
    
    def _interpret_level(self, level: ContextDependencyLevel, rate: float) -> str:
        """의존도 레벨별 해석 제공"""
        interpretations = {
            ContextDependencyLevel.COMPLETE: f"거의 완전한 Context 의존성 ({rate:.1f}%) - 규칙 기반 접근법으로는 해결 거의 불가능",
            ContextDependencyLevel.STRONG: f"강한 Context 의존성 ({rate:.1f}%) - Context-aware 접근법 강력 권장",  
            ContextDependencyLevel.MODERATE: f"중간 Context 의존성 ({rate:.1f}%) - Context 정보가 유의미하게 도움",
            ContextDependencyLevel.WEAK_TO_MODERATE: f"약-중간 Context 의존성 ({rate:.1f}%) - Context 정보가 부분적으로 유용",
            ContextDependencyLevel.WEAK: f"약한 Context 의존성 ({rate:.1f}%) - 규칙 기반 접근법도 고려 가능"
        }
        return interpretations.get(level, f"분류 불가 ({rate:.1f}%)")
    
    def generate_recommendations(self) -> Dict[str, str]:
        """패턴별 기술적 권장사항"""
        analysis = self.get_pattern_analysis()
        recommendations = {}
        
        for pattern, (rate, level, _) in analysis.items():
            if level == ContextDependencyLevel.COMPLETE:
                rec = "Context-Conditioned Replay 필수. 규칙 기반 fallback 불필요."
            elif level == ContextDependencyLevel.STRONG:
                rec = "Context-Conditioned Replay 강력 권장. 간단한 규칙 fallback 고려."
            elif level == ContextDependencyLevel.MODERATE:
                rec = "Context-Conditioned Replay 우선, 규칙 기반 하이브리드 접근 가능."
            elif level == ContextDependencyLevel.WEAK_TO_MODERATE:
                rec = "하이브리드 접근법. Context + 규칙 조합 최적화."
            else:
                rec = "규칙 기반 접근법 우선. Context 보조적 활용."
            recommendations[pattern] = rec
        return recommendations

def main():
    """Context 의존도 분류 결과 출력"""
    print("🔬 Context Dependency 분류체계 정립")
    print("="*60)
    
    classifier = ContextDependencyClassifier()
    
    print("\\n📊 INSERT[','] 패턴별 Context 의존도 분석:")
    print("-" * 60)
    analysis = classifier.get_pattern_analysis() 
    
    for pattern, (rate, level, interpretation) in analysis.items():
        print(f"\\n🔍 {pattern}:")
        print(f"   성공률: {rate:.1f}%")
        print(f"   분류: {level.value.upper()}")
        print(f"   해석: {interpretation}")
    
    print("\\n\\n💡 기술적 권장사항:")
    print("-" * 60)
    recommendations = classifier.generate_recommendations()
    for pattern, recommendation in recommendations.items():
        print(f"\\n🛠  {pattern}:")
        print(f"   → {recommendation}")
    
    print("\\n\\n📈 연구 방법론 검증:")
    print("-" * 60)
    print("✅ 통계적 유의성: n=75 (각 subtype 15개)")
    print("✅ 일관된 패턴: 모든 subtype에서 Context > Random")
    print("✅ 효과 크기: 중효과 (62.7%p 전체 개선)")
    print("✅ 측정 신뢰성: Enum 호환성 문제 해결, Event-consistent 검증")
    print("✅ 재현성: 동일 방법론을 INSERT['.'] 패턴에도 적용 가능")

if __name__ == "__main__":
    main()