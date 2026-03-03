#!/usr/bin/env python3
"""
Phase 2.2 패턴 검증 시스템 - PatternValidator

Context-aware 규칙 적용을 위한 고도화된 안전성 검증 시스템
39개 Phase 2 학습 규칙을 안전한 10-15개로 정제

Based on: docs/plans/postprocessing_improvement_plan.md Phase 2.2
"""

import re
import yaml
import json
import time
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
from collections import Counter, defaultdict
import logging

# 한국어 언어학적 패턴 정의
KOREAN_JAMO_PATTERNS = {
    'initial': 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ',
    'medial': 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ',
    'final': 'ㄱㄲㄳㄴㄵㄶㄷㄸㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ'
}

class PatternValidator:
    """Phase 2.2 패턴 검증 및 안전성 보장 시스템"""
    
    def __init__(self, existing_rules_file: str = "stage3_rules.yaml"):
        self.existing_rules_file = Path(existing_rules_file)
        
        # 로깅 먼저 설정
        self.logger = self._setup_logging()
        
        # 그 다음에 규칙 로드
        self.existing_rules = self.load_existing_rules()
        self.dangerous_patterns = self.load_dangerous_patterns()
        
        # 검증 통계
        self.validation_stats = {
            'total_validated': 0,
            'passed': 0,
            'failed_safety': 0,
            'failed_conflict': 0,
            'failed_linguistic': 0,
            'failed_frequency': 0
        }
        
    def _setup_logging(self) -> logging.Logger:
        """로깅 설정"""
        logger = logging.getLogger('PatternValidator')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler('tools/pattern_validation.log', encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def load_existing_rules(self) -> Dict:
        """기존 Stage3 규칙 로드"""
        if not self.existing_rules_file.exists():
            self.logger.warning(f"기존 규칙 파일 없음: {self.existing_rules_file}")
            return {}
            
        with open(self.existing_rules_file, 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f)
            
        stage3 = rules.get('stage3_postprocessing', {})
        self.logger.info(f"기존 규칙 로드: {len(stage3.get('characters', []))}개 문자 규칙")
        
        return rules
        
    def load_dangerous_patterns(self) -> List[Dict]:
        """위험한 패턴 정의 (무차별 단순 치환 규칙들)"""
        dangerous = [
            # 발견된 위험한 단순 치환들
            {'pattern': '는', 'type': 'single_char', 'reason': 'Context 없는 조사 치환'},
            {'pattern': '기', 'type': 'single_char', 'reason': 'Context 없는 어미 치환'},
            {'pattern': '어', 'type': 'single_char', 'reason': 'Context 없는 모음 치환'},  
            {'pattern': '다', 'type': 'single_char', 'reason': 'Context 없는 어미 치환'},
            {'pattern': '가', 'type': 'single_char', 'reason': 'Context 없는 조사 치환'},
            {'pattern': '로', 'type': 'single_char', 'reason': 'Context 없는 조사 치환'},
            {'pattern': '과', 'type': 'single_char', 'reason': 'Context 없는 조사 치환'},
            {'pattern': '든', 'type': 'single_char', 'reason': 'Context 없는 어미 치환'},
            {'pattern': '그', 'type': 'single_char', 'reason': 'Context 없는 관형사 치환'},
            {'pattern': '할', 'type': 'single_char', 'reason': 'Context 없는 동사 치환'},
        ]
        
        self.logger.info(f"위험 패턴 정의: {len(dangerous)}개")
        return dangerous
        
    def validate_pattern(self, pattern: Dict) -> Dict[str, Any]:
        """패턴 검증 메인 함수"""
        self.validation_stats['total_validated'] += 1
        
        result = {
            'pattern': pattern,
            'is_safe': True,
            'reasons': [],
            'risk_level': 'low',
            'recommendations': []
        }
        
        # 1. 기본 안전성 검사
        safety_result = self.check_basic_safety(pattern)
        if not safety_result['is_safe']:
            result['is_safe'] = False
            result['reasons'].extend(safety_result['reasons'])
            result['risk_level'] = safety_result['risk_level']
            self.validation_stats['failed_safety'] += 1
            
        # 2. 기존 규칙과 충돌 검사
        conflict_result = self.check_rule_conflicts(pattern)
        if conflict_result['has_conflict']:
            if result['is_safe']:  # 아직 안전하다면 경고 레벨로
                result['risk_level'] = 'medium'
                result['recommendations'].extend(conflict_result['recommendations'])
            else:  # 이미 위험하다면 실패
                result['reasons'].extend(conflict_result['reasons'])
                self.validation_stats['failed_conflict'] += 1
                
        # 3. 한국어 언어학적 타당성 검사  
        linguistic_result = self.check_linguistic_validity(pattern)
        if not linguistic_result['is_valid']:
            result['is_safe'] = False
            result['reasons'].extend(linguistic_result['reasons'])
            result['risk_level'] = 'high'
            self.validation_stats['failed_linguistic'] += 1
            
        # 4. 빈도 임계값 검사
        frequency_result = self.check_frequency_threshold(pattern)
        if not frequency_result['meets_threshold']:
            result['is_safe'] = False
            result['reasons'].extend(frequency_result['reasons'])
            self.validation_stats['failed_frequency'] += 1
            
        # 최종 판정
        if result['is_safe']:
            self.validation_stats['passed'] += 1
            result['recommendations'].append("안전한 패턴으로 확인됨 - 적용 권장")
            
        # 로깅
        self.logger.info(
            f"패턴 검증: {pattern.get('pattern', 'unknown')} → "
            f"{'PASS' if result['is_safe'] else 'FAIL'} "
            f"(위험도: {result['risk_level']})"
        )
        
        return result
        
    def check_basic_safety(self, pattern: Dict) -> Dict[str, Any]:
        """1. 기본 안전성 검사"""
        pattern_str = pattern.get('pattern', '')
        replacement = pattern.get('replacement', '')
        
        result = {
            'is_safe': True,
            'reasons': [],
            'risk_level': 'low'
        }
        
        # 단일 문자 치환 검사 (가장 위험함)
        if len(pattern_str) == 1:
            if any(dp['pattern'] == pattern_str for dp in self.dangerous_patterns):
                result['is_safe'] = False
                result['risk_level'] = 'critical'
                result['reasons'].append(f"위험한 단일 문자 치환: '{pattern_str}' → '{replacement}'")
                
        # 빈 문자열 검사
        if not pattern_str or not replacement:
            result['is_safe'] = False
            result['risk_level'] = 'high'
            result['reasons'].append("패턴 또는 대체 문자열이 비어있음")
            
        # 동일 문자열 치환 검사  
        if pattern_str == replacement:
            result['is_safe'] = False
            result['risk_level'] = 'medium'
            result['reasons'].append("패턴과 대체 문자열이 동일함")
            
        # 과도한 길이 차이 검사
        length_diff = abs(len(pattern_str) - len(replacement))
        if length_diff > 5:
            result['risk_level'] = 'medium'
            result['reasons'].append(f"길이 차이가 큼: {length_diff}자")
            
        return result
        
    def check_rule_conflicts(self, pattern: Dict) -> Dict[str, Any]:
        """2. 기존 규칙과 충돌 검사"""
        pattern_str = pattern.get('pattern', '')
        
        result = {
            'has_conflict': False,
            'reasons': [],
            'recommendations': []
        }
        
        # 기존 문자 규칙과 비교
        existing_chars = self.existing_rules.get('stage3_postprocessing', {}).get('characters', [])
        
        for existing_rule in existing_chars:
            existing_pattern = existing_rule.get('pattern', '')
            existing_replacement = existing_rule.get('replacement', '')
            
            # 정확히 동일한 패턴
            if existing_pattern == pattern_str:
                if existing_replacement != pattern.get('replacement', ''):
                    result['has_conflict'] = True
                    result['reasons'].append(
                        f"기존 규칙과 충돌: '{pattern_str}' → "
                        f"기존: '{existing_replacement}', 신규: '{pattern.get('replacement', '')}'"
                    )
                else:
                    result['recommendations'].append(f"기존 규칙과 동일 (중복 규칙)")
                    
            # 패턴 포함 관계 검사
            if pattern_str in existing_pattern or existing_pattern in pattern_str:
                result['recommendations'].append(
                    f"기존 규칙과 유사: '{existing_pattern}' ↔ '{pattern_str}'"
                )
                
        return result
        
    def check_linguistic_validity(self, pattern: Dict) -> Dict[str, Any]:
        """3. 한국어 언어학적 타당성 검사"""
        pattern_str = pattern.get('pattern', '')
        replacement = pattern.get('replacement', '')
        
        result = {
            'is_valid': True,
            'reasons': []
        }
        
        # 한글 문자 검증
        def is_korean_char(char):
            return '가' <= char <= '힣' or 'ㄱ' <= char <= 'ㅣ'
            
        def has_korean(text):
            return any(is_korean_char(char) for char in text)
            
        if not has_korean(pattern_str) or not has_korean(replacement):
            result['is_valid'] = False
            result['reasons'].append("한글 문자가 포함되지 않음")
            return result
            
        # 조사/어미 단독 치환 금지 (Context 필요)
        particles = ['은', '는', '이', '가', '을', '를', '에', '에서', '로', '으로', '와', '과', '의']
        endings = ['다', '까', '냐', '니', '지', '아', '어', '여', '고', '게', '게']
        
        if pattern_str in particles or pattern_str in endings:
            if len(pattern_str) <= 2:  # 단독 조사/어미
                result['is_valid'] = False
                result['reasons'].append(f"Context 없는 조사/어미 치환: '{pattern_str}'")
                
        # 문법적 타당성 간단 검사
        if len(pattern_str) == 1 and len(replacement) == 1:
            # 단일 문자 치환의 경우 더 엄격
            if pattern_str != replacement:
                # 유사한 형태의 문자인지 검사 (자음/모음 구조)
                try:
                    pattern_ord = ord(pattern_str)
                    replacement_ord = ord(replacement)
                    
                    # 한글 완성형 범위 내에서
                    if 44032 <= pattern_ord <= 55215 and 44032 <= replacement_ord <= 55215:
                        # 초성, 중성, 종성 분해해서 비교
                        pattern_cho = (pattern_ord - 44032) // 588
                        pattern_jung = ((pattern_ord - 44032) % 588) // 28
                        pattern_jong = (pattern_ord - 44032) % 28
                        
                        replacement_cho = (replacement_ord - 44032) // 588
                        replacement_jung = ((replacement_ord - 44032) % 588) // 28
                        replacement_jong = (replacement_ord - 44032) % 28
                        
                        # 2개 이상 구성요소가 다르면 위험
                        diff_count = sum([
                            pattern_cho != replacement_cho,
                            pattern_jung != replacement_jung, 
                            pattern_jong != replacement_jong
                        ])
                        
                        if diff_count >= 2:
                            result['is_valid'] = False
                            result['reasons'].append(
                                f"문자 구조 차이 과다: '{pattern_str}' → '{replacement}'"
                            )
                            
                except:
                    # 유니코드 분석 실패시 통과
                    pass
                    
        return result
        
    def check_frequency_threshold(self, pattern: Dict) -> Dict[str, Any]:
        """4. 빈도 임계값 검사 (3회 이상)"""
        frequency = pattern.get('frequency', 0)
        confidence = pattern.get('confidence', 0.0)
        source_count = pattern.get('source_count', 0)
        
        result = {
            'meets_threshold': True,
            'reasons': []
        }
        
        # 최소 빈도 검사 (3회 이상)
        if frequency < 3:
            result['meets_threshold'] = False
            result['reasons'].append(f"빈도 부족: {frequency}회 (최소 3회 필요)")
            
        # 최소 신뢰도 검사 (60% 이상)
        if confidence < 0.6:
            result['meets_threshold'] = False
            result['reasons'].append(f"신뢰도 부족: {confidence:.2f} (최소 0.60 필요)")
            
        # 최소 소스 개수 검사 (2개 이상)
        if source_count < 2:
            result['meets_threshold'] = False
            result['reasons'].append(f"소스 부족: {source_count}개 (최소 2개 필요)")
            
        return result
        
    def validate_all_patterns(self, patterns_file: str = "learning_data/learned_rules_advanced.yaml") -> Dict:
        """39개 Phase 2 규칙 전체 검증"""
        patterns_path = Path(patterns_file)
        
        if not patterns_path.exists():
            self.logger.error(f"패턴 파일 없음: {patterns_path}")
            return {"error": f"파일 없음: {patterns_path}"}
            
        with open(patterns_path, 'r', encoding='utf-8') as f:
            learned_rules = yaml.safe_load(f)
            
        character_rules = learned_rules.get('stage3_postprocessing', {}).get('characters', [])
        
        self.logger.info(f"전체 검증 시작: {len(character_rules)}개 패턴")
        print(f"📊 Phase 2 패턴 검증 시작: {len(character_rules)}개 규칙")
        
        results = {
            'total_patterns': len(character_rules),
            'safe_patterns': [],
            'unsafe_patterns': [],
            'medium_risk_patterns': [],
            'validation_summary': {},
            'recommendations': {
                'safe_for_production': [],
                'needs_context_aware': [],
                'should_reject': []
            }
        }
        
        for i, pattern in enumerate(character_rules, 1):
            print(f"  검증 중... {i}/{len(character_rules)}: {pattern.get('pattern', 'unknown')}")
            
            validation_result = self.validate_pattern(pattern)
            
            # 결과 분류
            if validation_result['is_safe']:
                results['safe_patterns'].append({
                    'pattern': pattern,
                    'validation': validation_result,
                    'rank': len(results['safe_patterns']) + 1
                })
                results['recommendations']['safe_for_production'].append(pattern)
                
            elif validation_result['risk_level'] == 'medium':
                results['medium_risk_patterns'].append({
                    'pattern': pattern,
                    'validation': validation_result
                })
                results['recommendations']['needs_context_aware'].append(pattern)
                
            else:  # high or critical risk
                results['unsafe_patterns'].append({
                    'pattern': pattern,
                    'validation': validation_result
                })
                results['recommendations']['should_reject'].append(pattern)
                
        # 검증 통계 정리
        results['validation_summary'] = self.validation_stats.copy()
        results['validation_summary']['safe_count'] = len(results['safe_patterns'])
        results['validation_summary']['unsafe_count'] = len(results['unsafe_patterns'])
        results['validation_summary']['medium_risk_count'] = len(results['medium_risk_patterns'])
        
        # 결과 출력
        print(f"\n✅ 검증 완료!")
        print(f"  📊 전체: {results['total_patterns']}개")
        print(f"  ✅ 안전: {len(results['safe_patterns'])}개")
        print(f"  ⚠️  주의: {len(results['medium_risk_patterns'])}개") 
        print(f"  ❌ 위험: {len(results['unsafe_patterns'])}개")
        
        # 로그 및 파일 저장
        self.save_validation_results(results)
        
        return results
        
    def save_validation_results(self, results: Dict):
        """검증 결과 저장"""
        output_file = Path("tools/pattern_validation_results.json")
        
        # JSON 직렬화를 위해 결과 정리
        serializable_results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_patterns': results['total_patterns'],
            'validation_summary': results['validation_summary'],
            'safe_patterns': [
                {
                    'pattern': item['pattern'].get('pattern'),
                    'replacement': item['pattern'].get('replacement'),
                    'confidence': item['pattern'].get('confidence'),
                    'frequency': item['pattern'].get('frequency'),
                    'rank': item['rank']
                } 
                for item in results['safe_patterns']
            ],
            'unsafe_patterns': [
                {
                    'pattern': item['pattern'].get('pattern'),
                    'replacement': item['pattern'].get('replacement'),
                    'risk_level': item['validation']['risk_level'],
                    'reasons': item['validation']['reasons']
                }
                for item in results['unsafe_patterns']
            ],
            'medium_risk_patterns': [
                {
                    'pattern': item['pattern'].get('pattern'),
                    'replacement': item['pattern'].get('replacement'),
                    'risk_level': item['validation']['risk_level'],
                    'recommendations': item['validation']['recommendations']
                }
                for item in results['medium_risk_patterns']
            ]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2)
            
        self.logger.info(f"검증 결과 저장: {output_file}")
        print(f"📄 상세 결과 저장: {output_file}")
        
    def generate_safe_rules_yaml(self, validation_results: Dict, output_file: str = "tools/safe_rules_filtered.yaml"):
        """안전한 규칙만으로 새로운 YAML 생성"""
        safe_patterns = validation_results['safe_patterns']
        
        if not safe_patterns:
            print("❌ 안전한 패턴이 없습니다!")
            return
            
        # 안전한 규칙들로 새 YAML 구성
        safe_yaml = {
            'metadata': {
                'version': '2.1_filtered',
                'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                'source': 'PatternValidator 필터링 결과',
                'total_safe_patterns': len(safe_patterns),
                'filtered_from': 'learned_rules_advanced.yaml',
                'validation_criteria': {
                    'basic_safety': True,
                    'no_conflicts': True, 
                    'linguistic_valid': True,
                    'min_frequency': 3,
                    'min_confidence': 0.6,
                    'min_sources': 2
                }
            },
            'stage3_postprocessing': {
                'spacing': [],  # 현재는 문자 규칙만 검증
                'characters': [
                    pattern['pattern'] for pattern in safe_patterns
                ]
            }
        }
        
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(safe_yaml, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
        print(f"✅ 안전한 규칙 {len(safe_patterns)}개를 새 파일로 저장: {output_path}")
        self.logger.info(f"안전 규칙 YAML 생성: {output_path} ({len(safe_patterns)}개 규칙)")

def main():
    """메인 실행 함수"""
    print("🔍 Phase 2.2 패턴 검증 시스템 시작")
    print("=" * 50)
    
    # PatternValidator 초기화
    validator = PatternValidator()
    
    # 39개 규칙 전체 검증 실행
    print("📋 39개 Phase 2 학습 규칙 검증 시작...")
    results = validator.validate_all_patterns()
    
    if "error" not in results:
        # 안전한 규칙들로 새 YAML 생성
        print("\n🔧 안전한 규칙만으로 새 YAML 생성...")
        validator.generate_safe_rules_yaml(results)
        
        print("\n🎯 권장 사항:")
        print(f"  ✅ 즉시 적용 가능: {len(results['recommendations']['safe_for_production'])}개 규칙")
        print(f"  🔧 Context-aware 변환 필요: {len(results['recommendations']['needs_context_aware'])}개 규칙")
        print(f"  ❌ 적용 금지: {len(results['recommendations']['should_reject'])}개 규칙")
        
        # 다음 단계 안내
        print("\n📅 다음 단계:")
        print("  1. tools/pattern_validation_results.json 검토")
        print("  2. tools/safe_rules_filtered.yaml 확인")
        print("  3. Context-aware 규칙 변환 시스템 구현")
        print("  4. A/B 테스트 프레임워크 구축")
    
    print("\n✅ Phase 2.2-1단계 (PatternValidator) 완료!")

if __name__ == "__main__":
    main()