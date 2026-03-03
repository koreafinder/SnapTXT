#!/usr/bin/env python3
"""
Phase 2.4.5: Rule Contribution Analysis Engine
각 교정 규칙의 개별 기여도 자동 측정 및 품질 분류

Purpose: 
- 규칙별 단독 A/B 테스트 자동화
- Beneficial/Neutral/Harmful 규칙 자동 분류
- ΔCER 정량 측정으로 품질 통제

이게 없으면 Phase 2.5에서 "쓰레기 규칙까지 클러스터링"할 위험 80%
"""

import logging
import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
import statistics

# Character Error Rate 계산
import difflib

log = logging.getLogger(__name__)

@dataclass
class RulePerformance:
    """개별 규칙의 성능 측정 결과"""
    rule_id: str
    pattern: str
    replacement: str
    
    # 개별 적용 결과
    delta_cer_all: float          # 전체 CER 변화량
    delta_cer_space: float        # 공백 오류 CER 변화량  
    delta_cer_punct: float        # 구두점 오류 CER 변화량
    delta_cer_char: float         # 문자 오류 CER 변화량
    
    # 적용 통계
    applications_count: int       # 실제 적용된 횟수
    false_positive_rate: float    # 잘못 교정한 비율
    coverage: float               # 전체 오류 중 다룬 비율
    
    # 분류 결과
    status: str                   # Beneficial/Neutral/Harmful
    confidence: float             # 분류 신뢰도
    auto_enable: bool            # 자동 활성화 가능 여부
    
    # 상세 분석
    side_effects: List[str]       # 부작용 목록
    context_dependency: float     # 문맥 의존성 점수 (0-1)
    robustness_score: float      # 다른 텍스트에서 안정성 (0-1)

@dataclass  
class RuleContributionReport:
    """전체 규칙 기여도 분석 보고서"""
    analysis_id: str
    generated_at: str
    test_dataset_size: int
    
    rule_performances: List[RulePerformance]
    
    # 전체 통계
    beneficial_count: int
    neutral_count: int  
    harmful_count: int
    
    # 추천 사항
    recommended_rules: List[str]   # 활성화 추천 규칙 ID들
    disabled_rules: List[str]      # 비활성화 추천 규칙 ID들
    
    # 품질 지표
    overall_improvement: float     # 전체 개선량
    quality_score: float          # 규칙셋 품질 점수 (0-100)

class RuleContributionAnalyzer:
    """규칙별 기여도 분석 엔진"""
    
    def __init__(self):
        self.test_samples = []
        self.ground_truths = []
        
    def add_test_sample(self, ocr_text: str, ground_truth: str):
        """테스트 샘플 추가"""
        self.test_samples.append(ocr_text)
        self.ground_truths.append(ground_truth)
        
    def calculate_cer(self, predicted: str, ground_truth: str) -> float:
        """Character Error Rate 계산"""
        if not ground_truth:
            return 0.0
            
        # 문자 단위 edit distance 계산
        operations = list(difflib.ndiff(predicted, ground_truth))
        
        insertions = sum(1 for op in operations if op.startswith('+ '))
        deletions = sum(1 for op in operations if op.startswith('- '))
        
        total_errors = insertions + deletions
        return total_errors / len(ground_truth)
    
    def apply_single_rule(self, text: str, rule_dict: Dict) -> str:
        """단일 규칙 적용"""
        pattern = rule_dict['pattern']
        replacement = rule_dict['replacement']
        
        try:
            corrected = re.sub(pattern, replacement, text)
            return corrected
        except Exception as e:
            log.warning(f"규칙 적용 실패 {pattern}: {str(e)}")
            return text
    
    def analyze_rule_categories(self, original: str, corrected: str, ground_truth: str) -> Dict[str, float]:
        """카테고리별 CER 변화량 분석"""
        
        # 공백 관련 오류만 추출
        space_errors_orig = self._extract_space_errors(original, ground_truth)
        space_errors_corr = self._extract_space_errors(corrected, ground_truth)
        
        # 구두점 관련 오류만 추출  
        punct_errors_orig = self._extract_punct_errors(original, ground_truth)
        punct_errors_corr = self._extract_punct_errors(corrected, ground_truth)
        
        # 문자 관련 오류만 추출
        char_errors_orig = self._extract_char_errors(original, ground_truth) 
        char_errors_corr = self._extract_char_errors(corrected, ground_truth)
        
        return {
            'space': len(space_errors_orig) - len(space_errors_corr),
            'punct': len(punct_errors_orig) - len(punct_errors_corr), 
            'char': len(char_errors_orig) - len(char_errors_corr)
        }
    
    def _extract_space_errors(self, text: str, ground_truth: str) -> List[int]:
        """공백 관련 오류만 추출"""
        errors = []
        matcher = difflib.SequenceMatcher(None, text, ground_truth)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != 'equal':
                text_part = text[i1:i2]
                gt_part = ground_truth[j1:j2]
                
                # 공백 관련 오류인지 판단
                if ' ' in text_part or ' ' in gt_part:
                    errors.append(i1)
        
        return errors
    
    def _extract_punct_errors(self, text: str, ground_truth: str) -> List[int]:
        """구두점 관련 오류만 추출"""  
        errors = []
        punct_chars = set('.,!?;:""\'\'()[]{}…․·-–—')
        matcher = difflib.SequenceMatcher(None, text, ground_truth)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != 'equal':
                text_part = text[i1:i2]
                gt_part = ground_truth[j1:j2]
                
                # 구두점 관련 오류인지 판단
                if (any(c in punct_chars for c in text_part) or 
                    any(c in punct_chars for c in gt_part)):
                    errors.append(i1)
        
        return errors
    
    def _extract_char_errors(self, text: str, ground_truth: str) -> List[int]:
        """문자 관련 오류만 추출"""
        errors = []
        matcher = difflib.SequenceMatcher(None, text, ground_truth)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != 'equal':
                text_part = text[i1:i2]
                gt_part = ground_truth[j1:j2]
                
                # 일반 문자 오류 (공백, 구두점 제외)
                if not (' ' in text_part or ' ' in gt_part):
                    punct_chars = set('.,!?;:""\'\'()[]{}…․·-–—')
                    if not (any(c in punct_chars for c in text_part) or 
                           any(c in punct_chars for c in gt_part)):
                        errors.append(i1)
        
        return errors
    
    def analyze_single_rule(self, rule_dict: Dict) -> RulePerformance:
        """단일 규칙의 기여도 분석"""
        
        rule_id = rule_dict.get('id', 'unknown')
        pattern = rule_dict['pattern']
        replacement = rule_dict['replacement']
        
        log.info(f"🔍 규칙 {rule_id} 분석 중: '{pattern}' → '{replacement}'")
        
        # 전체 테스트 샘플에 대해 규칙 적용 전/후 비교
        cer_deltas_all = []
        cer_deltas_space = []
        cer_deltas_punct = []
        cer_deltas_char = []
        
        applications_count = 0
        false_positives = 0
        
        for original, ground_truth in zip(self.test_samples, self.ground_truths):
            # 규칙 적용 전 CER
            cer_before = self.calculate_cer(original, ground_truth)
            
            # 규칙 적용
            corrected = self.apply_single_rule(original, rule_dict)
            
            # 실제로 텍스트가 변했나 확인
            if corrected != original:
                applications_count += 1
                
                # 변화가 ground truth와 더 가까워졌나 확인
                cer_after = self.calculate_cer(corrected, ground_truth)
                
                if cer_after > cer_before:
                    false_positives += 1
            
            # 규칙 적용 후 CER  
            cer_after = self.calculate_cer(corrected, ground_truth)
            
            # CER 변화량 (음수면 개선, 양수면 악화)
            cer_delta = cer_before - cer_after
            cer_deltas_all.append(cer_delta)
            
            # 카테고리별 변화량 분석
            category_changes = self.analyze_rule_categories(original, corrected, ground_truth)
            cer_deltas_space.append(category_changes['space'])
            cer_deltas_punct.append(category_changes['punct'])
            cer_deltas_char.append(category_changes['char'])
        
        # 통계 계산
        avg_delta_all = statistics.mean(cer_deltas_all) if cer_deltas_all else 0.0
        avg_delta_space = statistics.mean(cer_deltas_space) if cer_deltas_space else 0.0
        avg_delta_punct = statistics.mean(cer_deltas_punct) if cer_deltas_punct else 0.0
        avg_delta_char = statistics.mean(cer_deltas_char) if cer_deltas_char else 0.0
        
        false_positive_rate = false_positives / max(1, applications_count)
        coverage = applications_count / len(self.test_samples)
        
        # 규칙 분류: Beneficial/Neutral/Harmful
        status, confidence, auto_enable = self._classify_rule(
            avg_delta_all, false_positive_rate, coverage, applications_count
        )
        
        # 부작용 분석
        side_effects = self._analyze_side_effects(rule_dict, cer_deltas_all)
        
        # 문맥 의존성 및 견고성 점수
        context_dependency = self._calculate_context_dependency(rule_dict, cer_deltas_all)
        robustness_score = self._calculate_robustness(cer_deltas_all)
        
        performance = RulePerformance(
            rule_id=str(rule_id),
            pattern=pattern,
            replacement=replacement,
            delta_cer_all=avg_delta_all,
            delta_cer_space=avg_delta_space,
            delta_cer_punct=avg_delta_punct,
            delta_cer_char=avg_delta_char,
            applications_count=applications_count,
            false_positive_rate=false_positive_rate,
            coverage=coverage,
            status=status,
            confidence=confidence,
            auto_enable=auto_enable,
            side_effects=side_effects,
            context_dependency=context_dependency,
            robustness_score=robustness_score
        )
        
        log.info(f"   ✅ 규칙 {rule_id} 분석 완료: {status} (ΔCER: {avg_delta_all:+.3f})")
        
        return performance
    
    def _classify_rule(self, avg_delta: float, false_positive_rate: float, 
                      coverage: float, applications: int) -> Tuple[str, float, bool]:
        """규칙을 Beneficial/Neutral/Harmful로 분류"""
        
        # Harmful 조건들
        if avg_delta < -0.01:  # CER 0.1%p 이상 악화
            return "Harmful", 0.95, False
            
        if false_positive_rate > 0.3:  # false positive 30% 이상
            return "Harmful", 0.90, False
            
        if applications == 0:  # 아예 적용 안됨
            return "Neutral", 0.80, False
        
        # Beneficial 조건들  
        if avg_delta > 0.005 and false_positive_rate < 0.1:  # 0.5%p 개선 + low FP
            return "Beneficial", 0.95, True
            
        if avg_delta > 0.002 and coverage > 0.1:  # 0.2%p 개선 + 적용율 10%+
            return "Beneficial", 0.85, True
        
        # Neutral (애매한 경우)
        if abs(avg_delta) <= 0.002:  # 거의 변화 없음
            return "Neutral", 0.75, False
            
        # 약간 좋지만 확신 부족
        if avg_delta > 0:
            return "Beneficial", 0.60, False
        else:
            return "Neutral", 0.60, False
    
    def _analyze_side_effects(self, rule_dict: Dict, cer_deltas: List[float]) -> List[str]:
        """부작용 분석"""
        side_effects = []
        
        # 편차가 큰 경우 (일관성 부족)
        if len(cer_deltas) > 1:
            std_dev = statistics.stdev(cer_deltas)
            if std_dev > 0.05:
                side_effects.append(f"높은 변동성 (std: {std_dev:.3f})")
        
        # 패턴이 너무 특정적인 경우
        pattern = rule_dict['pattern']
        if len(pattern) > 20:
            side_effects.append("과도하게 특정적인 패턴")
        
        return side_effects
    
    def _calculate_context_dependency(self, rule_dict: Dict, cer_deltas: List[float]) -> float:
        """문맥 의존성 계산 (높을수록 위험)"""
        
        # 패턴의 복잡도 기반 휴리스틱
        pattern = rule_dict['pattern']
        
        # 단순한 문자 교체는 낮은 의존성
        if len(pattern) <= 3 and not re.search(r'[\\()\[\]{}^$*+?|]', pattern):
            base_dependency = 0.2
        # 복잡한 regex는 높은 의존성  
        elif re.search(r'[\\()\[\]{}^$*+?|]', pattern):
            base_dependency = 0.8
        else:
            base_dependency = 0.5
        
        # 성능 변동성이 클수록 의존성 높음
        if len(cer_deltas) > 1:
            std_dev = statistics.stdev(cer_deltas)
            dependency_penalty = min(0.3, std_dev * 6)
            return min(1.0, base_dependency + dependency_penalty)
        
        return base_dependency
    
    def _calculate_robustness(self, cer_deltas: List[float]) -> float:
        """견고성 점수 (일관된 성능일수록 높음)"""
        
        if not cer_deltas:
            return 0.0
        
        # 평균이 양수이고 편차가 작을수록 견고함
        mean_delta = statistics.mean(cer_deltas)
        
        if len(cer_deltas) == 1:
            return 0.7 if mean_delta > 0 else 0.3
        
        std_dev = statistics.stdev(cer_deltas)
        
        # 일관되게 좋은 성능
        if mean_delta > 0.001 and std_dev < 0.02:
            return 0.9
        # 평균적으로 좋지만 변동성 있음
        elif mean_delta > 0 and std_dev < 0.05:
            return 0.7
        # 일관되게 나쁜 성능
        elif mean_delta < -0.001 and std_dev < 0.02:
            return 0.1
        # 매우 불안정함  
        elif std_dev > 0.1:
            return 0.2
        else:
            return 0.5
    
    def analyze_rule_set(self, rules: List[Dict]) -> RuleContributionReport:
        """전체 규칙셋 분석"""
        
        log.info(f"🚀 규칙셋 전체 분석 시작: {len(rules)}개 규칙, {len(self.test_samples)}개 샘플")
        
        performances = []
        
        for rule in rules:
            performance = self.analyze_single_rule(rule)
            performances.append(performance)
        
        # 전체 통계 계산
        beneficial = [p for p in performances if p.status == "Beneficial"]
        neutral = [p for p in performances if p.status == "Neutral"]
        harmful = [p for p in performances if p.status == "Harmful"]
        
        recommended_rules = [p.rule_id for p in beneficial if p.auto_enable]
        disabled_rules = [p.rule_id for p in harmful]
        
        # 전체 개선량 (권장 규칙들만)
        if recommended_rules:
            overall_improvement = sum(p.delta_cer_all for p in performances 
                                    if p.rule_id in recommended_rules)
        else:
            overall_improvement = 0.0
        
        # 품질 점수 (좋은 규칙 비율 기반)
        if performances:
            quality_score = (len(beneficial) / len(performances)) * 100
        else:
            quality_score = 0.0
        
        report = RuleContributionReport(
            analysis_id=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            generated_at=datetime.now().isoformat(),
            test_dataset_size=len(self.test_samples),
            rule_performances=performances,
            beneficial_count=len(beneficial),
            neutral_count=len(neutral),
            harmful_count=len(harmful),
            recommended_rules=recommended_rules,
            disabled_rules=disabled_rules,
            overall_improvement=overall_improvement,
            quality_score=quality_score
        )
        
        log.info("📊 규칙셋 분석 완료:")
        log.info(f"   ✅ Beneficial: {len(beneficial)}개")
        log.info(f"   ⚠️  Neutral: {len(neutral)}개") 
        log.info(f"   ❌ Harmful: {len(harmful)}개")
        log.info(f"   🎯 전체 개선량: {overall_improvement:+.3f}")
        log.info(f"   📈 품질 점수: {quality_score:.1f}/100")
        
        return report
    
    def save_analysis_report(self, report: RuleContributionReport, output_path: Path):
        """분석 보고서 저장"""
        
        report_content = f"""
# Rule Contribution Analysis Report
Generated at: {report.generated_at}
Analysis ID: {report.analysis_id}

## Summary
- Test Dataset Size: {report.test_dataset_size} samples
- Total Rules Analyzed: {len(report.rule_performances)} 
- Quality Score: {report.quality_score:.1f}/100
- Overall Improvement: {report.overall_improvement:+.3f} CER

## Rule Classification
- ✅ Beneficial: {report.beneficial_count} rules
- ⚠️  Neutral: {report.neutral_count} rules  
- ❌ Harmful: {report.harmful_count} rules

## Recommended Actions
### Auto-Enable Rules:
"""
        
        for rule_id in report.recommended_rules:
            perf = next(p for p in report.rule_performances if p.rule_id == rule_id)
            report_content += f"- Rule {rule_id}: '{perf.pattern}' → '{perf.replacement}' (ΔCER: {perf.delta_cer_all:+.3f})\n"
        
        report_content += "\n### Disable Rules:\n"
        
        for rule_id in report.disabled_rules:
            perf = next(p for p in report.rule_performances if p.rule_id == rule_id)
            report_content += f"- Rule {rule_id}: '{perf.pattern}' → '{perf.replacement}' (ΔCER: {perf.delta_cer_all:+.3f})\n"
        
        report_content += "\n## Detailed Analysis\n\n"
        
        for perf in report.rule_performances:
            report_content += f"""
### Rule {perf.rule_id}: {perf.status}
- Pattern: '{perf.pattern}' → '{perf.replacement}'
- Overall ΔCER: {perf.delta_cer_all:+.4f}
- Category ΔCERs:
  - Space: {perf.delta_cer_space:+.4f}
  - Punct: {perf.delta_cer_punct:+.4f} 
  - Char: {perf.delta_cer_char:+.4f}
- Applications: {perf.applications_count} times
- False Positive Rate: {perf.false_positive_rate:.1%}
- Coverage: {perf.coverage:.1%}
- Confidence: {perf.confidence:.2f}
- Auto-Enable: {perf.auto_enable}
- Context Dependency: {perf.context_dependency:.2f}
- Robustness: {perf.robustness_score:.2f}
- Side Effects: {', '.join(perf.side_effects) if perf.side_effects else 'None'}

"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        log.info(f"📋 분석 보고서 저장 완료: {output_path}")
        
        return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
    
    # 간단한 테스트
    analyzer = RuleContributionAnalyzer()
    
    # 테스트 샘플 (IMG_4990 기반)
    analyzer.add_test_sample(
        "인식하게 되니다: 두려웅이 생겨나고 안팎의 갈등은 일상이 덥니다'",
        "인식하게 됩니다: 두려움이 생겨나고 안팎의 갈등은 일상이 됩니다."
    )
    
    analyzer.add_test_sample(
        "존재와의 연결을 방해하는 가장 근 걸림돌은 마음과 자기부정이다.",
        "존재와의 연결을 방해하는 가장 큰 걸림돌은 마음과 자기부정이다."
    )
    
    # Phase 2.4에서 생성된 6개 규칙 테스트
    test_rules = [
        {"id": 1, "pattern": "되", "replacement": "됩"},
        {"id": 2, "pattern": "웅", "replacement": "움"},
        {"id": 3, "pattern": "덥", "replacement": "됩"},
        {"id": 4, "pattern": "'", "replacement": "."},
        {"id": 5, "pattern": "근", "replacement": "큰"},
        {"id": 6, "pattern": "갔", "replacement": "회"},
    ]
    
    # 규칙셋 분석
    report = analyzer.analyze_rule_set(test_rules)
    
    # 결과 출력
    print(f"\n🎯 Phase 2.4.5 규칙 품질 검사 결과:")
    print(f"품질 점수: {report.quality_score:.1f}/100")
    print(f"권장 규칙: {len(report.recommended_rules)}개")
    print(f"비활성화 권장: {len(report.disabled_rules)}개")
    print(f"전체 개선량: {report.overall_improvement:+.3f} CER")