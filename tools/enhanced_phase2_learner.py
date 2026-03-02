#!/usr/bin/env python3
"""
개선된 Phase 2 학습 시스템 및 29개 샘플 테스트

더 정교한 차이점 분석과 패턴 추출을 통해
실제 OCR 오류를 효과적으로 학습하는 시스템
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

class EnhancedFeedbackLearner:
    """개선된 피드백 학습 시스템"""
    
    def __init__(self):
        self.learning_data_dir = Path("../snaptxt/learning/learning_data")
        self.learning_data_dir.mkdir(parents=True, exist_ok=True)
        
        self.learned_rules_file = self.learning_data_dir / "learned_rules.yaml"
        self.realistic_samples = self._create_realistic_samples()
    
    def _create_realistic_samples(self):
        """29개 이미지에 대한 현실적인 OCR 오류 시뮬레이션"""
        base_texts = [
            "마이클 싱어는 세계적으로 유명한 명상가이자 영적 지도자입니다.",
            "내면의 평화를 찾기 위해서는 일상의 작은 습관부터 바꿔나가야 합니다.", 
            "현재 순간에 집중하는 것이 무엇보다 중요합니다.",
            "감정을 관찰하되 동화되지 마세요. 분노가 일어날 때는 조심하세요.",
            "진정한 자유는 외부 상황에 좌우되지 않는 내면의 평온에서 나옵니다.",
            "호흡에 집중하는 것은 가장 기본적이면서도 강력한 명상법입니다.",
            "생각과 자아를 분리하는 연습을 해보세요.",
            "일상생활에서도 명상적 의식을 유지할 수 있습니다.",
            "타인과의 갈등에서 벗어나려면 먼저 자신의 마음을 평온히 해야 합니다.",
            "진실을 추구하는 것은 용기가 필요한 일입니다.",
            "에고의 목소리와 영혼의 목소리를 구분하는 법을 배워야 합니다.",
            "완전한 존재가 되려 노력하지 마세요.",
            "서두르지 마세요. 영적 성장은 하나의 여정입니다.",
            "과거의 상처에서 벗어나는 것은 쉽지 않습니다.",
            "감사하는 마음을 기르세요.",
            "명상은 도피가 아닙니다.",
            "다른 사람의 의견에 흔들리지 마세요.",
            "사랑은 조건이 없어야 합니다.",
            "고통을 피하려 하지 마세요.",
            "물질적 성공에만 매달리지 마세요.",
            "다른 사람을 판단하지 마세요.",
            "변화를 두려워하지 마세요.",
            "완벽을 추구하지 마세요.",
            "침묵의 힘을 알아보세요.",
            "자연과 함께 시간을 보내세요.",
            "용서는 상대방을 위한 것이 아니라 자신을 위한 것입니다.",
            "지금 이 순간이 모든 것입니다.",
            "내면의 성전을 건설하세요.",
            "사랑과 두려움 중 항상 사랑을 선택하세요."
        ]
        
        samples = []
        for i, text in enumerate(base_texts, 1):
            # 현실적인 OCR 오류 생성
            corrupted = self._apply_realistic_ocr_errors(text)
            
            samples.append({
                "image_id": f"IMG_47{88+i}",
                "original_text": text,
                "ocr_result": corrupted,
                "error_level": random.choice(["light", "medium", "heavy"])
            })
        
        return samples
    
    def _apply_realistic_ocr_errors(self, text):
        """현실적인 OCR 오류 적용"""
        corrupted = text
        
        # 1. 띄어쓰기 오류 (높은 확률)
        if random.random() < 0.8:
            # 무작위 위치에서 띄어쓰기 제거
            words = corrupted.split()
            if len(words) >= 2:
                merge_count = random.randint(1, min(3, len(words)-1))
                for _ in range(merge_count):
                    pos = random.randint(0, len(words)-2)
                    words[pos] = words[pos] + words[pos+1]
                    words.pop(pos+1)
                corrupted = ' '.join(words)
        
        # 2. 구두점 앞 공백 추가 (높은 확률)
        if random.random() < 0.7:
            corrupted = re.sub(r'([.!?,:;])', r' \1', corrupted)
        
        # 3. 특정 문자 오인식 (중간 확률)
        if random.random() < 0.5:
            char_errors = [
                ('다', '도'), ('요', '여'), ('습니다', '습니 다'),
                ('것입니다', '것입니 다'), ('합니다', '합니 다'),
                ('입니다', '입니 다'), ('동', '둥'), ('정', '청')
            ]
            error = random.choice(char_errors)
            corrupted = corrupted.replace(error[0], error[1])
        
        # 4. 숫자/영문과 한글 사이 공백 제거 (낮은 확률)
        if random.random() < 0.3:
            corrupted = re.sub(r'(\w)\s([가-힣])', r'\1\2', corrupted)
            corrupted = re.sub(r'([가-힣])\s(\w)', r'\1\2', corrupted)
        
        return corrupted
    
    def extract_patterns_from_correction(self, original_ocr, corrected_text):
        """개선된 패턴 추출"""
        patterns = []
        
        # 1. 간단한 문자열 교체 패턴 찾기
        simple_replacements = self._find_simple_replacements(original_ocr, corrected_text)
        patterns.extend(simple_replacements)
        
        # 2. 띄어쓰기 패턴 찾기  
        spacing_patterns = self._find_spacing_patterns(original_ocr, corrected_text)
        patterns.extend(spacing_patterns)
        
        # 3. 구두점 패턴 찾기
        punctuation_patterns = self._find_punctuation_patterns(original_ocr, corrected_text)
        patterns.extend(punctuation_patterns)
        
        return patterns
    
    def _find_simple_replacements(self, original, corrected):
        """단순 문자열 교체 패턴 찾기"""
        patterns = []
        
        # difflib로 차이점 찾기
        matcher = difflib.SequenceMatcher(None, original, corrected)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                old_text = original[i1:i2].strip()
                new_text = corrected[j1:j2].strip()
                
                if old_text and new_text and len(old_text) <= 10:
                    # 단어 경계 고려
                    pattern_regex = rf'\b{re.escape(old_text)}\b'
                    
                    patterns.append({
                        'pattern': pattern_regex,
                        'replacement': new_text,
                        'category': 'characters',
                        'confidence': 0.85,
                        'frequency': 1,
                        'description': f'문자 교체: {old_text} → {new_text}',
                        'learned_at': datetime.now().isoformat(),
                        'source_type': 'simple_replacement'
                    })
        
        return patterns
    
    def _find_spacing_patterns(self, original, corrected):
        """띄어쓰기 패턴 찾기"""
        patterns = []
        
        # 1. 공백 추가가 필요한 패턴
        # 연결된 단어들 찾기
        import re
        
        # 한글 연속 → 띄어쓰기로 분리된 패턴 찾기
        original_words = re.findall(r'[가-힣]+', original)
        corrected_words = re.findall(r'[가-힣]+', corrected) 
        
        # 원본에서 긴 단어가 수정본에서 여러 짧은 단어로 분리된 경우
        for orig_word in original_words:
            if len(orig_word) > 4:  # 충분히 긴 단어
                # 수정본에서 이 단어가 분리되었는지 확인
                if orig_word in original and orig_word not in corrected:
                    # 대략적인 분리 패턴 생성
                    # 예: "생각과자아를" → "생각과 자아를"
                    spacing_pattern = self._create_spacing_pattern(orig_word, corrected)
                    if spacing_pattern:
                        patterns.append(spacing_pattern)
        
        # 2. 구두점 앞 공백 제거 패턴
        punct_spacing = re.findall(r'\s+([.!?,:;])', original)
        if punct_spacing:
            patterns.append({
                'pattern': r'\s+([.!?,:;])',
                'replacement': r'\1',
                'category': 'spacing',
                'confidence': 0.90,
                'frequency': 1,
                'description': '구두점 앞 불필요한 공백 제거',
                'learned_at': datetime.now().isoformat(),
                'source_type': 'punctuation_spacing'
            })
        
        return patterns
    
    def _create_spacing_pattern(self, long_word, corrected_text):
        """긴 단어를 분리하는 패턴 생성"""
        # 간단한 휴리스틱: 2-4글자씩 분리
        if len(long_word) >= 4:
            # 가능한 분리점 찾기
            for split_pos in range(2, len(long_word)-1):
                part1 = long_word[:split_pos]
                part2 = long_word[split_pos:]
                
                spaced_version = f"{part1} {part2}"
                if spaced_version in corrected_text:
                    return {
                        'pattern': re.escape(long_word),
                        'replacement': spaced_version,
                        'category': 'spacing',
                        'confidence': 0.80,
                        'frequency': 1,
                        'description': f'단어 분리: {long_word} → {spaced_version}',
                        'learned_at': datetime.now().isoformat(),
                        'source_type': 'word_splitting'
                    }
        
        return None
    
    def _find_punctuation_patterns(self, original, corrected):
        """구두점 패턴 찾기"""
        patterns = []
        
        # 구두점 변화 찾기
        orig_puncts = re.findall(r'[.!?,:;ㅏㅓㅗㅜㅡㅣ]', original)
        corr_puncts = re.findall(r'[.!?,:;]', corrected)
        
        # 한글 자모가 구두점으로 변경된 패턴
        for orig_char in orig_puncts:
            if orig_char in 'ㅏㅓㅗㅜㅡㅣ':
                patterns.append({
                    'pattern': re.escape(orig_char),
                    'replacement': '.',
                    'category': 'punctuation', 
                    'confidence': 0.95,
                    'frequency': 1,
                    'description': f'한글 자모 오인식 수정: {orig_char} → .',
                    'learned_at': datetime.now().isoformat(),
                    'source_type': 'char_to_punct'
                })
        
        return patterns
    
    def learn_from_samples(self):
        """29개 샘플에서 패턴 학습"""
        print("🧠 29개 샘플에서 Phase 2 패턴 학습 시작...")
        
        all_learned_patterns = []
        
        for i, sample in enumerate(self.realistic_samples, 1):
            print(f"   [{i:2d}/29] {sample['image_id']} 학습 중...")
            
            # 패턴 추출
            patterns = self.extract_patterns_from_correction(
                sample['ocr_result'], 
                sample['original_text']
            )
            
            all_learned_patterns.extend(patterns)
            
            if i % 5 == 0:
                print(f"      진행률: {i}/29 ({i/29*100:.1f}%), 누적 패턴: {len(all_learned_patterns)}개")
        
        print(f"\n✅ 총 {len(all_learned_patterns)}개 패턴 학습 완료!")
        
        # 패턴 통계
        categories = {}
        for pattern in all_learned_patterns:
            cat = pattern['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"📊 카테고리별 패턴:")
        for cat, count in categories.items():
            print(f"   {cat}: {count}개")
        
        return all_learned_patterns
    
    def consolidate_patterns(self, patterns):
        """패턴 통합 및 최적화"""
        print(f"\n🔧 패턴 통합 및 최적화...")
        
        # 중복 패턴 제거 및 빈도 계산
        pattern_map = {}
        
        for pattern in patterns:
            key = f"{pattern['pattern']}→{pattern['replacement']}"
            
            if key in pattern_map:
                # 기존 패턴 빈도 증가
                pattern_map[key]['frequency'] += 1
                # 신뢰도 점진적 증가
                current_conf = pattern_map[key]['confidence']
                pattern_map[key]['confidence'] = min(current_conf + 0.05, 0.95)
            else:
                pattern_map[key] = pattern
        
        consolidated = list(pattern_map.values())
        
        # 고품질 패턴 필터링 (빈도 2 이상 또는 신뢰도 0.85 이상)
        high_quality = [
            p for p in consolidated 
            if p['frequency'] >= 2 or p['confidence'] >= 0.85
        ]
        
        print(f"✅ 통합 완료:")
        print(f"   전체 패턴: {len(consolidated)}개")
        print(f"   고품질 패턴: {len(high_quality)}개")
        
        return high_quality
    
    def save_learned_rules(self, patterns):
        """학습된 규칙을 YAML 형식으로 저장"""
        print(f"\n💾 학습된 규칙 저장...")
        
        # 카테고리별 분류
        rules_by_category = {
            'spacing': [],
            'characters': [],
            'punctuation': [],
            'formatting': []
        }
        
        for pattern in patterns:
            category = pattern['category']
            if category in rules_by_category:
                rules_by_category[category].append(pattern)
        
        # YAML 구조 생성
        yaml_structure = {
            'stage3_postprocessing': rules_by_category,
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'pattern_count': len(patterns),
                'learning_source': '29_sample_images',
                'phase2_learning': True
            }
        }
        
        # 파일 저장
        with open(self.learned_rules_file, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_structure, f, default_flow_style=False, 
                     allow_unicode=True, indent=2)
        
        print(f"✅ 저장 완료: {self.learned_rules_file}")
        
    def test_auto_application(self):
        """자동 적용 시스템 테스트"""
        print(f"\n⚡ 자동 적용 시스템 테스트...")
        
        try:
            # AutoRuleApplicator import를 여기서 해서 경로 문제 회피
            import sys
            sys.path.append(str(Path(__file__).parent.parent))
            from snaptxt.learning.auto_applicator import AutoRuleApplicator
            
            applicator = AutoRuleApplicator()
            
            # 분석 실행
            analysis = applicator.analyze_learned_rules()
            
            print(f"📊 자동 적용 분석 결과:")
            print(f"   총 학습된 규칙: {analysis.get('total', 0)}개")
            print(f"   적용 준비 완료: {len(analysis.get('ready_rules', []))}개")
            print(f"   대기 중: {len(analysis.get('pending_rules', []))}개")
            
            return analysis
            
        except Exception as e:
            print(f"❌ 자동 적용 테스트 오류: {e}")
            return {}
    
    def run_full_enhanced_test(self):
        """전체 개선된 학습 테스트 실행"""
        print("🚀 개선된 Phase 2 학습 시스템 테스트 (29개 샘플)")
        print("="*65)
        
        # 1. 샘플에서 패턴 학습
        raw_patterns = self.learn_from_samples()
        
        # 2. 패턴 통합 및 최적화
        quality_patterns = self.consolidate_patterns(raw_patterns)
        
        # 3. 학습된 규칙 저장
        self.save_learned_rules(quality_patterns)
        
        # 4. 자동 적용 시스템 테스트
        auto_analysis = self.test_auto_application()
        
        print("\n" + "="*65)
        print("🎉 개선된 Phase 2 학습 시스템 테스트 완료!")
        print("="*65)
        
        print(f"📊 최종 결과:")
        print(f"   원시 패턴: {len(raw_patterns)}개")
        print(f"   고품질 패턴: {len(quality_patterns)}개")
        print(f"   적용 준비 규칙: {len(auto_analysis.get('ready_rules', []))}개")
        
        # 품질 점수 계산
        quality_score = (len(quality_patterns) / 29) * 100  # 이미지당 패턴 수
        print(f"📈 품질 점수: {quality_score:.1f}점 (이미지당 {quality_patterns.__len__()/29:.1f}개 패턴)")
        
        if quality_score >= 50:
            print("🎉 우수한 학습 성과!")
        elif quality_score >= 30:
            print("👍 양호한 학습 성과!")
        else:
            print("⚠️ 학습 성과 개선 필요")
        
        return {
            "raw_patterns": len(raw_patterns),
            "quality_patterns": len(quality_patterns),
            "ready_for_application": len(auto_analysis.get('ready_rules', [])),
            "quality_score": quality_score
        }


def main():
    """개선된 Phase 2 학습 시스템 테스트 실행"""
    learner = EnhancedFeedbackLearner()
    result = learner.run_full_enhanced_test()
    return result

if __name__ == "__main__":
    main()