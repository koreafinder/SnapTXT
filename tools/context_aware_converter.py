#!/usr/bin/env python3
"""
Phase 2.2 Context-aware 규칙 변환 시스템

안전한 10개 규칙을 더욱 정교하게 Context-aware 패턴으로 변환하여
정확성을 높이고 오적용을 방지하는 시스템

Based on: tools/safe_rules_filtered.yaml
"""

import re
import yaml
import json
import time
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
from collections import defaultdict
import logging

class ContextAwareRuleConverter:
    """Context-aware 규칙 변환 시스템"""
    
    def __init__(self, safe_rules_file: str = "tools/safe_rules_filtered.yaml"):
        self.safe_rules_file = Path(safe_rules_file)
        
        # 로깅 먼저 설정
        self.logger = self._setup_logging()
        
        # 그 다음에 규칙 로드
        self.safe_rules = self.load_safe_rules()
        self.context_patterns = self.load_context_patterns()
        
        # 변환 통계
        self.conversion_stats = {
            'total_rules': 0,
            'simple_rules': 0,
            'context_enhanced': 0,
            'pattern_enhanced': 0
        }
        
    def _setup_logging(self) -> logging.Logger:
        """로깅 설정"""
        logger = logging.getLogger('ContextAwareConverter')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler('tools/context_conversion.log', encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def load_safe_rules(self) -> Dict:
        """안전한 규칙 로드"""
        if not self.safe_rules_file.exists():
            self.logger.error(f"안전 규칙 파일 없음: {self.safe_rules_file}")
            return {}
            
        with open(self.safe_rules_file, 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f)
            
        character_rules = rules.get('stage3_postprocessing', {}).get('characters', [])
        self.logger.info(f"안전 규칙 로드: {len(character_rules)}개")
        
        return rules
        
    def load_context_patterns(self) -> Dict:
        """Context-aware 패턴 정의 로드"""
        # Ground Truth 데이터에서 추출한 일반적인 한국어 패턴들
        patterns = {
            # 문자별 Context 패턴 정의
            '마': {
                'safe_contexts': [
                    r'마음',      # 마음 관련 단어
                    r'마이',      # 마이클 등 고유명사
                    r'마지막',    # 마지막
                    r'마치',      # 마치
                    r'그러나마',  # 그러나마
                ],
                'risky_contexts': [
                    r'^마$',      # 단독 '마'
                    r'마\.', r'마,', r'마\?', r'마!'  # 문장 끝 조사
                ]
            },
            '상': {
                'safe_contexts': [
                    r'상처',      # 상처
                    r'상황',      # 상황
                    r'상태',      # 상태 
                    r'상상',      # 상상
                    r'대상',      # 대상
                    r'사상',      # 사상
                ],
                'risky_contexts': [
                    r'^상$',      # 단독 '상'
                ]
            },
            '있': {
                'safe_contexts': [
                    r'있습니다',  # 있습니다
                    r'있는',      # 있는
                    r'있을',      # 있을
                    r'있어',      # 있어
                    r'있다',      # 있다
                ],
                'risky_contexts': [
                    r'^있$',      # 단독 '있'
                ]
            },
            '하': {
                'safe_contexts': [
                    r'하고',      # 하고
                    r'하는',      # 하는
                    r'하지',      # 하지
                    r'하여',      # 하여 
                    r'하면',      # 하면
                    r'하게',      # 하게
                ],
                'risky_contexts': [
                    r'^하$',      # 단독 '하'
                ]
            },
            '것': {
                'safe_contexts': [
                    r'것이',      # 것이
                    r'것을',      # 것을
                    r'것입니다',  # 것입니다
                    r'것입니',    # 것입니
                    r'것도',      # 것도
                    r'아무것',    # 아무것
                ],
                'risky_contexts': [
                    r'^것$',      # 단독 '것'
                ]  
            },
            '자': {
                'safe_contexts': [
                    r'자신',      # 자신
                    r'자아',      # 자아
                    r'자유',      # 자유
                    r'자료',      # 자료
                    r'자리',      # 자리
                    r'문자',      # 문자
                ],
                'risky_contexts': [
                    r'^자$',      # 단독 '자'
                ]
            },
            '수': {
                'safe_contexts': [
                    r'수있',      # 수 있 (할 수 있)
                    r'수도',      # 수도
                    r'숫자',      # 숫자
                    r'방수',      # 방수
                    r'다수',      # 다수
                ],
                'risky_contexts': [
                    r'^수$',      # 단독 '수'
                ]
            }
        }
        
        self.logger.info(f"Context 패턴 로드: {len(patterns)}개 문자")
        return patterns
        
    def analyze_rule_safety(self, rule: Dict) -> Dict:
        """규칙별 안전성 분석 및 Context 필요성 판단"""
        pattern = rule.get('pattern', '')
        replacement = rule.get('replacement', '')
        frequency = rule.get('frequency', 0)
        confidence = rule.get('confidence', 0.0)
        
        analysis = {
            'pattern': pattern,
            'replacement': replacement,
            'needs_context': False,
            'complexity': 'simple',
            'safety_level': 'high',
            'recommended_strategy': 'direct_apply',
            'context_patterns': []
        }
        
        # Context 필요성 판단
        if len(pattern) == 1:
            # 단일 문자는 항상 Context 필요
            analysis['needs_context'] = True
            analysis['complexity'] = 'complex'
            analysis['recommended_strategy'] = 'pattern_match'
            
        elif len(pattern) == 2:
            # 2글자는 빈도와 신뢰도에 따라 판단
            if frequency < 6 or confidence < 0.85:
                analysis['needs_context'] = True
                analysis['complexity'] = 'medium'
                analysis['recommended_strategy'] = 'conditional_apply'
                
        # Context 패턴 생성 (필요한 경우만)
        if analysis['needs_context'] and pattern in self.context_patterns:
            analysis['context_patterns'] = self.context_patterns[pattern]
            
        return analysis
        
    def generate_context_aware_rule(self, rule: Dict, analysis: Dict) -> Dict:
        """Context-aware 규칙 생성"""
        pattern = rule.get('pattern', '')
        replacement = rule.get('replacement', '')
        
        # 기본 규칙 복사
        enhanced_rule = rule.copy()
        enhanced_rule['original_pattern'] = pattern
        enhanced_rule['strategy'] = analysis['recommended_strategy']
        
        if analysis['recommended_strategy'] == 'direct_apply':
            # 직접 적용 (기존 방식)
            enhanced_rule['enhanced'] = False
            self.conversion_stats['simple_rules'] += 1
            
        elif analysis['recommended_strategy'] == 'conditional_apply':
            # 조건부 적용 (주변 문맥 간단 검사)
            enhanced_rule['enhanced'] = True
            enhanced_rule['conditions'] = {
                'min_word_length': 2,  # 2글자 이상 단어에서만
                'exclude_sentence_end': True,  # 문장 끝에서는 제외
                'require_korean_context': True  # 한글 문맥 내에서만
            }
            enhanced_rule['enhanced_pattern'] = self._create_conditional_pattern(pattern, replacement)
            self.conversion_stats['context_enhanced'] += 1
            
        elif analysis['recommended_strategy'] == 'pattern_match':
            # 패턴 매칭 적용 (정확한 Context 검사)
            enhanced_rule['enhanced'] = True
            enhanced_rule['context_patterns'] = analysis.get('context_patterns', {})
            enhanced_rule['enhanced_patterns'] = self._create_pattern_matchers(
                pattern, replacement, analysis['context_patterns']
            )
            self.conversion_stats['pattern_enhanced'] += 1
            
        return enhanced_rule
        
    def _create_conditional_pattern(self, pattern: str, replacement: str) -> Dict:
        """조건부 적용 패턴 생성"""
        return {
            'type': 'conditional',
            'original': pattern,
            'replacement': replacement,
            'conditions': {
                # 단어 경계 내에서만 적용
                'word_boundary': True,
                # 문장 부호 앞에서는 제외  
                'exclude_before': ['.', ',', '?', '!', ':', ';'],
                # 최소 길이 확보
                'min_context_length': 2
            },
            'regex_pattern': rf'\b{re.escape(pattern)}\b(?![.,:;!?])'
        }
        
    def _create_pattern_matchers(self, pattern: str, replacement: str, context_def: Dict) -> List[Dict]:
        """정확한 패턴 매처들 생성"""
        matchers = []
        
        safe_contexts = context_def.get('safe_contexts', [])
        risky_contexts = context_def.get('risky_contexts', [])
        
        # Safe context 기반 매처들
        for safe_pattern in safe_contexts:
            # pattern이 safe_pattern 내부에 있을 때만 적용
            if pattern in safe_pattern:
                matcher = {
                    'type': 'safe_context',
                    'context_pattern': safe_pattern,
                    'target_pattern': pattern,
                    'replacement': replacement,
                    'regex': safe_pattern.replace(pattern, f'({re.escape(pattern)})')
                }
                matchers.append(matcher)
                
        # Risky context 회피 매처 
        for risky_pattern in risky_contexts:
            matcher = {
                'type': 'avoid_context',
                'risky_pattern': risky_pattern,
                'target_pattern': pattern,
                'action': 'skip'
            }
            matchers.append(matcher)
            
        return matchers
        
    def convert_all_rules(self) -> Dict:
        """모든 안전한 규칙을 Context-aware로 변환"""
        character_rules = self.safe_rules.get('stage3_postprocessing', {}).get('characters', [])
        
        self.conversion_stats['total_rules'] = len(character_rules)
        
        print(f"🔧 Context-aware 변환 시작: {len(character_rules)}개 안전한 규칙")
        
        enhanced_rules = []
        conversion_report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'input_rules_count': len(character_rules),
            'enhanced_rules': [],
            'conversion_summary': {},
            'recommendations': []
        }
        
        for i, rule in enumerate(character_rules, 1):
            pattern = rule.get('pattern', 'unknown') 
            print(f"  변환 중... {i}/{len(character_rules)}: {pattern}")
            
            # 안전성 분석
            analysis = self.analyze_rule_safety(rule)
            
            # Context-aware 규칙 생성
            enhanced_rule = self.generate_context_aware_rule(rule, analysis)
            enhanced_rules.append(enhanced_rule)
            
            # 보고서에 추가
            conversion_report['enhanced_rules'].append({
                'original_pattern': pattern,
                'replacement': rule.get('replacement', ''),
                'strategy': analysis['recommended_strategy'],
                'needs_context': analysis['needs_context'],
                'complexity': analysis['complexity'],
                'enhanced': enhanced_rule.get('enhanced', False)
            })
            
            self.logger.info(
                f"규칙 변환: {pattern} → {analysis['recommended_strategy']} "
                f"(Context: {'필요' if analysis['needs_context'] else '불필요'})"
            )
            
        # 변환 요약
        conversion_report['conversion_summary'] = self.conversion_stats.copy()
        
        # 권장사항 생성
        conversion_report['recommendations'] = self._generate_recommendations()
        
        print(f"\n✅ Context-aware 변환 완료!")
        print(f"  📊 전체: {self.conversion_stats['total_rules']}개")
        print(f"  🔄 단순 적용: {self.conversion_stats['simple_rules']}개")
        print(f"  ⚙️ Context 강화: {self.conversion_stats['context_enhanced']}개")
        print(f"  🎯 패턴 매칭: {self.conversion_stats['pattern_enhanced']}개")
        
        # 결과 저장
        self.save_enhanced_rules(enhanced_rules, conversion_report)
        
        return {
            'enhanced_rules': enhanced_rules,
            'conversion_report': conversion_report
        }
        
    def _generate_recommendations(self) -> List[str]:
        """변환 결과 기반 권장사항 생성"""
        recommendations = []
        
        simple_ratio = self.conversion_stats['simple_rules'] / max(self.conversion_stats['total_rules'], 1)
        
        if simple_ratio > 0.7:
            recommendations.append(
                "✅ 단순 적용 규칙이 70% 이상: 높은 안전성 확보됨"
            )
        elif simple_ratio > 0.5:
            recommendations.append(
                "⚠️ 단순 적용 규칙 50-70%: 적정 수준의 복잡성"
            )
        else:
            recommendations.append(
                "🔧 Context 강화 규칙이 다수: 세밀한 테스트 필요"
            )
            
        if self.conversion_stats['pattern_enhanced'] > 0:
            recommendations.append(
                f"🎯 패턴 매칭 규칙 {self.conversion_stats['pattern_enhanced']}개: "
                "정확성 향상 기대"
            )
            
        recommendations.append(
            "📅 다음 단계: A/B 테스트로 실제 성능 검증 권장"
        )
        
        return recommendations
        
    def save_enhanced_rules(self, enhanced_rules: List[Dict], conversion_report: Dict):
        """강화된 규칙 저장"""
        
        # 1. 강화된 YAML 규칙 파일 생성
        enhanced_yaml = {
            'metadata': {
                'version': '2.2_context_aware',
                'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                'source': 'Context-aware 규칙 변환 결과',
                'total_enhanced_rules': len(enhanced_rules),
                'conversion_strategy': {
                    'simple_rules': self.conversion_stats['simple_rules'],
                    'context_enhanced': self.conversion_stats['context_enhanced'],
                    'pattern_enhanced': self.conversion_stats['pattern_enhanced']
                },
                'safety_level': 'production_ready'
            },
            'stage3_postprocessing': {
                'spacing': [],
                'characters': enhanced_rules
            }
        }
        
        yaml_output_file = Path("tools/context_aware_rules.yaml")
        with open(yaml_output_file, 'w', encoding='utf-8') as f:
            yaml.dump(enhanced_yaml, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
        print(f"📄 Context-aware 규칙 저장: {yaml_output_file}")
        
        # 2. 변환 보고서 JSON 저장  
        json_output_file = Path("tools/context_conversion_report.json")
        with open(json_output_file, 'w', encoding='utf-8') as f:
            json.dump(conversion_report, f, ensure_ascii=False, indent=2)
            
        print(f"📊 변환 보고서 저장: {json_output_file}")
        
        self.logger.info(f"Context-aware 규칙 저장 완료: {len(enhanced_rules)}개 규칙")

def main():
    """메인 실행 함수"""
    print("🔧 Phase 2.2 Context-aware 규칙 변환 시스템 시작")
    print("=" * 60)
    
    # Context-aware 변환기 초기화
    converter = ContextAwareRuleConverter()
    
    # 안전한 10개 규칙을 Context-aware로 변환
    print("📋 안전한 규칙들을 Context-aware 패턴으로 변환...")
    results = converter.convert_all_rules()
    
    # 변환 결과 요약
    report = results['conversion_report']
    print(f"\n🎯 변환 완료 요약:")
    for rec in report['recommendations']:
        print(f"  {rec}")
        
    print(f"\n📅 다음 단계:")
    print(f"  1. tools/context_aware_rules.yaml 검토")
    print(f"  2. tools/context_conversion_report.json 확인") 
    print(f"  3. A/B 테스트 프레임워크 구축")
    print(f"  4. 실제 텍스트에 적용하여 성능 측정")
    
    print(f"\n✅ Phase 2.2-3단계 (Context-aware 변환) 완료!")

if __name__ == "__main__":
    main()