#!/usr/bin/env python3
"""Debug Scope Guard"""

from snaptxt.postprocess.patterns.stage_scope_guard import *

# Debug wrapper function
def debug_should_apply_rule(stage: str, pattern: str, replacement: str, metadata):
    scope_key = generate_scope_key(pattern, replacement)
    phenomenon = classify_phenomenon(pattern, replacement)
    policy = get_scope_policy(phenomenon, stage)
    
    print(f"Debug info:")
    print(f"  Stage: {stage}")
    print(f"  Pattern: {pattern}")
    print(f"  Replacement: {replacement}")
    print(f"  Phenomenon: {phenomenon}")
    print(f"  Policy: {policy}")
    print(f"  Scope key: {scope_key}")
    print(f"  Already applied: {scope_key in metadata.applied_scope_keys}")
    print(f"  Expected policy match: {stage.lower()}_only = {((stage.lower()) + '_only')}")
    
    return should_apply_rule(stage, pattern, replacement, metadata)

# Test
from snaptxt.postprocess.patterns.stage_scope_guard import StageMetadata

global_metadata = StageMetadata()

print("=== Debug Test 1: Stage2 broken_jamo ===")
result1 = debug_should_apply_rule('S2', 'ㅏ', '아', global_metadata)
print(f"Result: {result1}")

print("\n=== Debug Test 2: Stage3 ending_normalization ===")  
result2 = debug_should_apply_rule('S3', '습니다', '합니다', global_metadata)
print(f"Result: {result2}")