from expanded_comma_experiment import CommaInsertType as ExpandedCommaInsertType
from comma_subtype_experiment import CommaInsertType as OriginalCommaInsertType

print("=== Enum Comparison ===")
print(f"Expanded CLAUSE_BOUNDARY: {ExpandedCommaInsertType.CLAUSE_BOUNDARY}")
print(f"Original CLAUSE_BOUNDARY: {OriginalCommaInsertType.CLAUSE_BOUNDARY}")
print(f"Are they equal? {ExpandedCommaInsertType.CLAUSE_BOUNDARY == OriginalCommaInsertType.CLAUSE_BOUNDARY}")
print(f"Expanded value: {ExpandedCommaInsertType.CLAUSE_BOUNDARY.value}")
print(f"Original value: {OriginalCommaInsertType.CLAUSE_BOUNDARY.value}")

print(f"\n=== Test with Original Enum ===")
from comma_subtype_experiment import CommaContextInserter
inserter = CommaContextInserter()
gt = '이것은 중요하다 그리고 필요하다'

# Test with original enum
result_orig = inserter.context_aware_insert_by_type(gt, OriginalCommaInsertType.CLAUSE_BOUNDARY)
print(f"Using original enum: {result_orig}")

# Test with expanded enum  
result_exp = inserter.context_aware_insert_by_type(gt, ExpandedCommaInsertType.CLAUSE_BOUNDARY)
print(f"Using expanded enum: {result_exp}")

print(f"\n=== Enum Details ===")
print(f"Original enum type: {type(OriginalCommaInsertType.CLAUSE_BOUNDARY)}")
print(f"Expanded enum type: {type(ExpandedCommaInsertType.CLAUSE_BOUNDARY)}")
print(f"Original enum class: {OriginalCommaInsertType}")
print(f"Expanded enum class: {ExpandedCommaInsertType}")