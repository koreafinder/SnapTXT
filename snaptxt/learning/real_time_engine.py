#!/usr/bin/env python3
"""
실시간 패턴 학습 엔진 - Phase 2.2

수집된 사용자 피드백을 실시간으로 분석하여 
새로운 후처리 패턴을 학습하고 기존 규칙을 개선하는 시스템
"""

import json
import yaml
import re
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict, Counter
import logging

# 피드백 수집기 import
from feedback_collector import UserFeedbackCollector

class RealTimeLearningEngine:
    """실시간 패턴 학습 및 규칙 개선 엔진"""
    
    def __init__(self):
        self.collector = UserFeedbackCollector()
        self.learning_dir = Path("learning_data")
        self.learning_dir.mkdir(exist_ok=True)
        
        self.rules_file = Path("stage3_rules.yaml")
        self.learned_rules_file = self.learning_dir / "learned_rules.yaml"
        self.learning_log = self.learning_dir / "learning_engine.log"
        
        # 학습 설정
        self.min_pattern_frequency = 3  # 최소 발생 빈도
        self.min_pattern_confidence = 0.8  # 최소 신뢰도
        self.learning_interval = 300  # 5분마다 학습 (초)
        
        # 실시간 학습 상태
        self.learning_active = False
        self.learning_thread = None
        
        # 패턴 캐시
        self.pattern_cache = {}
        self.last_learning_time = None
        
        self.setup_logging()
        
    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.learning_log),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def start_real_time_learning(self):
        """실시간 학습 시작"""
        if self.learning_active:
            self.logger.info("⚠️ 실시간 학습이 이미 활성화되어 있습니다")
            return
            
        self.learning_active = True
        self.learning_thread = threading.Thread(target=self._learning_loop, daemon=True)
        self.learning_thread.start()
        
        self.logger.info("🚀 실시간 패턴 학습 엔진 시작")
        
    def stop_real_time_learning(self):
        """실시간 학습 중지"""
        self.learning_active = False
        if self.learning_thread and self.learning_thread.is_alive():
            self.learning_thread.join(timeout=5)
            
        self.logger.info("⏹️ 실시간 패턴 학습 엔진 중지")
        
    def _learning_loop(self):
        """학습 루프 (백그라운드 스레드)"""
        while self.learning_active:
            try:
                self._perform_learning_cycle()
                time.sleep(self.learning_interval)
            except Exception as e:
                self.logger.error(f"❌ 학습 사이클 오류: {e}")
                time.sleep(60)  # 오류 시 1분 대기
    
    def _perform_learning_cycle(self):
        """학습 사이클 실행"""
        self.logger.info("🔄 학습 사이클 시작")
        
        # 1. 새로운 피드백 데이터 확인
        new_feedbacks = self._get_new_feedbacks()
        if not new_feedbacks:
            self.logger.info("📭 새로운 피드백 없음")
            return
            
        self.logger.info(f"📝 새로운 피드백: {len(new_feedbacks)}개")
        
        # 2. 패턴 분석 및 학습
        learned_patterns = self._analyze_and_learn_patterns(new_feedbacks)
        
        # 3. 고품질 패턴 필터링
        quality_patterns = self._filter_quality_patterns(learned_patterns)
        
        # 4. 기존 규칙과 통합
        if quality_patterns:
            self._integrate_learned_patterns(quality_patterns)
            self.logger.info(f"✅ {len(quality_patterns)}개 패턴 학습 완료")
        
        # 5. 규칙 최적화
        self._optimize_existing_rules()
        
        self.last_learning_time = datetime.now()
        
    def _get_new_feedbacks(self) -> List[Dict]:
        """마지막 학습 이후 새로운 피드백 가져오기"""
        if not self.collector.feedback_log.exists():
            return []
            
        cutoff_time = self.last_learning_time or datetime.now() - timedelta(hours=24)
        new_feedbacks = []
        
        with open(self.collector.feedback_log, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    feedback = json.loads(line.strip())
                    feedback_time = datetime.fromisoformat(feedback['timestamp'])
                    
                    if feedback_time > cutoff_time:
                        new_feedbacks.append(feedback)
                        
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
                    
        return new_feedbacks
    
    def _analyze_and_learn_patterns(self, feedbacks: List[Dict]) -> List[Dict]:
        """피드백에서 패턴 분석 및 학습"""
        all_patterns = []
        pattern_frequency = Counter()
        pattern_examples = defaultdict(list)
        
        for feedback in feedbacks:
            patterns = feedback.get('extracted_patterns', [])
            
            for pattern in patterns:
                pattern_key = f"{pattern['pattern']}→{pattern['replacement']}"
                pattern_frequency[pattern_key] += 1
                pattern_examples[pattern_key].append({
                    'original': pattern.get('original_example', ''),
                    'timestamp': feedback['timestamp'],
                    'confidence': pattern.get('confidence', 0)
                })
                
                all_patterns.append(pattern)
        
        # 빈도 기반 패턴 신뢰도 조정
        enhanced_patterns = []
        for pattern in all_patterns:
            pattern_key = f"{pattern['pattern']}→{pattern['replacement']}"
            frequency = pattern_frequency[pattern_key]
            
            if frequency >= self.min_pattern_frequency:
                # 빈도가 높을수록 신뢰도 증가
                confidence_boost = min(0.2, (frequency - 1) * 0.05)
                enhanced_confidence = min(0.98, pattern['confidence'] + confidence_boost)
                
                enhanced_pattern = pattern.copy()
                enhanced_pattern['confidence'] = enhanced_confidence
                enhanced_pattern['frequency'] = frequency
                enhanced_pattern['examples'] = pattern_examples[pattern_key]
                
                enhanced_patterns.append(enhanced_pattern)
        
        return enhanced_patterns
    
    def _filter_quality_patterns(self, patterns: List[Dict]) -> List[Dict]:
        """고품질 패턴 필터링"""
        quality_patterns = []
        
        for pattern in patterns:
            # 기본 품질 조건
            if (pattern['confidence'] >= self.min_pattern_confidence and
                pattern['frequency'] >= self.min_pattern_frequency):
                
                # 추가 품질 검사
                if self._validate_pattern_quality(pattern):
                    quality_patterns.append(pattern)
                    self.logger.info(f"✅ 고품질 패턴: {pattern['pattern']} → {pattern['replacement']} (신뢰도: {pattern['confidence']:.0%})")
                else:
                    self.logger.info(f"⚠️ 품질 검사 실패: {pattern['pattern']}")
        
        return quality_patterns
    
    def _validate_pattern_quality(self, pattern: Dict) -> bool:
        """패턴 품질 검증"""
        pattern_text = pattern.get('pattern', '')
        replacement = pattern.get('replacement', '')
        
        # 1. 최소 길이 검사
        if len(pattern_text.strip()) < 2 or len(replacement.strip()) < 2:
            return False
        
        # 2. 정규식 유효성 검사
        try:
            re.compile(pattern_text)
        except re.error:
            return False
        
        # 3. 한국어 유효성 검사
        korean_pattern = re.compile(r'[가-힣]')
        if not (korean_pattern.search(pattern_text) or korean_pattern.search(replacement)):
            # 한국어가 포함되지 않은 패턴은 영어 전용으로 검증
            if not re.match(r'^[a-zA-Z\s\-\.]+$', pattern_text + replacement):
                return False
        
        # 4. 공통 오류 패턴 감지
        known_good_patterns = [
            ('드러워', '드러났'),
            ('돌두', '몰두'),
            ('마이\\s*클\\s*싱\\s*어', '마이클 싱어'),
            ('명\\s*상\\s*가', '명상가')
        ]
        
        for good_old, good_new in known_good_patterns:
            if good_old in pattern_text and good_new in replacement:
                return True  # 알려진 좋은 패턴
        
        # 5. 사용자 빈도 기반 검증
        if pattern['frequency'] >= 5:  # 5회 이상 발생한 패턴은 신뢰
            return True
        
        return pattern['confidence'] >= 0.9  # 높은 신뢰도 필요
    
    def _integrate_learned_patterns(self, patterns: List[Dict]):
        """학습된 패턴을 기존 규칙과 통합"""
        # 기존 학습된 규칙 로드
        existing_learned = {}
        if self.learned_rules_file.exists():
            with open(self.learned_rules_file, 'r', encoding='utf-8') as f:
                existing_learned = yaml.safe_load(f) or {}
        
        # 새 패턴 추가/업데이트
        if 'stage3_postprocessing' not in existing_learned:
            existing_learned['stage3_postprocessing'] = {
                'spacing': [],
                'characters': [],
                'punctuation': [],
                'formatting': []
            }
        
        stage3 = existing_learned['stage3_postprocessing']
        
        for pattern in patterns:
            category = pattern.get('category', 'characters')
            
            # 중복 패턴 확인
            existing_patterns = {p.get('pattern', ''): i for i, p in enumerate(stage3[category])}
            pattern_key = pattern['pattern']
            
            rule = {
                'pattern': pattern['pattern'],
                'replacement': pattern['replacement'],
                'description': f"실시간 학습: {pattern.get('original_example', '')} → {pattern['replacement']}",
                'confidence': pattern['confidence'],
                'frequency': pattern['frequency'],
                'real_time_learned': True,
                'learned_at': datetime.now().isoformat(),
                'examples': pattern.get('examples', [])
            }
            
            if pattern_key in existing_patterns:
                # 기존 패턴 업데이트
                idx = existing_patterns[pattern_key]
                stage3[category][idx] = rule
                self.logger.info(f"🔄 패턴 업데이트: {pattern_key}")
            else:
                # 새 패턴 추가
                stage3[category].append(rule)
                self.logger.info(f"➕ 새 패턴 추가: {pattern_key}")
        
        # 메타데이터 업데이트
        existing_learned['metadata'] = {
            'last_updated': datetime.now().isoformat(),
            'real_time_learning': True,
            'total_learned_patterns': sum(len(stage3[cat]) for cat in stage3),
            'learning_engine_version': '2.0'
        }
        
        # 저장
        with open(self.learned_rules_file, 'w', encoding='utf-8') as f:
            yaml.dump(existing_learned, f, default_flow_style=False, 
                     allow_unicode=True, indent=2)
        
        self.logger.info(f"💾 학습된 규칙 저장: {self.learned_rules_file}")
        
    def _optimize_existing_rules(self):
        """기존 규칙 최적화"""
        try:
            # Phase 1 규칙과 학습된 규칙 통합 최적화
            if self.rules_file.exists() and self.learned_rules_file.exists():
                self._merge_phase1_and_learned_rules()
                
        except Exception as e:
            self.logger.error(f"❌ 규칙 최적화 오류: {e}")
    
    def _merge_phase1_and_learned_rules(self):
        """Phase 1 규칙과 실시간 학습 규칙 통합"""
        phase1_rules = {}
        learned_rules = {}
        
        # Phase 1 규칙 로드
        if self.rules_file.exists():
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                phase1_rules = yaml.safe_load(f)
        
        # 학습된 규칙 로드
        if self.learned_rules_file.exists():
            with open(self.learned_rules_file, 'r', encoding='utf-8') as f:
                learned_rules = yaml.safe_load(f)
        
        # 통합 규칙 생성
        if phase1_rules and learned_rules:
            merged_rules = self._create_merged_rules(phase1_rules, learned_rules)
            
            # 백업 후 적용
            backup_file = f"stage3_rules_backup_{int(time.time())}.yaml"
            if self.rules_file.exists():
                self.rules_file.rename(backup_file)
                self.logger.info(f"💾 기존 규칙 백업: {backup_file}")
            
            # 통합된 규칙 저장
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                yaml.dump(merged_rules, f, default_flow_style=False,
                         allow_unicode=True, indent=2)
            
            self.logger.info("🔄 Phase 1 + 실시간 학습 규칙 통합 완료")
    
    def _create_merged_rules(self, phase1_rules: Dict, learned_rules: Dict) -> Dict:
        """Phase 1과 학습된 규칙을 통합"""
        merged = phase1_rules.copy()
        
        if 'stage3_postprocessing' not in merged:
            merged['stage3_postprocessing'] = {
                'spacing': [], 'characters': [], 'punctuation': [], 'formatting': []
            }
        
        learned_stage3 = learned_rules.get('stage3_postprocessing', {})
        
        for category in ['spacing', 'characters', 'punctuation', 'formatting']:
            existing_patterns = {rule.get('pattern', ''): rule 
                               for rule in merged['stage3_postprocessing'][category]}
            
            for learned_rule in learned_stage3.get(category, []):
                pattern = learned_rule.get('pattern', '')
                
                if pattern in existing_patterns:
                    # 실시간 학습 규칙이 더 높은 빈도/신뢰도를 가지면 교체
                    existing_rule = existing_patterns[pattern]
                    if (learned_rule.get('frequency', 0) > existing_rule.get('frequency', 0) or
                        learned_rule.get('confidence', 0) > existing_rule.get('confidence', 0)):
                        existing_patterns[pattern] = learned_rule
                else:
                    # 새 규칙 추가
                    merged['stage3_postprocessing'][category].append(learned_rule)
            
            # 업데이트된 규칙 리스트 재구성
            merged['stage3_postprocessing'][category] = list(existing_patterns.values())
        
        # 메타데이터 업데이트
        merged['metadata'] = {
            'last_updated': datetime.now().isoformat(),
            'phase1_rules': True,
            'real_time_learning': True,
            'total_rules': sum(len(merged['stage3_postprocessing'][cat]) 
                             for cat in merged['stage3_postprocessing']),
            'merger_version': '2.0'
        }
        
        return merged
    
    def get_learning_statistics(self) -> Dict:
        """학습 통계 정보"""
        stats = {
            'learning_active': self.learning_active,
            'last_learning_time': self.last_learning_time.isoformat() if self.last_learning_time else None,
            'total_feedbacks': 0,
            'learned_patterns': 0,
            'phase1_patterns': 0,
            'total_active_patterns': 0
        }
        
        try:
            # 피드백 카운트
            if self.collector.feedback_log.exists():
                with open(self.collector.feedback_log, 'r', encoding='utf-8') as f:
                    stats['total_feedbacks'] = sum(1 for line in f)
            
            # 학습된 패턴 카운트
            if self.learned_rules_file.exists():
                with open(self.learned_rules_file, 'r', encoding='utf-8') as f:
                    learned = yaml.safe_load(f)
                    if learned and 'stage3_postprocessing' in learned:
                        stats['learned_patterns'] = sum(
                            len(learned['stage3_postprocessing'][cat])
                            for cat in learned['stage3_postprocessing']
                        )
            
            # Phase 1 패턴 카운트
            if self.rules_file.exists():
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    phase1 = yaml.safe_load(f)
                    if phase1 and 'stage3_postprocessing' in phase1:
                        all_rules = sum(
                            len(phase1['stage3_postprocessing'][cat])
                            for cat in phase1['stage3_postprocessing']
                        )
                        stats['total_active_patterns'] = all_rules
                        
                        # Phase 1 vs 실시간 학습 분리
                        phase1_count = sum(
                            1 for cat in phase1['stage3_postprocessing']
                            for rule in phase1['stage3_postprocessing'][cat]
                            if not rule.get('real_time_learned', False)
                        )
                        stats['phase1_patterns'] = phase1_count
        
        except Exception as e:
            self.logger.error(f"통계 수집 오류: {e}")
        
        return stats
    
    def force_learning_cycle(self):
        """강제로 학습 사이클 실행 (테스트용)"""
        self.logger.info("🔧 강제 학습 사이클 실행")
        self._perform_learning_cycle()


def main():
    """실시간 학습 엔진 테스트"""
    engine = RealTimeLearningEngine()
    
    print("🚀 실시간 패턴 학습 엔진 테스트")
    
    # 1. 강제 학습 사이클 실행
    engine.force_learning_cycle()
    
    # 2. 학습 통계 확인
    stats = engine.get_learning_statistics()
    print(f"\n📊 학습 통계:")
    print(f"   총 피드백: {stats['total_feedbacks']}개")
    print(f"   학습된 패턴: {stats['learned_patterns']}개")
    print(f"   Phase 1 패턴: {stats['phase1_patterns']}개")
    print(f"   전체 활성 패턴: {stats['total_active_patterns']}개")
    
    # 3. 실시간 학습 시작 (짧은 시간)
    print(f"\n🔄 실시간 학습 시작 (10초 테스트)")
    engine.learning_interval = 10  # 10초마다 학습
    engine.start_real_time_learning()
    
    try:
        time.sleep(15)  # 15초 대기
    finally:
        engine.stop_real_time_learning()
    
    print(f"✅ 실시간 학습 엔진 테스트 완료")


if __name__ == "__main__":
    main()