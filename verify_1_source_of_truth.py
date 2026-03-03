#!/usr/bin/env python3
"""
실전 검증 1: Source of Truth 단일 경로 증명
"""

from pathlib import Path
import sys

def verify_single_source_of_truth():
    """경로 일치 증명"""
    
    print("=" * 60)
    print("1️⃣ SOURCE OF TRUTH 단일 경로 증명")
    print("=" * 60)
    
    # Rule Isolation System 경로
    from phase_3_0_rule_isolation import RuleIsolationSystem
    isolation = RuleIsolationSystem()
    ui_active_dir = isolation.active_dir.absolute()
    
    print(f"[DEBUG] UI ACTIVE_DIR: {ui_active_dir}")
    
    # Production API 경로 (내부 로직 추출)
    base_dir = Path(__file__).parent
    api_active_dir = (base_dir / "rules_isolated" / "active").absolute()
    
    print(f"[DEBUG] API ACTIVE_DIR: {api_active_dir}")
    
    # 일치 여부
    paths_match = ui_active_dir == api_active_dir
    print(f"[DEBUG] PATHS_MATCH: {paths_match}")
    
    if paths_match:
        print("✅ PASS: 단일 Source of Truth 확인")
    else:
        print("❌ FAIL: 경로 불일치")
        sys.exit(1)
    
    return ui_active_dir

if __name__ == "__main__":
    verify_single_source_of_truth()