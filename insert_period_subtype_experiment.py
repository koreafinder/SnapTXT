"""
INSERT["."] Subtype 분리 및 Event-Consistent 성공 기준 실험
============================================================

핵심 개선사항:
1. INSERT["."]를 "sentence-final" vs "abbr/initial" subtype으로 분리
2. 성공 기준을 "event-consistent" (실제 OCR 패턴 재현)으로 엄격화
3. Random vs Context-aware를 각 subtype별로 정확히 비교
"""

import re
from typing import List, Tuple, Optional, Dict
from enum import Enum

print('🔬 INSERT["."] Subtype 분리 및 Event-Consistent 성공 기준 실험')
print('='*80)

class PeriodInsertType(Enum):
    SENTENCE_FINAL = "sentence_final"    # 문장 끝 마침표 누락
    ABBREVIATION = "abbreviation"        # 약어 마침표 누락 (Dr, Mr, Prof 등)
    INITIAL = "initial"                  # 이니셜 마침표 누락 (A, B, C 등)

# Event-consistent GT 텍스트 풀 (subtype 분리)
gt_text_subtypes = {
    PeriodInsertType.SENTENCE_FINAL: [
        {"gt": "This is a test sentence", "expected_insert_pos": 24, "context": "문장 완성"},
        {"gt": "The result was very successful", "expected_insert_pos": 30, "context": "형용사 끝"},  
        {"gt": "They worked hard today", "expected_insert_pos": 22, "context": "부사 끝"},
        {"gt": "The book explains everything clearly", "expected_insert_pos": 35, "context": "부사 끝"},
        {"gt": "Chapter 5 covers the main topic", "expected_insert_pos": 31, "context": "명사 끝"},
    ],
    
    PeriodInsertType.ABBREVIATION: [
        {"gt": "Dr Smith is a good person", "expected_insert_pos": 2, "context": "Dr 호칭"},
        {"gt": "Mr Johnson worked hard today", "expected_insert_pos": 2, "context": "Mr 호칭"},
        {"gt": "Prof Kim has many students", "expected_insert_pos": 4, "context": "Prof 호칭"},
        {"gt": "Mrs Chen announced the news", "expected_insert_pos": 3, "context": "Mrs 호칭"},
        {"gt": "vs other approaches today", "expected_insert_pos": 2, "context": "vs 약어"},
    ],
    
    PeriodInsertType.INITIAL: [
        {"gt": "Michael A Singer wrote this book", "expected_insert_pos": 9, "context": "중간 이름 이니셜"},
        {"gt": "John B Watson did research", "expected_insert_pos": 6, "context": "중간 이름 이니셜"},
        {"gt": "Mary C Johnson is the author", "expected_insert_pos": 6, "context": "중간 이름 이니셜"},
        {"gt": "David R Smith published papers", "expected_insert_pos": 7, "context": "중간 이름 이니셜"},
        {"gt": "Sarah T Lee studied medicine", "expected_insert_pos": 7, "context": "중간 이름 이니셜"},
    ]
}

class EventConsistentValidator:
    """Event-consistent 성공 기준 검증기"""
    
    def is_event_consistent(self, gt: str, result: str, expected_pos: int, insert_type: PeriodInsertType) -> Tuple[bool, str]:
        """실제 OCR 오류 패턴과 일치하는지 검증"""
        
        # 1. 기본 검증: 정확히 한 개의 마침표가 추가되었는가?
        if result.count('.') == gt.count('.') + 1:
            pass  # 정확히 1개 추가됨
        else:
            return False, f"마침표 개수 불일치: {gt.count('.')} → {result.count('.')}"
        
        # 2. 예상 위치에 마침표가 있는가?
        if len(result) > expected_pos and result[expected_pos] == '.':
            expected_result = gt[:expected_pos] + '.' + gt[expected_pos:]
            if result == expected_result:
                return True, f"정확한 위치 {expected_pos}에 삽입 성공"
            else:
                return False, f"예상결과 불일치: {expected_result} vs {result}"
        
        # 3. Subtype별 추가 검증
        if insert_type == PeriodInsertType.SENTENCE_FINAL:
            # 문장 끝에만 마침표가 있어야 함
            if result.endswith('.') and gt + '.' == result:
                return True, "문장 끝 마침표 정확"
            else:
                return False, f"문장 끝이 아닌 위치에 삽입: {result}"
        
        elif insert_type == PeriodInsertType.ABBREVIATION:
            # 약어 뒤에 마침표가 있어야 함
            abbr_patterns = [r'\bDr\.', r'\bMr\.', r'\bProf\.', r'\bMrs\.', r'\bvs\.', r'\bMs\.']
            for pattern in abbr_patterns:
                if re.search(pattern, result):
                    return True, f"약어 패턴 매칭: {pattern}"
            return False, f"약어 패턴 불일치: {result}"
        
        elif insert_type == PeriodInsertType.INITIAL:
            # 이니셜 뒤에 마침표가 있어야 함  
            initial_pattern = r'\b[A-Z]\.'
            if re.search(initial_pattern, result):
                return True, f"이니셜 패턴 매칭: {initial_pattern}"
            return False, f"이니셜 패턴 불일치: {result}"
        
        return False, "알 수 없는 오류"

class ImprovedContextInserter:
    """개선된 Context-aware 삽입기 (Subtype별 특화)"""
    
    def context_aware_insert_by_type(self, gt: str, insert_type: PeriodInsertType) -> Tuple[str, str, float, int]:
        """Subtype별 Context-aware 삽입"""
        
        if insert_type == PeriodInsertType.SENTENCE_FINAL:
            return self._insert_sentence_final(gt)
        elif insert_type == PeriodInsertType.ABBREVIATION:
            return self._insert_abbreviation(gt)
        elif insert_type == PeriodInsertType.INITIAL:
            return self._insert_initial(gt)
        else:
            return gt, "unknown_type", 0.0, -1
    
    def _insert_sentence_final(self, gt: str) -> Tuple[str, str, float, int]:
        """문장 끝 마침표 삽입"""
        pos = len(gt)
        result = gt + "."
        return result, "sentence_end", 0.9, pos
    
    def _insert_abbreviation(self, gt: str) -> Tuple[str, str, float, int]:
        """약어 마침표 삽입"""
        abbr_patterns = [
            (r'(\bDr)(\s+)', 2),       # Dr Smith → Dr. Smith  
            (r'(\bMr)(\s+)', 2),       # Mr Johnson → Mr. Johnson
            (r'(\bProf)(\s+)', 4),     # Prof Kim → Prof. Kim
            (r'(\bMrs)(\s+)', 3),      # Mrs Chen → Mrs. Chen
            (r'(\bMs)(\s+)', 2),       # Ms Lee → Ms. Lee
            (r'(\bvs)(\s+)', 2),       # vs other → vs. other
        ]
        
        for pattern, insert_pos_offset in abbr_patterns:
            match = re.search(pattern, gt)
            if match:
                pos = match.start() + insert_pos_offset
                result = gt[:pos] + '.' + gt[pos:]
                return result, f"abbr_{match.group(1).lower()}", 0.8, pos
        
        # 약어 패턴 없으면 실패
        return gt, "no_abbr_pattern", 0.0, -1
    
    def _insert_initial(self, gt: str) -> Tuple[str, str, float, int]:
        """이니셜 마침표 삽입"""
        # First Middle Last 패턴 탐지
        initial_pattern = r'(\b[A-Z][a-z]+\s+)([A-Z])(\s+[A-Z][a-z]+)'
        match = re.search(initial_pattern, gt)
        
        if match:
            pos = match.start() + len(match.group(1)) + 1  # 이니셜 뒤
            result = gt[:pos] + '.' + gt[pos:]
            return result, f"initial_{match.group(2)}", 0.85, pos
        
        # 이니셜 패턴 없으면 실패
        return gt, "no_initial_pattern", 0.0, -1

class RandomInserter:
    """Random 삽입기 (기존 방식)"""
    
    def random_insert_by_type(self, gt: str, insert_type: PeriodInsertType) -> Tuple[str, str, float, int]:
        """Subtype과 무관하게 단순 끝 추가"""
        pos = len(gt)
        result = gt + "."
        return result, "random_end", 0.5, pos

def run_subtype_experiment():
    """Subtype별 Random vs Context-aware 비교 실험"""
    
    context_inserter = ImprovedContextInserter()
    random_inserter = RandomInserter()
    validator = EventConsistentValidator()
    
    print('\n=== Event-Consistent 성공 기준 Subtype별 실험 ===')
    
    for insert_type, test_cases in gt_text_subtypes.items():
        print(f'\n🔍 {insert_type.value.upper()} 테스트')
        print('-' * 60)
        
        random_successes = 0
        context_successes = 0
        total_tests = len(test_cases)
        
        print(f'{"GT Text":<30} {"Expected":<10} {"Random":<10} {"Context":<10} {"Winner":<10}')
        print('-' * 80)
        
        for test_case in test_cases:
            gt = test_case["gt"]
            expected_pos = test_case["expected_insert_pos"]
            context_info = test_case["context"]
            
            # Random 삽입 테스트
            random_result, random_context, random_score, random_pos = random_inserter.random_insert_by_type(gt, insert_type)
            random_consistent, random_reason = validator.is_event_consistent(gt, random_result, expected_pos, insert_type)
            if random_consistent:
                random_successes += 1
            
            # Context-aware 삽입 테스트  
            context_result, context_context, context_score, context_pos = context_inserter.context_aware_insert_by_type(gt, insert_type)
            context_consistent, context_reason = validator.is_event_consistent(gt, context_result, expected_pos, insert_type)
            if context_consistent:
                context_successes += 1
            
            # 승자 결정
            winner = "Context" if context_consistent and not random_consistent else \
                    "Random" if random_consistent and not context_consistent else \
                    "Tie" if context_consistent and random_consistent else "Both Fail"
            
            # 결과 출력
            expected_display = f"pos:{expected_pos}"
            print(f'{gt[:28]:<30} {expected_display:<10} {str(random_consistent):<10} {str(context_consistent):<10} {winner:<10}')
        
        # Subtype별 통계
        random_rate = (random_successes / total_tests) * 100
        context_rate = (context_successes / total_tests) * 100
        improvement = context_rate - random_rate
        
        print(f'\n📊 {insert_type.value} 결과:')
        print(f'  Random 성공률:      {random_successes}/{total_tests} = {random_rate:.1f}%')
        print(f'  Context-aware 성공률: {context_successes}/{total_tests} = {context_rate:.1f}%')
        print(f'  개선 정도:          {improvement:+.1f}%p')
        
        if context_rate > random_rate:
            multiplier = context_rate / max(random_rate, 1)
            print(f'  성공률 배수:        {multiplier:.1f}배 ✅')
        elif context_rate < random_rate:
            print(f'  Context-aware 우위 없음 ❌')
        else:
            print(f'  동등한 성능 🤝')

    print('\n=== 종합 결론 ===')
    print('Event-consistent 기준으로 Subtype별 성능:')
    print('1. SENTENCE_FINAL: Random vs Context-aware')
    print('2. ABBREVIATION: Random vs Context-aware') 
    print('3. INITIAL: Random vs Context-aware')
    print('\n각 Subtype별로 최적 접근법 확인 완료!')

if __name__ == "__main__":
    run_subtype_experiment()