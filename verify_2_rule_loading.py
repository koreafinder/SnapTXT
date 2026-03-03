#!/usr/bin/env python3
"""
실전 검증 2: active 규칙 실제 로딩 증명
"""

import os
from pathlib import Path
from phase_3_0_production_api import ProductionSnapTXT

def verify_active_rules_loading():
    """활성 규칙 로딩 증명"""
    
    print("=" * 60)
    print("2️⃣ ACTIVE 규칙 실제 로딩 증명")  
    print("=" * 60)
    
    # active 폴더 파일 목록
    base_dir = Path(__file__).parent
    active_dir = base_dir / "rules_isolated" / "active"
    
    print(f"Active 폴더 경로: {active_dir.absolute()}")
    
    if active_dir.exists():
        json_files = list(active_dir.rglob("*.json"))
        print(f"Active 폴더 JSON 파일: {len(json_files)}개")
        for file in json_files:
            rel_path = file.relative_to(active_dir)
            print(f"  - {rel_path}")
    else:
        print("⚠️ Active 폴더 없음")
    
    print("\n" + "-" * 40)
    print("Production API 로딩 시도...")
    print("-" * 40)
    
    # Production API 초기화 (로그 확인)
    production = ProductionSnapTXT()
    
    # 로딩된 규칙 검증
    loaded_count = len(production.active_rules)
    
    if loaded_count > 0:
        print(f"\n✅ SUCCESS: N={loaded_count} > 0")
        print("Loaded Rule Details:")
        for rule_id, rule_info in production.active_rules.items():
            print(f"  - {rule_id}: {rule_info.get('pattern', 'No pattern')[:50]}...")
    else:
        print(f"\n❌ FAIL: N={loaded_count} = 0")
    
    return loaded_count

if __name__ == "__main__":
    verify_active_rules_loading()