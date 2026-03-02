#!/usr/bin/env python3
"""
29개 완전 데이터셋 기반 고급 Phase 2 학습 시스템

Ground Truth 데이터를 실제 활용하여 더 정확하고 
현실적인 OCR 오류 패턴을 학습하는 고급 시스템
"""

import os
import re
import json
import yaml
import time
import difflib
from datetime import datetime
from pathlib import Path
import random

class GroundTruthBasedLearner:
    """Ground Truth 기반 고급 Phase 2 학습 시스템"""
    
    def __init__(self):
        self.learning_data_dir = Path("../learning_data")
        self.learning_data_dir.mkdir(parents=True, exist_ok=True)
        
        self.ground_truth_file = Path("../samples/ground_truth/ground_truth.json")
        self.learned_rules_file = self.learning_data_dir / "learned_rules_advanced.yaml"
        
        # Ground Truth 데이터 로드
        self.ground_truth = self._load_ground_truth()
        
        # 29개 이미지 리스트 
        self.image_list = [f"IMG_{i}" for i in range(4789, 4818)]
        
        print(f"🎯 Ground Truth 기반 학습 시스템 초기화")
        print(f"📚 로드된 데이터: {len(self.ground_truth)}개")
        
    def _load_ground_truth(self) -> dict:
        """Ground Truth JSON 데이터 로드"""
        if not self.ground_truth_file.exists():
            print(f"❌ Ground Truth 파일 없음: {self.ground_truth_file}")
            return {}
            
        with open(self.ground_truth_file, 'r', encoding='utf-8') as f:
            gt_data = json.load(f)
            
        ground_truth = gt_data.get('ground_truth', {})
        print(f"📖 Ground Truth 로드: {len(ground_truth)}개 텍스트")
        
        return ground_truth
    
    def generate_realistic_ocr_errors(self, original_text: str, error_intensity: float = 0.3) -> str:
        """Ground Truth 텍스트에서 현실적인 OCR 오류 생성"""
        corrupted = original_text
        
        # 1. 한글 자소 오인식 (가장 흔한 OCR 오류)
        char_substitutions = {
            # 자음 오인식
            'ㄱ': ['ㄴ', 'ㄷ'], 'ㄴ': ['ㄱ', 'ㅁ'], 'ㄷ': ['ㄹ', 'ㅂ'], 
            'ㄹ': ['ㄷ', 'ㅁ'], 'ㅁ': ['ㄴ', 'ㅂ'], 'ㅂ': ['ㅍ', 'ㅁ'],
            'ㅅ': ['ㅈ', 'ㅊ'], 'ㅈ': ['ㅊ', 'ㅅ'], 'ㅊ': ['ㅈ', 'ㅌ'],
            'ㅋ': ['ㅌ', 'ㅍ'], 'ㅌ': ['ㅍ', 'ㅋ'], 'ㅍ': ['ㅂ', 'ㅌ'],
            'ㅎ': ['ㅕ', 'ㅗ'],
            # 모음 오인식  
            'ㅏ': ['ㅓ', 'ㅑ'], 'ㅓ': ['ㅏ', 'ㅕ'], 'ㅗ': ['ㅜ', 'ㅛ'],
            'ㅜ': ['ㅗ', 'ㅠ'], 'ㅡ': ['ㅣ', 'ㅜ'], 'ㅣ': ['ㅡ', 'ㅏ']
        }
        
        # 2. 완성된 글자 단위 오인식 
        word_substitutions = {
            # 형태가 비슷한 글자
            '명': ['명', '멍', '병'], '상': ['상', '샹', '강'], 
            '가': ['가', '거', '고'], '는': ['는', '늘', '능'],
            '이': ['이', '리', '기'], '의': ['의', '에', '어'],
            '을': ['을', '올', '일'], '에': ['에', '예', '어'],
            '과': ['과', '괘', '광'], '로': ['로', '료', '노'],
            '마': ['마', '머', '모'], '심': ['심', '십', '신'],
            '든': ['든', '들', '돈'], '것': ['것', '걷', '겷'],
            '할': ['할', '한', '향'], '수': ['수', '추', '소'],
            '있': ['있', '잇', '었'], '어': ['어', '여', '오'],
            '하': ['하', '허', '호'], '그': ['그', '글', '긍'],
            '자': ['자', '저', '조'], '기': ['기', '가', '고'],
            '때': ['때', '댸', '돼'], '다': ['다', '더', '도']
        }
        
        # 3. 띄어쓰기 오류
        # 3-1. 불필요한 공백 삽입
        if random.random() < error_intensity:
            # 복합어나 긴 단어를 분리
            long_words = ['마이클싱어', '명상가', '영적지도자', '내면세계', '현재순간', '일상생활']
            for word in long_words:
                if word in corrupted:
                    # 중간에 공백 삽입
                    mid = len(word) // 2
                    new_word = word[:mid] + ' ' + word[mid:]
                    corrupted = corrupted.replace(word, new_word)
        
        # 3-2. 필수 공백 제거
        if random.random() < error_intensity * 0.7:
            # 단어 사이 공백을 랜덤하게 제거
            words = corrupted.split(' ')
            if len(words) > 2:
                # 랜덤하게 일부 공백 제거 
                merge_indices = random.sample(range(len(words)-1), min(2, len(words)-1))
                for i in sorted(merge_indices, reverse=True):
                    words[i] = words[i] + words[i+1]
                    del words[i+1]
                corrupted = ' '.join(words)
        
        # 4. 구두점 주변 공백 오류 
        if random.random() < error_intensity:
            # 구두점 앞에 불필요한 공백 추가
            corrupted = re.sub(r'([.!?,:;])', r' \1', corrupted)
            
        # 5. 글자 단위 변형 적용 
        for char, substitutes in char_substitutions.items():
            if char in corrupted and random.random() < error_intensity * 0.4:
                substitute = random.choice(substitutes)
                # 첫 번째로 발견된 글자만 변경 (과도한 변형 방지)
                corrupted = corrupted.replace(char, substitute, 1)
                
        # 6. 단어 단위 변형 적용
        for word, substitutes in word_substitutions.items():
            if word in corrupted and random.random() < error_intensity * 0.5:
                substitute = random.choice(substitutes)
                corrupted = corrupted.replace(word, substitute, 1)
        
        return corrupted
    
    def analyze_ocr_patterns(self, original: str, corrupted: str) -> list:
        """OCR 오류 패턴 정밀 분석"""
        patterns = []
        
        # 1. difflib를 사용한 정확한 차이점 분석
        differ = difflib.SequenceMatcher(None, original, corrupted)
        opcodes = differ.get_opcodes()
        
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'replace':
                original_part = original[i1:i2]
                corrupted_part = corrupted[j1:j2]
                
                # 의미있는 패턴만 수집 (단순 오타 제외)
                if len(original_part) >= 1 and len(corrupted_part) >= 1:
                    pattern = {
                        'type': 'character_substitution',
                        'original': original_part,
                        'corrupted': corrupted_part,
                        'context_before': original[max(0, i1-5):i1],
                        'context_after': original[i2:min(len(original), i2+5)],
                        'frequency': 1,
                        'confidence': 0.8  # 초기 신뢰도
                    }
                    patterns.append(pattern)
            
            elif tag == 'insert':
                # 불필요한 문자 삽입 
                inserted_part = corrupted[j1:j2]
                if inserted_part.strip():  # 공백이 아닌 경우만
                    pattern = {
                        'type': 'character_insertion',
                        'original': '',
                        'corrupted': inserted_part,
                        'context_before': original[max(0, i1-3):i1] if i1 > 0 else '',
                        'context_after': original[i1:min(len(original), i1+3)],
                        'frequency': 1,
                        'confidence': 0.7
                    }
                    patterns.append(pattern)
            
            elif tag == 'delete':
                # 필수 문자 누락
                deleted_part = original[i1:i2]
                if deleted_part.strip():  # 공백이 아닌 경우만
                    pattern = {
                        'type': 'character_deletion',
                        'original': deleted_part,
                        'corrupted': '',
                        'context_before': original[max(0, i1-3):i1],
                        'context_after': original[i2:min(len(original), i2+3)],
                        'frequency': 1,
                        'confidence': 0.7
                    }
                    patterns.append(pattern)
        
        # 2. 띄어쓰기 패턴 분석
        spacing_patterns = self._analyze_spacing_patterns(original, corrupted)
        patterns.extend(spacing_patterns)
        
        return patterns
    
    def _analyze_spacing_patterns(self, original: str, corrupted: str) -> list:
        """띄어쓰기 오류 패턴 전용 분석"""
        patterns = []
        
        # 공백 제거된 경우 탐지
        orig_no_space = original.replace(' ', '')
        corr_no_space = corrupted.replace(' ', '')
        
        if orig_no_space == corr_no_space:  # 내용은 같고 공백만 다른 경우
            orig_words = original.split(' ')
            corr_words = corrupted.split(' ')
            
            if len(orig_words) != len(corr_words):
                pattern = {
                    'type': 'spacing_error',
                    'original': original,
                    'corrupted': corrupted,
                    'description': f"띄어쓰기 변경: {len(orig_words)}개 단어 → {len(corr_words)}개 단어",
                    'frequency': 1,
                    'confidence': 0.9
                }
                patterns.append(pattern)
        
        return patterns
    
    def collect_learning_data(self, num_simulations: int = 100) -> list:
        """29개 Ground Truth 데이터에서 학습 데이터 수집"""
        print(f"📊 {len(self.ground_truth)}개 텍스트에서 {num_simulations}회 시뮬레이션 시작")
        
        all_patterns = []
        processed_count = 0
        
        for simulation in range(num_simulations):
            # 랜덤하게 Ground Truth 텍스트 선택
            img_id = random.choice(list(self.ground_truth.keys()))
            original_text = self.ground_truth[img_id]['text']
            
            # 다양한 오류 강도로 시뮬레이션 
            error_intensity = random.uniform(0.2, 0.6)  # 20-60% 오류율
            corrupted_text = self.generate_realistic_ocr_errors(original_text, error_intensity)
            
            # 패턴 추출
            patterns = self.analyze_ocr_patterns(original_text, corrupted_text)
            
            for pattern in patterns:
                pattern['source_image'] = img_id
                pattern['content_type'] = self.ground_truth[img_id].get('content_type', 'unknown')
                pattern['difficulty'] = self.ground_truth[img_id].get('difficulty', 'medium')
                pattern['simulation_round'] = simulation + 1
            
            all_patterns.extend(patterns)
            processed_count += 1
            
            if processed_count % 20 == 0:
                print(f"   진행: {processed_count}/{num_simulations} ({len(all_patterns)}개 패턴 수집)")
        
        print(f"✅ 수집 완료: {len(all_patterns)}개 원시 패턴")
        return all_patterns
    
    def consolidate_patterns(self, raw_patterns: list) -> list:
        """패턴 통합 및 품질 관리 (고급 알고리즘)"""
        print(f"🔄 {len(raw_patterns)}개 원시 패턴 통합 시작")
        
        # 1. 패턴별로 그룹화
        pattern_groups = {}
        
        for pattern in raw_patterns:
            # 키 생성: 타입 + 원본 + 변환
            key = f"{pattern['type']}:{pattern['original']}→{pattern['corrupted']}"
            
            if key not in pattern_groups:
                pattern_groups[key] = {
                    'type': pattern['type'],
                    'original': pattern['original'],
                    'corrupted': pattern['corrupted'],
                    'examples': [],
                    'total_frequency': 0,
                    'confidence_scores': [],
                    'source_images': set(),
                    'content_types': set(),
                    'difficulties': set()
                }
            
            group = pattern_groups[key]
            group['examples'].append(pattern)
            group['total_frequency'] += pattern.get('frequency', 1)
            group['confidence_scores'].append(pattern.get('confidence', 0.5))
            group['source_images'].add(pattern.get('source_image', 'unknown'))
            group['content_types'].add(pattern.get('content_type', 'unknown'))
            group['difficulties'].add(pattern.get('difficulty', 'medium'))
        
        # 2. 고품질 패턴 선별
        quality_patterns = []
        min_frequency = 3  # 최소 3회 이상 발견된 패턴
        min_confidence = 0.6  # 평균 신뢰도 60% 이상
        
        for key, group in pattern_groups.items():
            avg_confidence = sum(group['confidence_scores']) / len(group['confidence_scores'])
            unique_sources = len(group['source_images'])
            
            # 품질 기준: 빈도 + 신뢰도 + 다양한 소스
            if (group['total_frequency'] >= min_frequency and 
                avg_confidence >= min_confidence and 
                unique_sources >= 2):  # 최소 2개 이미지에서 발견
                
                # 최종 규칙 생성
                rule = {
                    'type': group['type'],
                    'pattern': group['original'],
                    'replacement': group['corrupted'],
                    'frequency': group['total_frequency'],
                    'confidence': min(avg_confidence * 1.1, 1.0),  # 신뢰도 보정
                    'source_count': unique_sources,
                    'content_types': list(group['content_types']),
                    'difficulties': list(group['difficulties']),
                    'description': f"{group['type']} 오류: '{group['original']}' → '{group['corrupted']}'",
                    'examples': len(group['examples'])
                }
                
                quality_patterns.append(rule)
        
        # 3. 신뢰도순 정렬
        quality_patterns.sort(key=lambda x: (x['confidence'], x['frequency']), reverse=True)
        
        print(f"✅ 통합 완료: {len(quality_patterns)}개 고품질 패턴 (원시 {len(raw_patterns)}개 → 품질 {len(quality_patterns)}개)")
        
        # 4. 상위 패턴 요약 출력
        print(f"🏆 상위 5개 패턴:")
        for i, pattern in enumerate(quality_patterns[:5], 1):
            print(f"   {i}. {pattern['description']} (신뢰도: {pattern['confidence']:.0%}, 빈도: {pattern['frequency']})")
        
        return quality_patterns
    
    def save_learned_rules(self, patterns: list) -> str:
        """학습된 규칙을 YAML 파일로 저장"""
        # Stage3 규칙 형식으로 변환
        stage3_rules = {
            'stage3_postprocessing': {
                'spacing': [],
                'characters': [],
                'punctuation': [],
                'formatting': []
            }
        }
        
        for pattern in patterns:
            rule_type = pattern['type']
            
            # 카테고리 매핑
            if 'spacing' in rule_type or 'space' in pattern.get('description', ''):
                category = 'spacing'
            elif 'punctuation' in rule_type or any(p in pattern['pattern'] for p in '.!?,:;'):
                category = 'punctuation'
            elif 'format' in rule_type:
                category = 'formatting'
            else:
                category = 'characters'
            
            # YAML 규칙 형식으로 변환
            yaml_rule = {
                'pattern': pattern['pattern'],
                'replacement': pattern['replacement'],
                'confidence': round(pattern['confidence'], 2),
                'frequency': pattern['frequency'],
                'description': pattern['description'],
                'learned': True,
                'source_count': pattern['source_count']
            }
            
            stage3_rules['stage3_postprocessing'][category].append(yaml_rule)
        
        # 메타데이터 추가
        metadata = {
            'metadata': {
                'version': '2.0_advanced',
                'created_at': datetime.now().isoformat(),
                'total_patterns': len(patterns),
                'source': 'Ground Truth 기반 고급 학습',
                'training_images': len(self.ground_truth),
                'quality_threshold': {
                    'min_frequency': 3,
                    'min_confidence': 0.6,
                    'min_sources': 2
                }
            }
        }
        
        # YAML 저장
        full_rules = {**metadata, **stage3_rules}
        
        with open(self.learned_rules_file, 'w', encoding='utf-8') as f:
            yaml.dump(full_rules, f, indent=2, sort_keys=False, allow_unicode=True)
        
        print(f"💾 학습 규칙 저장: {self.learned_rules_file}")
        
        # 카테고리별 요약
        categories = stage3_rules['stage3_postprocessing']
        for cat, rules in categories.items():
            if rules:
                print(f"   📁 {cat}: {len(rules)}개 규칙")
        
        return str(self.learned_rules_file)
    
    def run_complete_learning_cycle(self, simulations: int = 100) -> dict:
        """전체 학습 사이클 실행"""
        print(f"🚀 Ground Truth 기반 고급 Phase 2 학습 시작")
        print(f"📊 데이터: {len(self.ground_truth)}개 이미지")
        print(f"🔄 시뮬레이션: {simulations}회")
        
        start_time = time.time()
        
        # 1. 학습 데이터 수집
        raw_patterns = self.collect_learning_data(simulations)
        
        # 2. 패턴 통합 및 품질 관리
        quality_patterns = self.consolidate_patterns(raw_patterns)
        
        # 3. 규칙 저장
        rules_file = self.save_learned_rules(quality_patterns)
        
        # 4. 결과 요약
        elapsed = time.time() - start_time
        
        result = {
            'training_summary': {
                'ground_truth_images': len(self.ground_truth),
                'simulations': simulations,
                'raw_patterns': len(raw_patterns),
                'quality_patterns': len(quality_patterns),
                'quality_rate': len(quality_patterns) / len(raw_patterns) if raw_patterns else 0,
                'rules_file': rules_file,
                'training_time': round(elapsed, 2),
                'completion_time': datetime.now().isoformat()
            },
            'quality_patterns': quality_patterns
        }
        
        print(f"\n🎉 학습 완료!")
        print(f"   ⏱️ 소요 시간: {elapsed:.1f}초")
        print(f"   📈 품질율: {result['training_summary']['quality_rate']:.1%}")
        print(f"   🎯 최종 규칙: {len(quality_patterns)}개")
        
        return result


def main():
    """메인 실행 함수"""
    learner = GroundTruthBasedLearner()
    
    # 29개 데이터 기반 고급 학습 실행
    result = learner.run_complete_learning_cycle(simulations=150)  # 더 많은 시뮬레이션
    
    return result


if __name__ == "__main__":
    main()