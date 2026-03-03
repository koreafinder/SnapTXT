#!/usr/bin/env python3
"""
Phase 2.4.8: 재현성 테스트 자동화 프레임워크
29샘플에서 확보된 robust 기준을 모든 클러스터링에 자동 적용

목표:
1. Phase 2.5 클러스터링에서 모든 클러스터가 동일한 robust 검증 통과
2. 재현성 계수 > 0.7, P-value < 0.01, Bootstrap + CV 자동화
3. 실시간 검증으로 "살아있는 품질 관리 시스템"
"""

import numpy as np
import json
import os
from typing import List, Dict, Tuple, Optional, Callable, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from abc import ABC, abstractmethod
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from phase_2_4_6_robust_validation import RobustValidationFramework, BootstrapResult
from phase_2_4_7_expanded_validation import ExpandedValidationFramework, ExpandedValidationResult

@dataclass
class ReproducibilityStandard:
    """재현성 검증 표준"""
    min_reproducibility_coefficient: float = 0.7
    max_pvalue: float = 0.01  
    min_effect_size: float = 0.003
    bootstrap_iterations: int = 2000
    cv_folds: int = 5
    min_samples: int = 29
    confidence_level: float = 0.95
    
@dataclass  
class AutoValidationResult:
    """자동 검증 결과"""
    validation_id: str
    tested_component: str  # cluster, rule, pattern 등
    component_config: Dict[str, Any]
    
    # 검증 결과
    passes_reproducibility: bool
    passes_statistical_test: bool  
    passes_effect_size: bool
    overall_pass: bool
    
    # 상세 메트릭
    reproducibility_coefficient: float
    p_value: float
    effect_size: float
    confidence_interval: Tuple[float, float]
    
    # 권장사항
    recommendation: str
    confidence_rating: str  # HIGH/MEDIUM/LOW
    
class ComponentValidator(ABC):
    """검증 대상 컴포넌트의 추상 클래스"""
    
    @abstractmethod
    def extract_performance_metrics(self, samples: List[Any]) -> np.ndarray:
        """컴포넌트의 성능 메트릭 추출 (ΔCER 등)"""
        pass
    
    @abstractmethod
    def get_component_description(self) -> str:
        """컴포넌트 설명"""
        pass

class ClusterValidator(ComponentValidator):
    """클러스터 검증기"""
    
    def __init__(self, cluster_config: Dict):
        self.cluster_config = cluster_config
        
    def extract_performance_metrics(self, samples: List[Any]) -> np.ndarray:
        """클러스터 적용 시 ΔCER 계산"""
        # TODO: 실제 클러스터 적용 로직
        # 현재는 시뮬레이션
        n_samples = len(samples)
        
        # 클러스터 유형별 다른 성능 패턴 시뮬레이션
        cluster_type = self.cluster_config.get('type', 'unknown')
        
        if cluster_type == 'punctuation':
            # 구두점 클러스터: 안정적인 개선
            base_improvement = 0.006
            noise_level = 0.002
        elif cluster_type == 'character':  
            # 문자 클러스터: 가변적인 개선
            base_improvement = 0.004
            noise_level = 0.005
        elif cluster_type == 'layout':
            # 레이아웃 클러스터: 미미한 개선
            base_improvement = 0.001  
            noise_level = 0.003
        else:
            # 일반적인 클러스터
            base_improvement = 0.003
            noise_level = 0.004
            
        # 정규분포 + 약간의 outlier
        metrics = np.random.normal(base_improvement, noise_level, n_samples)
        
        # 5% 확률로 outlier 추가 (현실적)
        outlier_mask = np.random.random(n_samples) < 0.05  
        outliers = np.random.normal(base_improvement * 0.3, noise_level * 1.5, np.sum(outlier_mask))
        metrics[outlier_mask] = outliers
        
        return metrics
        
    def get_component_description(self) -> str:
        cluster_type = self.cluster_config.get('type', 'unknown')
        pattern_count = self.cluster_config.get('pattern_count', 0)
        return f"{cluster_type} cluster ({pattern_count} patterns)"

class RuleValidator(ComponentValidator):
    """개별 규칙 검증기"""
    
    def __init__(self, rule_config: Dict):
        self.rule_config = rule_config
        
    def extract_performance_metrics(self, samples: List[Any]) -> np.ndarray:
        """개별 규칙 적용 시 ΔCER 계산"""
        n_samples = len(samples)
        
        # 규칙 복잡도에 따른 성능 시뮬레이션
        complexity = self.rule_config.get('complexity', 'medium')
        
        if complexity == 'simple':
            # 단순 규칙: 안정적
            base = 0.005
            std = 0.002  
        elif complexity == 'complex':
            # 복잡 규칙: 불안정
            base = 0.007
            std = 0.006
        else:
            # 중간 복잡도
            base = 0.004  
            std = 0.003
            
        return np.random.normal(base, std, n_samples)
        
    def get_component_description(self) -> str:
        pattern = self.rule_config.get('pattern', 'unknown')
        return f"Rule: {pattern}"

class AutoReproducibilityFramework:
    """자동 재현성 검증 프레임워크"""
    
    def __init__(self, standards: ReproducibilityStandard):
        self.standards = standards
        self.validation_history: List[AutoValidationResult] = []
        
        # 기본 검증 엔진들 초기화
        self.robust_validator = RobustValidationFramework(
            bootstrap_iterations=standards.bootstrap_iterations,
            confidence_level=standards.confidence_level,
            effect_size_threshold=standards.min_effect_size,
            alpha=standards.max_pvalue
        )
        
        self.expanded_validator = ExpandedValidationFramework(
            cross_validation_folds=standards.cv_folds,
            bootstrap_iterations=standards.bootstrap_iterations,
            confidence_level=standards.confidence_level,
            effect_size_threshold=standards.min_effect_size
        )
    
    def validate_component(self, component: ComponentValidator, 
                         samples: Optional[List[Any]] = None,
                         validation_id: Optional[str] = None) -> AutoValidationResult:
        """컴포넌트 자동 검증"""
        
        if samples is None:
            samples = self._generate_standard_samples()
        
        if validation_id is None:
            validation_id = f"auto_validation_{len(self.validation_history):04d}"
            
        print(f"🔍 자동 검증 시작: {component.get_component_description()}")
        print(f"📊 샘플 수: {len(samples)}, ID: {validation_id}")
        
        # 1. 성능 메트릭 추출
        metrics = component.extract_performance_metrics(samples)
        
        # 2. Bootstrap 신뢰구간 계산  
        bootstrap_result = self.robust_validator.bootstrap_confidence_interval(metrics)
        
        # 3. Cross-validation 시뮬레이션
        reproducibility_coeff = self._simulate_cross_validation_reproducibility(metrics)
        
        # 4. 각 기준별 통과 여부 확인
        passes_reproducibility = reproducibility_coeff >= self.standards.min_reproducibility_coefficient
        passes_statistical = bootstrap_result.p_value <= self.standards.max_pvalue  
        passes_effect_size = bootstrap_result.effect_size >= self.standards.min_effect_size
        overall_pass = passes_reproducibility and passes_statistical and passes_effect_size
        
        # 5. 권장사항 생성
        recommendation = self._generate_recommendation(
            passes_reproducibility, passes_statistical, passes_effect_size
        )
        
        # 6. 신뢰도 평가
        confidence_rating = self._assess_confidence(
            bootstrap_result, reproducibility_coeff, overall_pass
        )
        
        # 7. 결과 객체 생성
        result = AutoValidationResult(
            validation_id=validation_id,
            tested_component=component.get_component_description(),
            component_config=getattr(component, 'cluster_config', {}) or getattr(component, 'rule_config', {}),
            passes_reproducibility=passes_reproducibility,
            passes_statistical_test=passes_statistical,
            passes_effect_size=passes_effect_size, 
            overall_pass=overall_pass,
            reproducibility_coefficient=reproducibility_coeff,
            p_value=bootstrap_result.p_value,
            effect_size=bootstrap_result.effect_size,
            confidence_interval=bootstrap_result.confidence_interval_95,
            recommendation=recommendation,
            confidence_rating=confidence_rating
        )
        
        # 8. 기록 저장
        self.validation_history.append(result)
        
        # 9. 결과 출력
        self._print_validation_result(result)
        
        return result
    
    def _simulate_cross_validation_reproducibility(self, metrics: np.ndarray) -> float:
        """Cross-validation 재현성 시뮬레이션"""
        
        # K-fold 시뮬레이션
        fold_size = len(metrics) // self.standards.cv_folds
        fold_means = []
        
        for i in range(self.standards.cv_folds):
            start_idx = i * fold_size
            end_idx = start_idx + fold_size
            if i == self.standards.cv_folds - 1:  # 마지막 fold는 나머지 모두
                fold_data = metrics[start_idx:]
            else:
                fold_data = metrics[start_idx:end_idx]
            
            fold_means.append(np.mean(fold_data))
        
        # 재현성 계수: CV 결과의 일관성
        overall_mean = np.mean(fold_means)
        if overall_mean == 0:
            return 0.0
            
        std_cv = np.std(fold_means)
        coefficient_of_variation = std_cv / abs(overall_mean)
        
        # 재현성 계수 = 1 - CV (낮은 변동성 = 높은 재현성)
        reproducibility = max(0.0, 1.0 - coefficient_of_variation)
        
        return min(1.0, reproducibility)  # 1.0으로 제한
        
    def _generate_recommendation(self, passes_repr: bool, passes_stat: bool, passes_effect: bool) -> str:
        """검증 결과 기반 권장사항 생성"""
        
        if passes_repr and passes_stat and passes_effect:
            return "✅ 모든 기준 통과! Phase 2.5에서 안전하게 사용 가능"
        elif passes_stat and passes_effect:
            return "⚠️ 통계적으로는 유의하나 재현성 부족. 더 많은 데이터 필요"
        elif passes_repr and passes_stat:
            return "⚠️ 재현 가능하나 효과 크기 미흡. 임계값 재검토 필요"  
        elif passes_stat:
            return "⚠️ 통계적 유의성만 확보. 재현성과 효과 크기 개선 필요"
        else:
            return "❌ 주요 기준 미충족. 컴포넌트 재설계 필요"
    
    def _assess_confidence(self, bootstrap_result: BootstrapResult, 
                          reproducibility_coeff: float, overall_pass: bool) -> str:
        """신뢰도 평가"""
        
        if overall_pass and bootstrap_result.effect_size > 2.0 and reproducibility_coeff > 0.8:
            return "HIGH"
        elif overall_pass or (bootstrap_result.effect_size > 1.0 and reproducibility_coeff > 0.6):
            return "MEDIUM"
        else:
            return "LOW"
            
    def _generate_standard_samples(self) -> List[Dict]:
        """표준 샘플 데이터 생성"""
        
        samples = []
        for i in range(self.standards.min_samples):
            sample = {
                'id': f'sample_{i:03d}',
                'difficulty': 'easy' if i < 10 else 'medium' if i < 20 else 'hard',
                'domain': 'book_ocr'
            }
            samples.append(sample)
        
        return samples
        
    def _print_validation_result(self, result: AutoValidationResult):
        """검증 결과 출력"""
        
        status_icon = "✅" if result.overall_pass else "❌"
        confidence_icon = {"HIGH": "🔥", "MEDIUM": "👍", "LOW": "😐"}[result.confidence_rating]
        
        print(f"\n{status_icon} 검증 완료: {result.tested_component}")
        print(f"   재현성: {'✅' if result.passes_reproducibility else '❌'} {result.reproducibility_coefficient:.3f}")
        print(f"   통계성: {'✅' if result.passes_statistical_test else '❌'} p={result.p_value:.6f}")  
        print(f"   효과크기: {'✅' if result.passes_effect_size else '❌'} {result.effect_size:.3f}")
        print(f"   신뢰도: {confidence_icon} {result.confidence_rating}")
        print(f"   권장사항: {result.recommendation}")
    
    def batch_validate_clusters(self, cluster_configs: List[Dict]) -> List[AutoValidationResult]:
        """여러 클러스터 일괄 검증"""
        
        print(f"🔄 {len(cluster_configs)}개 클러스터 일괄 검증 시작!")
        print("=" * 50)
        
        results = []
        passed_clusters = []
        
        for i, config in enumerate(cluster_configs):
            cluster_validator = ClusterValidator(config)
            result = self.validate_component(
                cluster_validator, 
                validation_id=f"cluster_batch_{i:02d}"
            )
            results.append(result)
            
            if result.overall_pass:
                passed_clusters.append(config)
        
        # 요약 보고
        pass_rate = len(passed_clusters) / len(cluster_configs)
        print(f"\n" + "=" * 50)
        print(f"🎯 일괄 검증 완료: {len(passed_clusters)}/{len(cluster_configs)} 클러스터 통과")
        print(f"📊 통과율: {pass_rate:.1%}")
        
        if pass_rate >= 0.7:
            print("✅ 전체적으로 양호한 클러스터 품질")
        elif pass_rate >= 0.5:
            print("⚠️ 보통 수준의 클러스터 품질 - 개선 권장")
        else:
            print("❌ 클러스터 품질 부족 - 재설계 필요")
            
        return results
    
    def generate_validation_dashboard(self) -> str:
        """검증 대시보드 생성"""
        
        if not self.validation_history:
            return "📊 검증 기록이 없습니다."
            
        total_validations = len(self.validation_history)
        passed_validations = sum(1 for v in self.validation_history if v.overall_pass)
        
        # 카테고리별 통계
        high_confidence = sum(1 for v in self.validation_history if v.confidence_rating == "HIGH")
        medium_confidence = sum(1 for v in self.validation_history if v.confidence_rating == "MEDIUM")
        low_confidence = sum(1 for v in self.validation_history if v.confidence_rating == "LOW")
        
        dashboard = f"""
# 🔍 재현성 테스트 자동화 대시보드

## 📊 전체 검증 현황
- **총 검증 수행**: {total_validations}회
- **통과**: {passed_validations}회 ({passed_validations/total_validations:.1%})
- **실패**: {total_validations-passed_validations}회 ({(total_validations-passed_validations)/total_validations:.1%})

## 🎯 신뢰도 분포
- 🔥 **HIGH**: {high_confidence}회 ({high_confidence/total_validations:.1%})
- 👍 **MEDIUM**: {medium_confidence}회 ({medium_confidence/total_validations:.1%})  
- 😐 **LOW**: {low_confidence}회 ({low_confidence/total_validations:.1%})

## 📈 최근 검증 결과
"""
        
        # 최근 5개 검증 결과
        recent_validations = self.validation_history[-5:]
        for validation in recent_validations:
            status_icon = "✅" if validation.overall_pass else "❌"
            confidence_icon = {"HIGH": "🔥", "MEDIUM": "👍", "LOW": "😐"}[validation.confidence_rating]
            
            dashboard += f"""
### {status_icon} {validation.tested_component} {confidence_icon}
- **재현성**: {validation.reproducibility_coefficient:.3f}  
- **P-value**: {validation.p_value:.6f}
- **효과크기**: {validation.effect_size:.3f}
"""
        
        return dashboard
    
    def save_validation_report(self, output_dir: str = "validation_results") -> str:
        """검증 보고서 저장"""
        
        Path(output_dir).mkdir(exist_ok=True)
        
        # JSON 기록 저장 (dataclass 호환성 수정)
        json_path = f"{output_dir}/auto_reproducibility_history.json"
        
        def convert_to_serializable(obj):
            """dataclass와 numpy 타입을 JSON serializable로 변환"""
            if isinstance(obj, (bool, np.bool_)):
                return bool(obj)
            elif isinstance(obj, (int, np.integer)):
                return int(obj)
            elif isinstance(obj, (float, np.floating)):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_serializable(v) for v in obj]
            else:
                return obj
        
        history_data = [convert_to_serializable(asdict(v)) for v in self.validation_history]
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
        
        # 대시보드 저장
        dashboard = self.generate_validation_dashboard()
        dashboard_path = f"{output_dir}/validation_dashboard.md"
        
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            f.write(dashboard)
        
        print(f"📁 검증 보고서 저장: {dashboard_path}")
        return dashboard_path

def main():
    """자동 재현성 프레임워크 데모"""
    
    print("🤖 Phase 2.4.8: 재현성 테스트 자동화 프레임워크 시작!")
    print("29샘플 robust 기준을 모든 클러스터에 자동 적용")
    print("=" * 60)
    
    # 29샘플에서 확보한 robust 기준 적용
    standards = ReproducibilityStandard(
        min_reproducibility_coefficient=0.7,    # 29샘플에서 달성한 0.746 기준
        max_pvalue=0.01,                        # 엄격한 통계 기준 유지  
        min_effect_size=0.003,                  # 효과 크기 기준 유지
        bootstrap_iterations=2000,              # 29샘플에서 사용한 설정
        cv_folds=5,                            # 5-fold CV 유지
        min_samples=29,                        # 최소 샘플 수
        confidence_level=0.95                   # 95% 신뢰구간
    )
    
    # 자동화 프레임워크 초기화
    auto_framework = AutoReproducibilityFramework(standards)
    
    # 예시: 여러 클러스터 자동 검증
    example_clusters = [
        {'type': 'punctuation', 'pattern_count': 3, 'complexity': 'simple'},
        {'type': 'character', 'pattern_count': 5, 'complexity': 'medium'},
        {'type': 'layout', 'pattern_count': 2, 'complexity': 'complex'},
        {'type': 'mixed', 'pattern_count': 7, 'complexity': 'medium'}
    ]
    
    # 일괄 검증 실행
    batch_results = auto_framework.batch_validate_clusters(example_clusters)
    
    # 개별 규칙 검증 예시
    print(f"\n📏 개별 규칙 검증 예시...")
    rule_config = {'pattern': "갔 → 회", 'complexity': 'simple'}
    rule_validator = RuleValidator(rule_config)
    rule_result = auto_framework.validate_component(rule_validator, validation_id="rule_example")
    
    # 대시보드 생성 및 저장
    dashboard_path = auto_framework.save_validation_report()
    
    # 최종 요약
    total_tests = len(auto_framework.validation_history)
    passed_tests = sum(1 for v in auto_framework.validation_history if v.overall_pass)
    
    print(f"\n" + "=" * 60)
    print(f"🎯 **자동 재현성 프레임워크 데모 완료!**")
    print(f"📊 총 검증: {total_tests}회, 통과: {passed_tests}회 ({passed_tests/total_tests:.1%})")
    print(f"📄 대시보드: {dashboard_path}")
    print(f"🚀 Phase 2.5 클러스터링에서 모든 클러스터가 이 기준을 통과해야 합니다!")
    
    return passed_tests >= total_tests * 0.6  # 60% 이상 통과율 목표

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)