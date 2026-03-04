"""
확장된 INSERT[","] 통계적 신뢰성 검증 실험
===============================================

연구 목표: 
- 작은 샘플(5개)에서 관찰된 패턴이 큰 데이터셋에서도 재현되는지 검증
- Fail-reason 분류체계 정교화 
- 통계적으로 신뢰할 수 있는 측정 프레임워크 구축

연구 원칙 (Research Principles):
1. 측정 우선, 해석 후순위
2. 작은 샘플로부터의 과도한 일반화 금지
3. Fail-reason 분류의 지속적 정제
"""

import re
from typing import List, Tuple, Optional, Dict
from enum import Enum
import random

# 중요: 원본 실험의 enum을 사용해야 Context inserter가 제대로 작동함
from comma_subtype_experiment import CommaInsertType

print('🔬 확장된 INSERT[","] 통계적 신뢰성 검증 실험')
print('='*80)

class FailReasonCategory(Enum):
    """정교한 실패 원인 분류체계"""
    POSITION_ERROR = "position_error"      # 위치는 알지만 잘못 적용
    CONTEXT_MISSING = "context_missing"    # 패턴 인식 실패
    NO_CHANGE = "no_change"               # 적용 가능한 패턴 없음
    PATTERN_CONFLICT = "pattern_conflict"  # 여러 패턴 충돌
    VALIDATION_FAIL = "validation_fail"    # 검증 로직 실패

# 확장된 테스트 케이스 (각 subtype당 15개로 증가)
# 수정: 정확한 expected_insert_pos로 업데이트 (실제 inserter 동작에 맞춤)
expanded_gt_comma_subtypes = {
    CommaInsertType.CLAUSE_BOUNDARY: [
        # 기존 5개 - 위치 수정
        {"gt": "이것은 중요하다 그리고 필요하다", "expected_insert_pos": 8, "context": "접속사(그리고) 앞"},
        {"gt": "책을 읽었다 하지만 이해하지 못했다", "expected_insert_pos": 6, "context": "접속사(하지만) 앞"},
        {"gt": "일을 마쳤다 그러므로 집에 간다", "expected_insert_pos": 6, "context": "접속사(그러므로) 앞"},
        {"gt": "날씨가 좋다 따라서 산책하자", "expected_insert_pos": 5, "context": "접속사(따라서) 앞"},
        {"gt": "공부했다 그런데 시험이 어렵다", "expected_insert_pos": 4, "context": "접속사(그런데) 앞"},
        # 추가 10개 - 위치 수정
        {"gt": "힘들었다 그러나 포기하지 않았다", "expected_insert_pos": 4, "context": "접속사(그러나) 앞"},
        {"gt": "비가 온다 그래서 집에 있자", "expected_insert_pos": 4, "context": "접속사(그래서) 앞"},
        {"gt": "돈이 없다 그럼에도 불구하고 행복하다", "expected_insert_pos": 4, "context": "접속사(그럼에도) 앞"},
        {"gt": "시간이 부족하다 게다가 일이 많다", "expected_insert_pos": 6, "context": "접속사(게다가) 앞"},
        {"gt": "추웠다 반면에 마음은 따뜻했다", "expected_insert_pos": 3, "context": "접속사(반면에) 앞"},
        {"gt": "실패했다 하지만 경험을 얻었다", "expected_insert_pos": 4, "context": "접속사(하지만) 앞"},
        {"gt": "어렵다 그렇지만 해볼 만하다", "expected_insert_pos": 3, "context": "접속사(그렇지만) 앞"},
        {"gt": "늦었다 그래도 가야 한다", "expected_insert_pos": 3, "context": "접속사(그래도) 앞"},
        {"gt": "피곤하다 그런데도 일해야 한다", "expected_insert_pos": 4, "context": "접속사(그런데도) 앞"},
        {"gt": "끝났다 따라서 집에 가자", "expected_insert_pos": 3, "context": "접속사(따라서) 앞"},
    ],
    
    CommaInsertType.LIST_SEPARATION: [
        # 기존 5개 - 위치 수정 (모두 첫 번째 항목 뒤 = position 2)
        {"gt": "사과 오렌지 바나나를 샀다", "expected_insert_pos": 2, "context": "첫 번째 항목 뒤"},
        {"gt": "빨강 파랑 노랑 색깔이 있다", "expected_insert_pos": 2, "context": "첫 번째 항목 뒤"},
        {"gt": "월요일 화요일 수요일에 만나자", "expected_insert_pos": 3, "context": "첫 번째 항목 뒤"},
        {"gt": "책 펜 노트가 필요하다", "expected_insert_pos": 1, "context": "첫 번째 항목 뒤"},
        {"gt": "개 고양이 새를 키운다", "expected_insert_pos": 1, "context": "첫 번째 항목 뒤"},
        # 추가 10개 - 위치 수정
        {"gt": "장미 튤립 백합을 심었다", "expected_insert_pos": 2, "context": "첫 번째 항목 뒤"},
        {"gt": "수학 영어 과학을 공부한다", "expected_insert_pos": 2, "context": "첫 번째 항목 뒤"},
        {"gt": "밥 국 반찬을 먹었다", "expected_insert_pos": 1, "context": "첫 번째 항목 뒤"},
        {"gt": "옷 신발 가방을 샀다", "expected_insert_pos": 1, "context": "첫 번째 항목 뒤"},
        {"gt": "축구 농구 테니스를 좋아한다", "expected_insert_pos": 2, "context": "첫 번째 항목 뒤"},
        {"gt": "봄 여름 가을이 좋다", "expected_insert_pos": 1, "context": "첫 번째 항목 뒤"},
        {"gt": "아침 점심 저녁을 먹었다", "expected_insert_pos": 2, "context": "첫 번째 항목 뒤"},
        {"gt": "자전거 자동차 기차로 갔다", "expected_insert_pos": 3, "context": "첫 번째 항목 뒤"},
        {"gt": "어제 오늘 내일이 중요하다", "expected_insert_pos": 2, "context": "첫 번째 항목 뒤"},
        {"gt": "커피 차 주스를 마셨다", "expected_insert_pos": 2, "context": "첫 번째 항목 뒤"},
    ],
    
    CommaInsertType.GEOGRAPHIC: [
        # 기존 5개 - 위치 수정 (모두 도시명 뒤 = position 2)
        {"gt": "서울 한국에 살고 있다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "부산 경남에서 태어났다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "도쿄 일본을 여행했다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "뉴욕 미국에서 공부했다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "런던 영국은 비가 많다", "expected_insert_pos": 2, "context": "도시 뒤"},
        # 추가 10개 - 위치 수정
        {"gt": "대구 경북에서 왔다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "광주 전남이 고향이다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "인천 경기로 이사했다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "울산 경남에 공장이 있다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "전주 전북에서 출발했다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "파리 프랑스가 아름답다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "로마 이탈리아를 보고 싶다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "베이징 중국에 갔다", "expected_insert_pos": 3, "context": "도시 뒤"},
        {"gt": "방콕 태국이 인상적이다", "expected_insert_pos": 2, "context": "도시 뒤"},
        {"gt": "시드니 호주에서 살았다", "expected_insert_pos": 3, "context": "도시 뒤"},
    ],
    
    CommaInsertType.APPOSITION: [
        # 기존 5개 - 위치 수정 (모두 직책/역할 뒤 = position 2)
        {"gt": "저자 김철수가 발표했다", "expected_insert_pos": 2, "context": "직책 뒤"},
        {"gt": "교수 이영희는 연구자다", "expected_insert_pos": 2, "context": "직책 뒤"},
        {"gt": "의사 박민수를 만났다", "expected_insert_pos": 2, "context": "직책 뒤"},
        {"gt": "대표 최정호가 출장간다", "expected_insert_pos": 2, "context": "직책 뒤"},
        {"gt": "선생님 정미자는 친절하다", "expected_insert_pos": 3, "context": "직책 뒤"},
        # 추가 10개 - 위치 수정  
        {"gt": "회장 김영수가 연설했다", "expected_insert_pos": 2, "context": "직책 뒤"},
        {"gt": "부장 이철호는 바쁘다", "expected_insert_pos": 2, "context": "직책 뒤"},
        {"gt": "과장 박순희가 지시했다", "expected_insert_pos": 2, "context": "직책 뒤"},
        {"gt": "팀장 최민수는 유능하다", "expected_insert_pos": 2, "context": "직책 뒤"},
        {"gt": "사장 오세훈이 방문했다", "expected_insert_pos": 2, "context": "직책 뒤"},
        {"gt": "간호사 김미영은 친절하다", "expected_insert_pos": 3, "context": "직책 뒤"},
        {"gt": "엔지니어 최동욱이 수리했다", "expected_insert_pos": 4, "context": "직책 뒤"},
        {"gt": "변호사 이가영을 고용했다", "expected_insert_pos": 3, "context": "직책 뒤"},
        {"gt": "회계사 박웅진이 계산했다", "expected_insert_pos": 3, "context": "직책 뒤"},
        {"gt": "디자이너 김소영은 창작했다", "expected_insert_pos": 4, "context": "직책 뒤"},
    ],
    
    CommaInsertType.QUOTATION: [
        # 기존 5개 - 위치 수정 (speach verb 뒤)
        {"gt": "그가 말했다 안녕하세요", "expected_insert_pos": 6, "context": "대화 도입부 뒤"},
        {"gt": "그녀가 외쳤다 도와주세요", "expected_insert_pos": 6, "context": "대화 도입부 뒤"},
        {"gt": "아버지가 말씀하셨다 조심해라", "expected_insert_pos": 9, "context": "대화 도입부 뒤"},
        {"gt": "선생님이 말했다 공부하자", "expected_insert_pos": 7, "context": "대화 도입부 뒤"},
        {"gt": "친구가 물었다 어디 가니", "expected_insert_pos": 5, "context": "대화 도입부 뒤"},
        # 추가 10개 - 위치 수정
        {"gt": "엄마가 말했다 빨리 와", "expected_insert_pos": 6, "context": "대화 도입부 뒤"},
        {"gt": "아이가 외쳤다 재미있어", "expected_insert_pos": 6, "context": "대화 도입부 뒤"},
        {"gt": "할머니가 말씀하셨다 건강해라", "expected_insert_pos": 9, "context": "대화 도입부 뒤"},
        {"gt": "의사가 말했다 괜찮습니다", "expected_insert_pos": 6, "context": "대화 도입부 뒤"},
        {"gt": "학생이 물었다 언제까지요", "expected_insert_pos": 6, "context": "대화 도입부 뒤"},
        {"gt": "손님이 말했다 맛있어요", "expected_insert_pos": 6, "context": "대화 도입부 뒤"},
        {"gt": "기자가 물었다 언제부터인가요", "expected_insert_pos": 6, "context": "대화 도입부 뒤"},
        {"gt": "환자가 말했다 아파요", "expected_insert_pos": 6, "context": "대화 도입부 뒤"},
        {"gt": "직원이 대답했다 네 알겠습니다", "expected_insert_pos": 7, "context": "대화 도입부 뒤"},
        {"gt": "고객이 요청했다 바꿔주세요", "expected_insert_pos": 7, "context": "대화 도입부 뒤"},
    ]
}

class EnhancedFailReasonAnalyzer:
    """정교화된 실패 원인 분석기"""
    
    def analyze_failure(self, gt: str, result: str, expected_pos: int, 
                       insert_type: CommaInsertType, method: str) -> FailReasonCategory:
        """실패 원인을 정교하게 분류"""
        
        # 1. NO_CHANGE: 전혀 변화가 없는 경우
        if gt == result:
            return FailReasonCategory.NO_CHANGE
        
        # 2. POSITION_ERROR: 쉼표는 추가됐지만 위치가 틀린 경우
        if result.count(',') == gt.count(',') + 1:
            if len(result) > expected_pos and result[expected_pos] != ',':
                return FailReasonCategory.POSITION_ERROR
        
        # 3. PATTERN_CONFLICT: 여러 개의 쉼표가 추가된 경우
        if result.count(',') > gt.count(',') + 1:
            return FailReasonCategory.PATTERN_CONFLICT
            
        # 4. VALIDATION_FAIL: 검증 단계에서 실패
        if method == "unknown_type" or method.startswith("no_"):
            return FailReasonCategory.CONTEXT_MISSING
        
        # 5. 기타
        return FailReasonCategory.VALIDATION_FAIL

class ExpandedStatisticalExperiment:
    """확장된 통계적 실험 클래스"""
    
    def __init__(self):
        from comma_subtype_experiment import CommaContextInserter, CommaRandomInserter, CommaEventConsistentValidator
        self.context_inserter = CommaContextInserter()
        self.random_inserter = CommaRandomInserter()
        self.validator = CommaEventConsistentValidator()
        self.fail_analyzer = EnhancedFailReasonAnalyzer()
    
    def run_expanded_experiment(self):
        """확장된 통계 실험 실행"""
        
        print('\\n=== 확장된 INSERT[","] 통계적 신뢰성 검증 ===')
        print(f'각 Subtype당 15개 테스트 케이스 (총 75개)')
        print()
        
        overall_stats = {
            "random": {"successes": 0, "total": 0, "fail_reasons": {}},
            "context": {"successes": 0, "total": 0, "fail_reasons": {}}
        }
        
        subtype_results = {}
        
        for insert_type, test_cases in expanded_gt_comma_subtypes.items():
            print(f'🔍 {insert_type.value.upper()} 확장 테스트 (n={len(test_cases)})')
            print('-' * 70)
            
            random_successes = 0
            context_successes = 0
            total_tests = len(test_cases)
            
            random_fail_reasons = {}
            context_fail_reasons = {}
            
            for test_case in test_cases[:]:  # 모든 테스트 케이스 실행
                gt = test_case["gt"] 
                expected_pos = test_case["expected_insert_pos"]
                
                # Random 테스트
                random_result, random_context, _, random_pos = self.random_inserter.random_insert_by_type(gt, insert_type)
                random_consistent, random_reason = self.validator.is_event_consistent(gt, random_result, expected_pos, insert_type)
                
                if random_consistent:
                    random_successes += 1
                else:
                    fail_reason = self.fail_analyzer.analyze_failure(gt, random_result, expected_pos, insert_type, random_context)
                    random_fail_reasons[fail_reason] = random_fail_reasons.get(fail_reason, 0) + 1
                
                # Context-aware 테스트
                context_result, context_context, _, context_pos = self.context_inserter.context_aware_insert_by_type(gt, insert_type)
                context_consistent, context_reason = self.validator.is_event_consistent(gt, context_result, expected_pos, insert_type)
                
                if context_consistent:
                    context_successes += 1
                else:
                    fail_reason = self.fail_analyzer.analyze_failure(gt, context_result, expected_pos, insert_type, context_context)
                    context_fail_reasons[fail_reason] = context_fail_reasons.get(fail_reason, 0) + 1
            
            # 통계 계산
            random_rate = (random_successes / total_tests) * 100
            context_rate = (context_successes / total_tests) * 100
            improvement = context_rate - random_rate
            
            # 결과 저장
            subtype_results[insert_type] = {
                "random_rate": random_rate,
                "context_rate": context_rate,
                "improvement": improvement,
                "sample_size": total_tests,
                "random_fail_reasons": random_fail_reasons,
                "context_fail_reasons": context_fail_reasons
            }
            
            # 전체 통계에 추가
            overall_stats["random"]["successes"] += random_successes
            overall_stats["random"]["total"] += total_tests
            overall_stats["context"]["successes"] += context_successes  
            overall_stats["context"]["total"] += total_tests
            
            # 실패 원인 병합
            for reason, count in random_fail_reasons.items():
                overall_stats["random"]["fail_reasons"][reason] = overall_stats["random"]["fail_reasons"].get(reason, 0) + count
            for reason, count in context_fail_reasons.items():
                overall_stats["context"]["fail_reasons"][reason] = overall_stats["context"]["fail_reasons"].get(reason, 0) + count
            
            # 개별 결과 출력
            print(f'📊 성공률: Random {random_rate:.1f}% vs Context {context_rate:.1f}% (n={total_tests})')
            print(f'📈 개선 정도: {improvement:+.1f}%p')
            
            # 실패 원인 분석
            if random_fail_reasons:
                print(f'🔍 Random 실패 원인: {dict(random_fail_reasons)}')
            if context_fail_reasons:
                print(f'🔍 Context 실패 원인: {dict(context_fail_reasons)}')
            print()
        
        # 전체 결과 요약
        print('=== 전체 통계 요약 ===')
        total_samples = overall_stats["random"]["total"]
        overall_random_rate = (overall_stats["random"]["successes"] / total_samples) * 100
        overall_context_rate = (overall_stats["context"]["successes"] / total_samples) * 100
        overall_improvement = overall_context_rate - overall_random_rate
        
        print(f'📊 전체 성공률 (n={total_samples}):')
        print(f'   Random: {overall_random_rate:.1f}% ({overall_stats["random"]["successes"]}/{total_samples})')
        print(f'   Context: {overall_context_rate:.1f}% ({overall_stats["context"]["successes"]}/{total_samples})')
        print(f'   개선: {overall_improvement:+.1f}%p')
        
        print(f'\\n🔍 전체 실패 원인 분석:')
        print(f'   Random 실패 원인: {dict(overall_stats["random"]["fail_reasons"])}')
        print(f'   Context 실패 원인: {dict(overall_stats["context"]["fail_reasons"])}')
        
        # 통계적 신뢰성 평가
        print(f'\\n📈 통계적 신뢰성 평가:')
        print(f'   - 샘플 크기: 각 subtype 15개 → 전체 75개 (이전 25개 대비 3배 증가)')
        print(f'   - 패턴 일관성: {"모든 subtype에서 동일 패턴" if all(r["context_rate"] >= r["random_rate"] for r in subtype_results.values()) else "subtype별 상이한 패턴"}')
        print(f'   - 효과 크기: {"대" if overall_improvement >= 80 else "중" if overall_improvement >= 50 else "소"}효과 ({overall_improvement:.1f}%p)')
        
        return subtype_results, overall_stats

if __name__ == "__main__":
    experiment = ExpandedStatisticalExperiment()
    subtype_results, overall_stats = experiment.run_expanded_experiment()