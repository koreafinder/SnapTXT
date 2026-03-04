from expanded_comma_experiment import ExpandedStatisticalExperiment, CommaInsertType, expanded_gt_comma_subtypes

# Test just ONE case from the expanded experiment to debug step by step
experiment = ExpandedStatisticalExperiment()

# Take first CLAUSE_BOUNDARY test case
test_case = expanded_gt_comma_subtypes[CommaInsertType.CLAUSE_BOUNDARY][0]
gt = test_case["gt"]
expected_pos = test_case["expected_insert_pos"]
insert_type = CommaInsertType.CLAUSE_BOUNDARY

print("=== Single Test Case Debug ===")
print(f"GT: '{gt}'")
print(f"Expected pos: {expected_pos}")
print(f"Insert type: {insert_type}")

print(f"\n--- Context-aware Test ---")
context_result, context_context, _, context_pos = experiment.context_inserter.context_aware_insert_by_type(gt, insert_type)
print(f"Result: '{context_result}'")
print(f"Context: {context_context}")
print(f"Position: {context_pos}")

print(f"\n--- Validation ---")
context_consistent, context_reason = experiment.validator.is_event_consistent(gt, context_result, expected_pos, insert_type)
print(f"Is consistent: {context_consistent}")
print(f"Reason: {context_reason}")

if context_consistent:
    print("✅ SUCCESS - should increment context_successes")
else:
    print("❌ FAILURE - analyzing failure...")
    fail_reason = experiment.fail_analyzer.analyze_failure(gt, context_result, expected_pos, insert_type, context_context)
    print(f"Fail reason: {fail_reason}")
    print(f"Original == Result? {gt == context_result}")
    
print(f"\n--- Double Check Manual Validation ---")
if context_result == gt:
    print("NO_CHANGE: True (no comma inserted)")
else:
    print(f"NO_CHANGE: False (comma inserted)")
    print(f"Expected comma at pos {expected_pos}, actual comma at pos {context_pos}")
    if context_pos == expected_pos and ',' in context_result:
        print("Should be SUCCESS!")
    else:
        print("Position/format mismatch")