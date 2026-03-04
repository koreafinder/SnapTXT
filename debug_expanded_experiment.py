from expanded_comma_experiment import ExpandedStatisticalExperiment, CommaInsertType

experiment = ExpandedStatisticalExperiment()
print('Context inserter type:', type(experiment.context_inserter))
print('Random inserter type:', type(experiment.random_inserter)) 
print('Validator type:', type(experiment.validator))
print('Fail analyzer type:', type(experiment.fail_analyzer))

# Test one case manually from the expanded data
gt = '이것은 중요하다 그리고 필요하다'
expected_pos = 8
insert_type = CommaInsertType.CLAUSE_BOUNDARY

print('\n=== Manual Test with Expanded Experiment Classes ===')
context_result, context_context, _, context_pos = experiment.context_inserter.context_aware_insert_by_type(gt, insert_type)
print(f'Context inserter: "{context_result}" at pos {context_pos}')

context_consistent, context_reason = experiment.validator.is_event_consistent(gt, context_result, expected_pos, insert_type)
print(f'Consistency check: {context_consistent}, reason: {context_reason}')

if context_consistent:
    print('✅ Should be SUCCESS!')
else:
    fail_reason = experiment.fail_analyzer.analyze_failure(gt, context_result, expected_pos, insert_type, context_context)
    print(f'❌ Fail reason: {fail_reason}')
    print(f'❌ Original == Result? {gt == context_result}')