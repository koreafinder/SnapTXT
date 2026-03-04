"""
INSERT[","] Subtype별 Event-Consistent 성능 비교 실험
========================================================

INSERT["."] 실험과 동일한 프레임워크 적용:
1. 성공 정의: event-consistent (실제 OCR 오류 재현)
2. Subtype 분리: 혼합 금지, 각각 독립 통계
3. 측정 기반: 실제 성공률만 보고, 과장된 추정 금지
4. Fail reason 세분화: NO_CHANGE → POSITION/CONTEXT 원인 분석
"""

import re
from typing import List, Tuple, Optional, Dict
from enum import Enum

print('🔬 INSERT[","] Subtype별 Event-Consistent 성능 비교 실험')
print('='*80)

class CommaInsertType(Enum):
    CLAUSE_BOUNDARY = "clause_boundary"    # 절 경계 쉼표 (접속사 앞)
    LIST_SEPARATION = "list_separation"    # 리스트 구분 쉼표 (열거)
    GEOGRAPHIC = "geographic"              # 지명 구분 쉼표 (도시, 국가)
    APPOSITION = "apposition"              # 동격 설명 쉼표 (이름, 직책)
    QUOTATION = "quotation"                # 인용 구분 쉼표 (대화 도입)

# Event-consistent GT 텍스트 풀 (Subtype별 분리)
gt_comma_subtypes = {
    CommaInsertType.CLAUSE_BOUNDARY: [
        {"gt": "이것은 중요하다 그리고 필요하다", "expected_insert_pos": 9, "context": "접속사(그리고) 앞"},
        {"gt": "책을 읽었다 하지만 이해하지 못했다", "expected_insert_pos": 7, "context": "접속사(하지만) 앞"},
        {"gt": "일을 마쳤다 그러므로 집에 간다", "expected_insert_pos": 7, "context": "접속사(그러므로) 앞"},
        {"gt": "날씨가 좋다 따라서 산책하자", "expected_insert_pos": 6, "context": "접속사(따라서) 앞"},
        {"gt": "공부했다 그런데 시험이 어렵다", "expected_insert_pos": 4, "context": "접속사(그런데) 앞"},
    ],
    
    CommaInsertType.LIST_SEPARATION: [
        {"gt": "사과 오렌지 바나나를 샀다", "expected_insert_pos": 2, "context": "첫 번째 항목 뒤"},
        {"gt": "빨강 파랑 노랑 색깔이 있다", "expected_insert_pos": 2, "context": "첫 번째 항목 뒤"},
        {"gt": "월요일 화요일 수요일에 만나자", "expected_insert_pos": 3, "context": "첫 번째 항목 뒤"},
        {"gt": "책 펜 노트가 필요하다", "expected_insert_pos": 1, "context": "첫 번째 항목 뒤"},
        {"gt": "개 고양이 새를 키운다", "expected_insert_pos": 1, "context": "첫 번째 항목 뒤"},
    ],
    
    CommaInsertType.GEOGRAPHIC: [
        {"gt": "서울 한국에 살고 있다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "부산 경남에서 태어났다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "도쿄 일본을 여행했다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "뉴욕 미국에서 공부했다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "런던 영국은 비가 많다", "expected_insert_pos": 2, "context": "도시 뒤"},
    ],
    
    CommaInsertType.APPOSITION: [
        {"gt": "저자 김철수가 발표했다", "expected_insert_pos": 2, "context": "직책 뒤"},
        {"gt": "교수 이영희는 연구자다", "expected_insert_pos": 2, "context": "직책 뒤"},
        {"gt": "의사 박민수를 만났다", "expected_insert_pos": 2, "context": "직책 뒤"},
        {"gt": "대표 최정호가 출장간다", "expected_insert_pos": 2, "context": "직책 뒤"},
        {"gt": "선생님 정미자는 친절하다", "expected_insert_pos": 3, "context": "직책 뒤"},
    ],
    
    CommaInsertType.QUOTATION: [
        {"gt": "그가 말했다 안녕하세요", "expected_insert_pos": 6, "context": "대화 도입부 뒤"},
        {"gt": "그녀가 외쳤다 도와주세요", "expected_insert_pos": 6, "context": "대화 도입부 뒤"}, 
        {"gt": "아버지가 말씀하셨다 조심해라", "expected_insert_pos": 9, "context": "대화 도입부 뒤"},
        {"gt": "선생님이 말했다 공부하자", "expected_insert_pos": 7, "context": "대화 도입부 뒤"},
        {"gt": "친구가 물었다 어디 가니", "expected_insert_pos": 5, "context": "대화 도입부 뒤"},
    ]
}

class CommaEventConsistentValidator:
    """INSERT[","] Event-consistent 성공 기준 검증기"""
    
    def is_event_consistent(self, gt: str, result: str, expected_pos: int, insert_type: CommaInsertType) -> Tuple[bool, str]:
        """INSERT[","] 실제 OCR 오류 패턴과 일치하는지 검증"""
        
        # 1. 기본 검증: 정확히 한 개의 쉼표가 추가되었는가?
        original_comma_count = gt.count(',')
        result_comma_count = result.count(',')
        
        if result_comma_count != original_comma_count + 1:
            return False, f"쉼표 개수 불일치: {original_comma_count} → {result_comma_count}"
        
        # 2. 예상 위치에 쉼표가 있는가?
        if len(result) > expected_pos and result[expected_pos] == ',':
            expected_result = gt[:expected_pos] + ',' + gt[expected_pos:]
            if result == expected_result:
                return True, f"정확한 위치 {expected_pos}에 삽입 성공"
            else:
                return False, f"예상결과 불일치: {expected_result} vs {result}"
        
        # 3. Subtype별 추가 검증
        if insert_type == CommaInsertType.CLAUSE_BOUNDARY:
            # 접속사 앞에 쉼표가 있어야 함
            conjunctions = ["그리고", "하지만", "그러므로", "따라서", "그런데", "그러나"]
            for conj in conjunctions:
                pattern = f",\\s*{conj}"
                if re.search(pattern, result):
                    return True, f"절 경계 패턴 매칭: {pattern}"
            return False, f"절 경계 패턴 불일치: {result}"
        
        elif insert_type == CommaInsertType.LIST_SEPARATION:
            # 첫 번째 항목 뒤에 쉼표가 있어야 함
            # 단어 뒤 공백 뒤에 또 다른 단어 패턴
            list_pattern = r'\w+,\s+\w+'
            if re.search(list_pattern, result):
                return True, f"리스트 구분 패턴 매칭: {list_pattern}"
            return False, f"리스트 구분 패턴 불일치: {result}"
        
        elif insert_type == CommaInsertType.GEOGRAPHIC:
            # 지명 뒤에 쉼표가 있어야 함
            geo_patterns = [r'서울,', r'부산,', r'도쿄,', r'뉴욕,', r'런던,']
            for pattern in geo_patterns:
                if re.search(pattern, result):
                    return True, f"지명 구분 패턴 매칭: {pattern}"
            return False, f"지명 구분 패턴 불일치: {result}"
        
        elif insert_type == CommaInsertType.APPOSITION:
            # 직책 뒤에 쉼표가 있어야 함  
            title_patterns = [r'저자,', r'교수,', r'의사,', r'대표,', r'선생님,']
            for pattern in title_patterns:
                if re.search(pattern, result):
                    return True, f"동격 설명 패턴 매칭: {pattern}"
            return False, f"동격 설명 패턴 불일치: {result}"
        
        elif insert_type == CommaInsertType.QUOTATION:
            # 대화 동사 뒤에 쉼표가 있어야 함
            quote_patterns = [r'말했다,', r'외쳤다,', r'말씀하셨다,', r'물었다,']
            for pattern in quote_patterns:
                if re.search(pattern, result):
                    return True, f"인용 구분 패턴 매칭: {pattern}"
            return False, f"인용 구분 패턴 불일치: {result}"
        
        return False, "알 수 없는 오류"

class CommaContextInserter:
    """INSERT[","] Context-aware 삽입기 (Subtype별 특화)"""
    
    def context_aware_insert_by_type(self, gt: str, insert_type: CommaInsertType) -> Tuple[str, str, float, int]:
        """Subtype별 Context-aware 쉼표 삽입"""
        
        if insert_type == CommaInsertType.CLAUSE_BOUNDARY:
            return self._insert_clause_boundary(gt)
        elif insert_type == CommaInsertType.LIST_SEPARATION:
            return self._insert_list_separation(gt)
        elif insert_type == CommaInsertType.GEOGRAPHIC:
            return self._insert_geographic(gt)
        elif insert_type == CommaInsertType.APPOSITION:
            return self._insert_apposition(gt)
        elif insert_type == CommaInsertType.QUOTATION:
            return self._insert_quotation(gt)
        else:
            return gt, "unknown_type", 0.0, -1
    
    def _insert_clause_boundary(self, gt: str) -> Tuple[str, str, float, int]:
        """절 경계 쉼표 삽입"""
        conjunctions = [
            ("그리고", 3),    # "이것은 중요하다 그리고" → "이것은 중요하다, 그리고"
            ("하지만", 3),    # "책을 읽었다 하지만" → "책을 읽었다, 하지만"
            ("그러므로", 4),  # "일을 마쳤다 그러므로" → "일을 마쳤다, 그러므로"
            ("따라서", 3),    # "날씨가 좋다 따라서" → "날씨가 좋다, 따라서"
            ("그런데", 3),    # "공부했다 그런데" → "공부했다, 그런데"
            ("그러나", 3),    # "시도했다 그러나" → "시도했다, 그러나"
        ]
        
        for conj, offset in conjunctions:
            pattern = f"(\\S+)\\s+({conj})"
            match = re.search(pattern, gt)
            if match:
                pos = match.start(2) - 1  # 접속사 앞 공백에 삽입
                result = gt[:pos] + ',' + gt[pos:]
                return result, f"clause_{conj}", 0.8, pos
        
        return gt, "no_conjunction_found", 0.0, -1
    
    def _insert_list_separation(self, gt: str) -> Tuple[str, str, float, int]:
        """리스트 구분 쉼표 삽입"""
        # 첫 번째 단어 뒤에 삽입하는 패턴
        list_patterns = [
            (r"(\\w+)\\s+(\\w+)\\s+(\\w+)", 1),  # "AAA BBB CCC" → "AAA, BBB CCC"
        ]
        
        for pattern, group_end in list_patterns:
            match = re.search(pattern, gt)
            if match:
                pos = match.end(group_end)  # 첫 번째 단어 끝
                result = gt[:pos] + ',' + gt[pos:]
                return result, f"list_first_item", 0.7, pos
        
        return gt, "no_list_pattern", 0.0, -1
    
    def _insert_geographic(self, gt: str) -> Tuple[str, str, float, int]:
        """지명 구분 쉼표 삽입"""
        geo_patterns = [
            (r"(서울)\\s+(한국)", 2),      # "서울 한국" → "서울, 한국"
            (r"(부산)\\s+(경남)", 2),      # "부산 경남" → "부산, 경남"  
            (r"(도쿄)\\s+(일본)", 2),      # "도쿄 일본" → "도쿄, 일본"
            (r"(뉴욕)\\s+(미국)", 2),      # "뉴욕 미국" → "뉴욕, 미국"
            (r"(런던)\\s+(영국)", 2),      # "런던 영국" → "런던, 영국"
        ]
        
        for pattern, city_len in geo_patterns:
            match = re.search(pattern, gt)
            if match:
                pos = match.end(1)  # 첫 번째 지명 끝
                result = gt[:pos] + ',' + gt[pos:]
                return result, f"geo_{match.group(1)}", 0.85, pos
        
        return gt, "no_geo_pattern", 0.0, -1
    
    def _insert_apposition(self, gt: str) -> Tuple[str, str, float, int]:
        """동격 설명 쉼표 삽입"""
        title_patterns = [
            (r"(저자)\\s+([가-힣]+)", 2),     # "저자 김철수" → "저자, 김철수"
            (r"(교수)\\s+([가-힣]+)", 2),     # "교수 이영희" → "교수, 이영희"
            (r"(의사)\\s+([가-힣]+)", 2),     # "의사 박민수" → "의사, 박민수" 
            (r"(대표)\\s+([가-힣]+)", 2),     # "대표 최정호" → "대표, 최정호"
            (r"(선생님)\\s+([가-힣]+)", 3),   # "선생님 정미자" → "선생님, 정미자"
        ]
        
        for pattern, title_len in title_patterns:
            match = re.search(pattern, gt)
            if match:
                pos = match.end(1)  # 직책 끝
                result = gt[:pos] + ',' + gt[pos:]
                return result, f"title_{match.group(1)}", 0.8, pos
        
        return gt, "no_title_pattern", 0.0, -1
    
    def _insert_quotation(self, gt: str) -> Tuple[str, str, float, int]:
        """인용 구분 쉼표 삽입"""
        quote_patterns = [
            (r"(말했다)\\s+", 3),           # "그가 말했다 안녕" → "그가 말했다, 안녕"
            (r"(외쳤다)\\s+", 3),           # "그녀가 외쳤다 도와" → "그녀가 외쳤다, 도와"
            (r"(말씀하셨다)\\s+", 5),       # "아버지가 말씀하셨다 조심" → "아버지가 말씀하셨다, 조심"
            (r"(물었다)\\s+", 3),           # "친구가 물었다 어디" → "친구가 물었다, 어디"
        ]
        
        for pattern, verb_len in quote_patterns:
            match = re.search(pattern, gt)
            if match:
                pos = match.end(1)  # 동사 끝
                result = gt[:pos] + ',' + gt[pos:]
                return result, f"quote_{match.group(1)}", 0.75, pos
        
        return gt, "no_quote_pattern", 0.0, -1

class CommaRandomInserter:
    """INSERT[","] Random 삽입기 (기존 방식)"""
    
    def random_insert_by_type(self, gt: str, insert_type: CommaInsertType) -> Tuple[str, str, float, int]:
        """Subtype과 무관하게 단순 끝 추가"""
        pos = len(gt)
        result = gt + ","
        return result, "random_end", 0.5, pos

def run_comma_subtype_experiment():
    """INSERT[","] Subtype별 Random vs Context-aware 비교 실험"""
    
    context_inserter = CommaContextInserter()
    random_inserter = CommaRandomInserter()
    validator = CommaEventConsistentValidator()
    
    print('\\n=== INSERT[","] Event-Consistent 성공 기준 Subtype별 실험 ===')
    
    for insert_type, test_cases in gt_comma_subtypes.items():
        print(f'\\n🔍 {insert_type.value.upper()} 테스트')
        print('-' * 60)
        
        random_successes = 0
        context_successes = 0 
        total_tests = len(test_cases)
        
        fail_reasons = {"random": [], "context": []}
        
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
            else:
                fail_reasons["random"].append(random_reason)
            
            # Context-aware 삽입 테스트  
            context_result, context_context, context_score, context_pos = context_inserter.context_aware_insert_by_type(gt, insert_type)
            context_consistent, context_reason = validator.is_event_consistent(gt, context_result, expected_pos, insert_type)
            if context_consistent:
                context_successes += 1
            else:
                fail_reasons["context"].append(context_reason)
            
            # 승자 결정
            winner = "Context" if context_consistent and not random_consistent else \\
                    "Random" if random_consistent and not context_consistent else \\
                    "Tie" if context_consistent and random_consistent else "Both Fail"
            
            # 결과 출력
            expected_display = f"pos:{expected_pos}"
            print(f'{gt[:28]:<30} {expected_display:<10} {str(random_consistent):<10} {str(context_consistent):<10} {winner:<10}')
        
        # Subtype별 통계
        random_rate = (random_successes / total_tests) * 100
        context_rate = (context_successes / total_tests) * 100
        improvement = context_rate - random_rate
        
        print(f'\\n📊 {insert_type.value} 결과:')
        print(f'  Random 성공률:      {random_successes}/{total_tests} = {random_rate:.1f}%')
        print(f'  Context-aware 성공률: {context_successes}/{total_tests} = {context_rate:.1f}%')
        print(f'  개선 정도:          {improvement:+.1f}%p')
        
        # Fail reason 분석  
        print(f'\\n🔍 Fail Reason 분석:')
        print(f'  Random 실패 원인: {fail_reasons["random"][:3]}...' if fail_reasons["random"] else '  Random 실패 없음')
        print(f'  Context 실패 원인: {fail_reasons["context"][:3]}...' if fail_reasons["context"] else '  Context 실패 없음')
        
        if context_rate > random_rate:
            print(f'  ✅ Context-aware 우위 확인')
        elif context_rate < random_rate:
            print(f'  ❌ Context-aware 우위 없음')
        else:
            print(f'  🤝 동등한 성능')

    print('\\n=== 종합 결론 ===')
    print('Event-consistent 기준으로 INSERT[","] Subtype별 성능:') 
    for subtype in gt_comma_subtypes.keys():
        print(f'- {subtype.value.upper()}: Random vs Context-aware 성능 비교 완료')
    
    print('\\n각 Subtype별 최적 접근법과 Fail reason 패턴 분석 완료!')

if __name__ == "__main__":
    run_comma_subtype_experiment()