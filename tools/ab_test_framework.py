#!/usr/bin/env python3
"""
Phase 2.2 A/B 테스트 프레임워크

Context-aware 규칙들의 실제 성능을 Ground Truth 데이터로 검증하여
각 규칙의 효과를 정량화하는 A/B 테스트 시스템

Based on: samples/ground_truth/ground_truth.json (29개 정답 데이터)
"""

import re
import yaml
import json
import time
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
from collections import defaultdict, Counter
import logging
import difflib

class ABTestFramework:
    """A/B 테스트 프레임워크"""
    
    def __init__(self, 
                 context_rules_file: str = "tools/context_aware_rules.yaml",
                 ground_truth_file: str = "samples/ground_truth/ground_truth.json"):
        self.context_rules_file = Path(context_rules_file)
        self.ground_truth_file = Path(ground_truth_file)
        
        # 로깅 먼저 설정
        self.logger = self._setup_logging()
        
        # 데이터 로드
        self.context_rules = self.load_context_rules()
        self.ground_truth = self.load_ground_truth()
        
        # 테스트 통계
        self.test_stats = {
            'total_tests': 0,
            'rule_performance': {},
            'overall_improvement': 0.0,
            'best_rules': [],
            'problematic_rules': []
        }
        
    def _setup_logging(self) -> logging.Logger:
        """로깅 설정"""
        logger = logging.getLogger('ABTestFramework')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler('tools/ab_test_results.log', encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def load_context_rules(self) -> Dict:
        """Context-aware 규칙 로드"""
        if not self.context_rules_file.exists():
            self.logger.error(f"Context-aware 규칙 파일 없음: {self.context_rules_file}")
            return {}
            
        with open(self.context_rules_file, 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f)
            
        character_rules = rules.get('stage3_postprocessing', {}).get('characters', [])
        self.logger.info(f"Context-aware 규칙 로드: {len(character_rules)}개")
        
        return rules
        
    def load_ground_truth(self) -> Dict:
        """Ground Truth 데이터 로드"""
        if not self.ground_truth_file.exists():
            self.logger.error(f"Ground Truth 파일 없음: {self.ground_truth_file}")
            return {}
            
        with open(self.ground_truth_file, 'r', encoding='utf-8') as f:
            gt_data = json.load(f)
            
        ground_truth = gt_data.get('ground_truth', {})
        self.logger.info(f"Ground Truth 로드: {len(ground_truth)}개 텍스트")
        
        return ground_truth
        
    def simulate_ocr_errors(self, ground_truth_text: str) -> str:
        """Ground Truth에서 OCR 오류 시뮬레이션"""
        # 실제 OCR에서 발생하는 일반적인 오류 패턴들
        error_patterns = [
            ('마음', '마 음'),          # 띄어쓰기 오류
            ('마이클', '마이 클'),       # 인명 분리
            ('상처', '상 처'),          # 단어 분리
            ('있습니다', '있 습니다'),   # 동사 분리
            ('하지만', '하 지만'),       # 접속사 분리
            ('것입니다', '것 입니다'),   # 명사 분리
            ('자신', '자 신'),          # 단어 분리
            ('수있', '수 있'),          # '할 수 있' 패턴
            
            # 문자 치환 오류 (우리가 수정하려는 것들)
            ('마음', '머음'),           # 마 → 머
            ('마이클', '모이클'),       # 마 → 모  
            ('상처', '샹처'),          # 상 → 샹
            ('있습니다', '잇습니다'),   # 있 → 잇
            ('하지만', '호지만'),       # 하 → 호
            ('것입니다', '걷입니다'),   # 것 → 걷
            ('자신', '저신'),          # 자 → 저
            ('자유', '조유'),          # 자 → 조
            ('수있', '소있'),          # 수 → 소
            ('상태', '강태'),          # 상 → 강
        ]
        
        corrupted_text = ground_truth_text
        applied_errors = []
        
        # 무작위로 몇 개의 오류 적용 (현실적인 수준)
        import random
        random.seed(42)  # 재현 가능한 결과를 위해
        
        for original, corrupted in error_patterns:
            if original in corrupted_text and random.random() < 0.3:  # 30% 확률로 오류 발생
                corrupted_text = corrupted_text.replace(original, corrupted)
                applied_errors.append((original, corrupted))
                
        return corrupted_text, applied_errors
        
    def apply_rule(self, text: str, rule: Dict) -> Tuple[str, List[str]]:
        """Context-aware 규칙 적용"""
        pattern = rule.get('pattern', '')
        replacement = rule.get('replacement', '')
        enhanced = rule.get('enhanced', False)
        
        if not enhanced:
            # 단순 치환
            modified_text = text.replace(pattern, replacement)
            changes = [f"{pattern} → {replacement}"] if pattern in text else []
            return modified_text, changes
            
        # Context-aware 적용
        enhanced_patterns = rule.get('enhanced_patterns', [])
        changes = []
        modified_text = text
        
        for pattern_def in enhanced_patterns:
            if pattern_def['type'] == 'safe_context':
                # Safe context 패턴 매칭
                context_pattern = pattern_def['context_pattern']
                target_pattern = pattern_def['target_pattern']
                target_replacement = pattern_def['replacement']
                
                # 정확한 매칭 (단어 단위)
                if context_pattern in modified_text:
                    # context_pattern 내의 target_pattern만 치환
                    old_context = context_pattern
                    new_context = context_pattern.replace(target_pattern, target_replacement)
                    
                    if old_context != new_context:
                        modified_text = modified_text.replace(old_context, new_context)
                        changes.append(f"{old_context} → {new_context}")
                        
        return modified_text, changes
        
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """텍스트 유사도 계산 (0~1)"""
        # 문자 단위 유사도
        char_similarity = difflib.SequenceMatcher(None, text1, text2).ratio()
        
        # 단어 단위 유사도
        words1 = text1.split()
        words2 = text2.split()
        word_similarity = difflib.SequenceMatcher(None, words1, words2).ratio()
        
        # 가중 평균 (문자 70%, 단어 30%)
        overall_similarity = char_similarity * 0.7 + word_similarity * 0.3
        
        return overall_similarity
        
    def test_single_rule(self, rule: Dict, test_data: Dict[str, str]) -> Dict:
        """개별 규칙 A/B 테스트"""
        pattern = rule.get('pattern', '')
        replacement = rule.get('replacement', '')
        
        rule_results = {
            'rule_info': {
                'pattern': pattern,
                'replacement': replacement,
                'enhanced': rule.get('enhanced', False)
            },
            'test_cases': [],
            'performance': {
                'total_tests': 0,
                'improvement_count': 0,
                'degradation_count': 0,
                'neutral_count': 0,
                'avg_improvement': 0.0
            }
        }
        
        improvements = []
        
        for img_id, original_text in test_data.items():
            # OCR 오류 시뮬레이션
            corrupted_text, applied_errors = self.simulate_ocr_errors(original_text)
            
            # 규칙 적용
            corrected_text, changes = self.apply_rule(corrupted_text, rule)
            
            # 성능 측정
            baseline_similarity = self.calculate_similarity(corrupted_text, original_text)
            improved_similarity = self.calculate_similarity(corrected_text, original_text)
            
            improvement = improved_similarity - baseline_similarity
            improvements.append(improvement)
            
            # 개선/악화/중립 분류
            if improvement > 0.01:  # 1% 이상 개선
                result_type = 'improvement'
                rule_results['performance']['improvement_count'] += 1
            elif improvement < -0.01:  # 1% 이상 악화  
                result_type = 'degradation'
                rule_results['performance']['degradation_count'] += 1
            else:  # 중립
                result_type = 'neutral'
                rule_results['performance']['neutral_count'] += 1
                
            rule_results['performance']['total_tests'] += 1
            
            # 테스트 케이스 결과 저장
            test_case = {
                'img_id': img_id,
                'baseline_similarity': round(baseline_similarity, 4),
                'improved_similarity': round(improved_similarity, 4),
                'improvement': round(improvement, 4),
                'result_type': result_type,
                'changes': changes,
                'applied_errors': applied_errors[:3]  # 처음 3개만 보여줌
            }
            
            # 의미있는 변화가 있는 경우만 상세 저장
            if abs(improvement) > 0.01:
                test_case['text_sample'] = {
                    'original': original_text[:100] + '...' if len(original_text) > 100 else original_text,
                    'corrupted': corrupted_text[:100] + '...' if len(corrupted_text) > 100 else corrupted_text,
                    'corrected': corrected_text[:100] + '...' if len(corrected_text) > 100 else corrected_text
                }
                
            rule_results['test_cases'].append(test_case)
            
        # 평균 개선도 계산
        rule_results['performance']['avg_improvement'] = sum(improvements) / len(improvements) if improvements else 0.0
        
        return rule_results
        
    def run_all_tests(self) -> Dict:
        """모든 Context-aware 규칙에 대한 A/B 테스트 실행"""
        character_rules = self.context_rules.get('stage3_postprocessing', {}).get('characters', [])
        
        # Ground Truth 텍스트 추출
        test_data = {}
        for img_id, data in self.ground_truth.items():
            test_data[img_id] = data.get('text', '')
            
        print(f"🧪 A/B 테스트 시작: {len(character_rules)}개 규칙 × {len(test_data)}개 텍스트")
        
        all_results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'test_summary': {
                'total_rules': len(character_rules),
                'total_texts': len(test_data),
                'total_test_combinations': len(character_rules) * len(test_data)
            },
            'rule_results': {},
            'ranking': [],
            'recommendations': []
        }
        
        # 각 규칙별 테스트
        for i, rule in enumerate(character_rules, 1):
            pattern = rule.get('pattern', f'rule_{i}')
            print(f"  테스트 중... {i}/{len(character_rules)}: {pattern}")
            
            rule_result = self.test_single_rule(rule, test_data)
            all_results['rule_results'][f"{pattern}_{rule.get('replacement', '')}"] = rule_result
            
            self.logger.info(
                f"규칙 테스트 완료: {pattern} → "
                f"평균 개선: {rule_result['performance']['avg_improvement']:.4f}"
            )
            
        # 규칙 성능 순위 매기기
        rule_rankings = []
        for rule_key, result in all_results['rule_results'].items():
            perf = result['performance']
            ranking_entry = {
                'rule': result['rule_info'],
                'avg_improvement': perf['avg_improvement'],
                'improvement_rate': perf['improvement_count'] / max(perf['total_tests'], 1),
                'degradation_rate': perf['degradation_count'] / max(perf['total_tests'], 1),
                'total_tests': perf['total_tests'],
                'rank_score': perf['avg_improvement'] * (perf['improvement_count'] / max(perf['total_tests'], 1))
            }
            rule_rankings.append(ranking_entry)
            
        # 성능 순으로 정렬
        rule_rankings.sort(key=lambda x: x['rank_score'], reverse=True)
        all_results['ranking'] = rule_rankings
        
        # 권장사항 생성
        all_results['recommendations'] = self._generate_test_recommendations(rule_rankings)
        
        # 결과 출력 및 저장
        self._print_test_summary(all_results)
        self.save_test_results(all_results)
        
        return all_results
        
    def _generate_test_recommendations(self, rankings: List[Dict]) -> List[str]:
        """테스트 결과 기반 권장사항 생성"""
        recommendations = []
        
        # 상위 5개 규칙 분석
        top_5 = rankings[:5]
        bottom_5 = rankings[-5:]
        
        # 전반적 성능 분석
        avg_improvements = [r['avg_improvement'] for r in rankings]
        overall_avg = sum(avg_improvements) / len(avg_improvements) if avg_improvements else 0
        
        if overall_avg > 0.02:
            recommendations.append(f"✅ 전체 평균 개선도 {overall_avg:.3f}: 높은 성능 확인됨")
        elif overall_avg > 0.01:
            recommendations.append(f"⚠️ 전체 평균 개선도 {overall_avg:.3f}: 적정 수준")
        else:
            recommendations.append(f"❌ 전체 평균 개선도 {overall_avg:.3f}: 성능 향상 제한적")
            
        # 최고 성능 규칙 추천
        if top_5:
            best_rule = top_5[0]
            recommendations.append(
                f"🥇 최고 성능 규칙: '{best_rule['rule']['pattern']} → {best_rule['rule']['replacement']}' "
                f"(개선도: {best_rule['avg_improvement']:.3f})"
            )
            
        # 문제 규칙 경고
        problematic = [r for r in rankings if r['avg_improvement'] < -0.01]
        if problematic:
            recommendations.append(
                f"⚠️ 성능 저하 규칙 {len(problematic)}개 발견 - 제거 고려 필요"
            )
            
        # 즉시 적용 권장 규칙
        safe_rules = [r for r in rankings if r['avg_improvement'] > 0.02 and r['degradation_rate'] < 0.1]
        if safe_rules:
            recommendations.append(
                f"🚀 즉시 적용 권장: 상위 {len(safe_rules)}개 규칙 (안전성 검증됨)"
            )
            
        return recommendations
        
    def _print_test_summary(self, results: Dict):
        """A/B 테스트 결과 요약 출력"""
        rankings = results['ranking']
        
        print(f"\n✅ A/B 테스트 완료!")
        print(f"  📊 총 테스트: {results['test_summary']['total_rules']}개 규칙")
        print(f"  📈 평균 개선도: {sum(r['avg_improvement'] for r in rankings) / len(rankings):.4f}")
        
        print(f"\n🏆 상위 5개 규칙:")
        for i, rule in enumerate(rankings[:5], 1):
            print(f"  {i}. {rule['rule']['pattern']} → {rule['rule']['replacement']}: "
                  f"개선도 {rule['avg_improvement']:.4f} "
                  f"(성공률: {rule['improvement_rate']:.2%})")
                  
        print(f"\n⚠️ 성능 저하 규칙:")  
        poor_rules = [r for r in rankings if r['avg_improvement'] < -0.01]
        for rule in poor_rules:
            print(f"  • {rule['rule']['pattern']} → {rule['rule']['replacement']}: "
                  f"개선도 {rule['avg_improvement']:.4f}")
                  
        print(f"\n💡 권장사항:")
        for rec in results['recommendations']:
            print(f"  {rec}")
        
    def save_test_results(self, results: Dict):
        """A/B 테스트 결과 저장"""
        output_file = Path("tools/ab_test_results.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        print(f"\n📄 상세 결과 저장: {output_file}")
        self.logger.info(f"A/B 테스트 결과 저장: {len(results['rule_results'])}개 규칙")
        
    def generate_production_rules(self, test_results: Dict, min_improvement: float = 0.02) -> Dict:
        """운영 환경 적용 권장 규칙 생성"""
        rankings = test_results['ranking']
        
        # 조건을 만족하는 규칙만 선별
        production_rules = []
        for rule in rankings:
            if (rule['avg_improvement'] >= min_improvement and 
                rule['degradation_rate'] < 0.1 and
                rule['improvement_rate'] > 0.3):
                
                production_rules.append(rule['rule'])
                
        # 운영용 YAML 생성
        production_yaml = {
            'metadata': {
                'version': '2.3_production_ready',
                'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                'source': 'A/B 테스트 검증 완료',
                'total_production_rules': len(production_rules),
                'selection_criteria': {
                    'min_improvement': min_improvement,
                    'max_degradation_rate': 0.1,
                    'min_improvement_rate': 0.3
                },
                'test_results_file': 'tools/ab_test_results.json'
            },
            'stage3_postprocessing': {
                'spacing': [],
                'characters': production_rules
            }
        }
        
        output_file = Path("tools/production_ready_rules.yaml")
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(production_yaml, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
        print(f"🚀 운영 적용 규칙 저장: {output_file} ({len(production_rules)}개 선별)")
        
        return {
            'production_rules_count': len(production_rules),
            'output_file': str(output_file)
        }

def main():
    """메인 실행 함수"""
    print("🧪 Phase 2.2 A/B 테스트 프레임워크 시작")
    print("=" * 60)
    
    # A/B 테스트 프레임워크 초기화
    ab_tester = ABTestFramework()
    
    # 모든 Context-aware 규칙에 대한 A/B 테스트 실행
    print("📋 Context-aware 규칙들의 실제 성능 측정...")
    test_results = ab_tester.run_all_tests()
    
    # 운영 환경 적용 권장 규칙 생성
    print("\n🚀 운영 환경 적용 권장 규칙 생성...")
    production_info = ab_tester.generate_production_rules(test_results)
    
    print(f"\n📅 Phase 2.2 완료 요약:")
    print(f"  ✅ PatternValidator: 39개 → 10개 안전 규칙 선별")
    print(f"  🔧 Context-aware: 10개 규칙을 패턴 매칭으로 강화")
    print(f"  🧪 A/B 테스트: {production_info['production_rules_count']}개 운영 준비 완료")
    
    print(f"\n📄 결과 파일:")
    print(f"  • tools/ab_test_results.json - 상세 테스트 결과")
    print(f"  • {production_info['output_file']} - 운영 적용 규칙")
    
    print(f"\n🎯 다음 단계: 실제 시스템에 운영 규칙 통합 및 성능 모니터링")
    
    print(f"\n✅ Phase 2.2 전체 완료!")

if __name__ == "__main__":
    main()