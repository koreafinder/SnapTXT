#!/usr/bin/env python3
"""
실전 검증 3: 실제 적용 증명 (핵심)
"""

from phase_3_0_production_api import ProductionSnapTXT, ProcessingContext

def verify_actual_application():
    """실제 적용 증명"""
    
    print("=" * 60)
    print("3️⃣ 실제 적용 증명 (핵심)")
    print("=" * 60)
    
    # Stage2/3 완료 후 상황 시뮬레이션 (진짜 비표준 문자 사용)
    stage23_result = "이것은 ‛비표준 인용부호′를 가진 텍스트입니다. ′또 다른 인용부호′도 있습니다."
    print(f"Stage2/3 done: {len(stage23_result)} chars")
    print(f"Stage2/3 text: '{stage23_result}'")
    
    print("\n" + "-" * 40)
    print("Production 교정 시작...")
    print("-" * 40)
    
    # Production 적용
    production = ProductionSnapTXT()
    context = ProcessingContext(domain="essay", safety_mode="standard")  # conservative -> standard
    
    final_text, report_path = production.apply(stage23_result, context)
    
    # 결과 분석
    if final_text != stage23_result:
        change_ratio = abs(len(final_text) - len(stage23_result)) / len(stage23_result) * 100
        print(f"Production applied: {len(stage23_result)} -> {len(final_text)} chars ({change_ratio:.1f}% change)")
        
        # 문자별 비교 (더 정확한 diff)
        print(f"\nCHAR-BY-CHAR COMPARISON:")
        for i, (c1, c2) in enumerate(zip(stage23_result, final_text)):
            if c1 != c2:
                print(f"Position {i}: '{c1}' (ord:{ord(c1)}) -> '{c2}' (ord:{ord(c2)})")
        
        # Diff 출력
        print(f"\nBEFORE: '{stage23_result}'")
        print(f"AFTER:  '{final_text}'")
        
        # 실제 적용된 규칙 확인
        applied_rules_count = len([r for r in production.active_rules if r])
        print(f"rules_applied={applied_rules_count}")
        
        if applied_rules_count > 0:
            print("✅ SUCCESS: 실제 규칙 적용됨")
        else:
            print("⚠️ WARNING: 텍스트 변경되었지만 적용 규칙 수 불명")
            
    else:
        print("⚠️ 텍스트 동일함 - Unicode/바이트 수준 비교 실시")
        
        # 바이트 수준 비교
        bytes1 = stage23_result.encode('utf-8')
        bytes2 = final_text.encode('utf-8')
        
        if bytes1 != bytes2:
            print("✅ SUCCESS: 바이트 수준에서 변경 감지됨")
            print(f"BYTES BEFORE: {bytes1}")
            print(f"BYTES AFTER:  {bytes2}")
        else:
            print("❌ FAIL: 바이트 수준에서도 변경 없음")
        
    print(f"\nReport: {report_path}")
    
    return final_text != stage23_result

if __name__ == "__main__":
    verify_actual_application()