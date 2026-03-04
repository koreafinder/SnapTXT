"""
INSERT["."] 패턴 Context-aware vs Random 성공률 비교 실험
=============================================================

목표: 작은 실험으로 Context-aware 가설 검증
- INSERT["."] 패턴 하나만 대상
- 간단한 context heuristic 2가지 구현
- Random vs Context-aware 직접 성공률 비교
"""

import re
import random
from typing import List, Tuple, Optional

print('🧪 INSERT["."] Context-aware vs Random 성공률 실험')
print('='*70)

# GT 텍스트 풀 (다양한 패턴 포함)
gt_text_pool = [
    "Michael A Singer wrote this book",        # 이름 사이 패턴
    "Dr Smith is a good person",               # 약어 뒤 패턴
    "This is a test sentence",                 # 문장 끝 패턴
    "Chapter 5 covers the main topic",         # 숫자 뒤 패턴
    "The author John Doe explains well",       # 이름 사이 패턴 2
    "They visited Seoul Korea yesterday",       # 지명 사이 패턴
    "Professor Kim has many students",          # 호칭 뒤 패턴
    "Year 2024 was very important",           # 연도 뒤 패턴
    "Mr Johnson worked hard today",           # 호칭 뒤 패턴
    "New York City has many buildings",       # 복합 지명 패턴
    "The CEO Mary Chen announced",            # 직책+이름 패턴
    "Version 3 includes new features",        # 버전 뒤 패턴
    "Dr Lee studied medicine for years",      # 약어 뒤 패턴 2
    "The result was very successful",         # 순수 문장 완성
    "Capital city Washington has museums"     # 지명 패턴
]

class ContextAwareInserter:
    """Context 기반 Period 삽입 실험 클래스"""
    
    def find_sentence_end_positions(self, text: str) -> List[Tuple[int, str, float]]:
        """문장 끝 패턴 탐지"""
        candidates = []
        
        # 주어+동사+목적어 완성 패턴
        sentence_patterns = [
            r'(\w+\s+\w+\s+\w+)$',  # "word word word" 끝
            r'(\w+\s+\w+\s+\w+\s+\w+)$',  # "word word word word" 끝
            r'(is\s+a\s+\w+)$',      # "is a something" 끝
            r'(has\s+\w+\s+\w+)$',   # "has something something" 끝
            r'(was\s+\w+\s+\w+)$',   # "was very something" 끝
            r'(includes\s+\w+\s+\w+)$' # "includes something something" 끝
        ]
        
        for pattern in sentence_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                position = len(text)  # 끝에 삽입
                context = f"sentence_end:{match.group(1)}"
                score = 0.8  # 문장 끝 높은 점수
                candidates.append((position, context, score))
        
        return candidates
    
    def find_name_middle_positions(self, text: str) -> List[Tuple[int, str, float]]:
        """이름 사이 패턴 탐지 (First Middle Last 구조)"""
        candidates = []
        
        # 이름 패턴들
        name_patterns = [
            r'(\b[A-Z][a-z]+\s+[A-Z]\s+[A-Z][a-z]+)',    # "Michael A Singer"
            r'(\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+)',  # "John Doe Smith"
            r'(\bDr\s+[A-Z][a-z]+)',                      # "Dr Smith" 
            r'(\bProfessor\s+[A-Z][a-z]+)',               # "Professor Kim"
            r'(\bMr\s+[A-Z][a-z]+)',                      # "Mr Johnson"
            r'(\bCEO\s+[A-Z][a-z]+\s+[A-Z][a-z]+)',      # "CEO Mary Chen"
        ]
        
        for pattern in name_patterns:
            for match in re.finditer(pattern, text):
                start_pos = match.start()
                end_pos = match.end()
                name_text = match.group(1)
                
                # Dr, Professor, Mr 등 호칭 뒤에 삽입
                if name_text.startswith(('Dr ', 'Professor ', 'Mr ')):
                    space_pos = name_text.find(' ')
                    if space_pos != -1:
                        position = start_pos + space_pos + 1  # 호칭과 이름 사이
                        context = f"title_after:{name_text[:space_pos]}"
                        score = 0.9  # 호칭 뒤 매우 높은 점수
                        candidates.append((position, context, score))
                
                # First Middle Last 구조에서 Middle 뒤에 삽입
                elif ' ' in name_text:
                    words = name_text.split()
                    if len(words) >= 2:
                        # 첫 번째 단어 뒤 (First 뒤)
                        first_word_end = start_pos + len(words[0])
                        context = f"first_name_after:{words[0]}"
                        score = 0.7
                        candidates.append((first_word_end, context, score))
                        
                        # Middle이 이니셜인 경우 (A, B 등)
                        if len(words) >= 3 and len(words[1]) == 1:
                            middle_end = first_word_end + 1 + len(words[1])
                            context = f"middle_initial_after:{words[1]}"
                            score = 0.85
                            candidates.append((middle_end, context, score))
        
        return candidates
    
    def find_number_after_positions(self, text: str) -> List[Tuple[int, str, float]]:
        """숫자 뒤 패턴 탐지"""
        candidates = []
        
        # 숫자 패턴들
        number_patterns = [
            r'(\bChapter\s+\d+)',     # "Chapter 5"
            r'(\bVersion\s+\d+)',     # "Version 3"
            r'(\bYear\s+\d{4})',      # "Year 2024"
        ]
        
        for pattern in number_patterns:
            for match in re.finditer(pattern, text):
                position = match.end()  # 숫자 뒤에 삽입
                context = f"number_after:{match.group(1)}"
                score = 0.75  # 숫자 뒤 높은 점수
                candidates.append((position, context, score))
        
        return candidates
    
    def context_aware_insert(self, gt_text: str) -> Tuple[str, str, float]:
        """Context 기반 Period 삽입"""
        candidates = []
        
        # 모든 패턴 탐지
        candidates.extend(self.find_sentence_end_positions(gt_text))
        candidates.extend(self.find_name_middle_positions(gt_text))
        candidates.extend(self.find_number_after_positions(gt_text))
        
        if not candidates:
            return gt_text, "no_suitable_position", 0.0
        
        # 점수 기준으로 최적 위치 선택
        best_candidate = max(candidates, key=lambda x: x[2])
        position, context, score = best_candidate
        
        # Period 삽입
        result = gt_text[:position] + "." + gt_text[position:]
        return result, context, score

class RandomInserter:
    """기존 Random Period 삽입 클래스"""
    
    def random_insert(self, gt_text: str) -> Tuple[str, str, float]:
        """Random 위치 Period 삽입 (기존 방식)"""
        # 기존 build_error_replay_dataset.py와 동일한 로직
        return gt_text + ".", "random_end", 0.5

def is_natural_sentence(text: str) -> bool:
    """삽입 결과가 자연스러운 문장인지 검증"""
    # 기본 문법 검증
    if text.endswith(".."):  # Double period
        return False
    if ".." in text:  # 중간에 double period
        return False
    if text.count(".") > 3:  # 너무 많은 period
        return False
    
    # 자연스러운 패턴 검증
    natural_patterns = [
        r'Dr\.',           # Dr.
        r'Mr\.',           # Mr.
        r'\b[A-Z]\.',      # Middle initial like "A."
        r'\w+\.$',         # 문장 끝
        r'Chapter\s+\d+\.', # Chapter 5.
        r'Version\s+\d+\.', # Version 3.
    ]
    
    for pattern in natural_patterns:
        if re.search(pattern, text):
            return True
    
    return False

def run_comparison_experiment():
    """Random vs Context-aware 성공률 비교 실험"""
    
    context_inserter = ContextAwareInserter()
    random_inserter = RandomInserter()
    
    print('\n=== 실험 결과 ===')
    print(f'{"GT Text":<30} {"Random":<15} {"Context-aware":<20} {"Winner":<10}')
    print('-' * 80)
    
    random_successes = 0
    context_successes = 0
    total_tests = len(gt_text_pool)
    
    detailed_results = []
    
    for i, gt_text in enumerate(gt_text_pool, 1):
        # Random insertion 테스트  
        random_result, random_context, random_score = random_inserter.random_insert(gt_text)
        random_natural = is_natural_sentence(random_result)
        if random_natural:
            random_successes += 1
        
        # Context-aware insertion 테스트
        context_result, context_context, context_score = context_inserter.context_aware_insert(gt_text)
        context_natural = is_natural_sentence(context_result)
        if context_natural:
            context_successes += 1
        
        # 승자 결정
        winner = "Context" if context_natural and not random_natural else \
                "Random" if random_natural and not context_natural else \
                "Tie" if context_natural and random_natural else "Both Fail"
        
        # 결과 출력
        print(f'{gt_text[:28]:<30} {str(random_natural):<15} {str(context_natural):<20} {winner:<10}')
        
        # 상세 결과 저장
        detailed_results.append({
            'gt_text': gt_text,
            'random_result': random_result,
            'random_natural': random_natural,
            'context_result': context_result,
            'context_context': context_context,
            'context_score': context_score,
            'context_natural': context_natural,
            'winner': winner
        })
    
    # 통계 결과
    print('\n=== 통계 결과 ===')
    random_rate = (random_successes / total_tests) * 100
    context_rate = (context_successes / total_tests) * 100
    improvement = context_rate - random_rate
    
    print(f'Random insertion 성공률:      {random_successes}/{total_tests} = {random_rate:.1f}%')
    print(f'Context-aware 성공률:         {context_successes}/{total_tests} = {context_rate:.1f}%')
    print(f'개선 정도:                   +{improvement:.1f}%p')
    
    if context_successes > random_successes:
        multiplier = context_rate / max(random_rate, 1)
        print(f'성공률 배수:                 {multiplier:.1f}배')
    
    # 상세 분석
    print('\n=== Context-aware 성공 사례 분석 ===')
    for result in detailed_results:
        if result['context_natural'] and not result['random_natural']:
            print(f'GT: {result["gt_text"]}')
            print(f'  Random:  {result["random_result"]} ❌')
            print(f'  Context: {result["context_result"]} ✅ ({result["context_context"]}, score:{result["context_score"]:.2f})')
            print()
    
    print('\n=== 가설 검증 결과 ===')
    if context_rate > random_rate:
        print('✅ Context-aware 접근법이 Random 접근법보다 우수함 확인!')
        print('✅ "삽입 위치를 안다"는 것이 성공률 향상에 실제 기여함')
        print('✅ 다음 단계: INSERT[","], INSERT["\'"] 등으로 확장 가능')
    else:
        print('❌ Context-aware 접근법이 예상만큼 우수하지 않음')
        print('❌ 휴리스틱 개선 또는 다른 접근법 필요')
    
    return random_rate, context_rate, improvement

if __name__ == "__main__":
    run_comparison_experiment()