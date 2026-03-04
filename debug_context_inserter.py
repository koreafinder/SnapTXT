from comma_subtype_experiment import CommaContextInserter, CommaInsertType, CommaEventConsistentValidator  
from expanded_comma_experiment import EnhancedFailReasonAnalyzer, FailReasonCategory

inserter = CommaContextInserter()
validator = CommaEventConsistentValidator()
analyzer = EnhancedFailReasonAnalyzer()

gt = '이것은 중요하다 그리고 필요하다'
expected_pos = 8
insert_type = CommaInsertType.CLAUSE_BOUNDARY

print("=== Context Inserter Debug ===")
result, context, confidence, pos = inserter.context_aware_insert_by_type(gt, insert_type)
print(f'Original: "{gt}"')
print(f'Result: "{result}"')
print(f'Position: {pos}, Context: {context}')

print("\n=== Validator Debug ===")
is_consistent, reason = validator.is_event_consistent(gt, result, expected_pos, insert_type)
print(f'Validator: {is_consistent}, reason: "{reason}"')

print("\n=== Manual Check ===")
if gt == result:
    print('NO_CHANGE: True (원문과 결과가 동일)')
    fail_reason = analyzer.analyze_failure(gt, result, expected_pos, insert_type, context)
    print(f'Fail reason: {fail_reason}')
else:
    print('NO_CHANGE: False (쉼표가 삽입됨)')
    print(f'Expected position: {expected_pos}, Actual position: {pos}')
    if pos == expected_pos:
        print('Position MATCH - Should be SUCCESS!')
    else:
        print('Position MISMATCH - Position Error')