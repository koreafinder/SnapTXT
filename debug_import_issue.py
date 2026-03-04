"""
Clean test to isolate the problem
"""
# Test 1: Direct import and test
print("=== Test 1: Direct Import ===")
from comma_subtype_experiment import CommaContextInserter, CommaInsertType

inserter = CommaContextInserter()
gt = '이것은 중요하다 그리고 필요하다'
insert_type = CommaInsertType.CLAUSE_BOUNDARY

result1 = inserter.context_aware_insert_by_type(gt, insert_type)
print(f"Direct: {result1}")

# Test 2: Import through expanded experiment
print("\n=== Test 2: Through Expanded Experiment ===")
from expanded_comma_experiment import ExpandedStatisticalExperiment

experiment = ExpandedStatisticalExperiment()
result2 = experiment.context_inserter.context_aware_insert_by_type(gt, insert_type)
print(f"Expanded: {result2}")

# Test 3: Check if they're the same object
print("\n=== Test 3: Object Comparison ===")
print(f"Same class? {type(inserter) == type(experiment.context_inserter)}")
print(f"Direct inserter: {inserter}")
print(f"Expanded inserter: {experiment.context_inserter}")

# Test 4: Check method attributes
print("\n=== Test 4: Method Check ===")
print(f"Direct method: {inserter.context_aware_insert_by_type}")
print(f"Expanded method: {experiment.context_inserter.context_aware_insert_by_type}")