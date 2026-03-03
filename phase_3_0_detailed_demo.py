#!/usr/bin/env python3
"""
Phase 3.0 Production 시스템 - 상세 기능 데모
규칙 적용 + 가시성 + 안전장치 통합 데모
"""

from phase_3_0_production_system import Phase3ProductionSystem, RuleEvidence, RuleState
import numpy as np

def run_detailed_demo():
    """상세 기능 데모"""
    
    print("🔍 **Phase 3.0 Production 상세 기능 데모**")
    print("=" * 50)
    
    # 시스템 초기화
    system = Phase3ProductionSystem() 
    system.initialize_production_rules()
    
    print(f"\n1️⃣ **Regression Gate 검증 데모**")
    print("-" * 30)
    
    # 새로운 규칙 후보 추가 시도 (일부는 실패하도록)
    candidate_rules = [
        {"pattern": "강력한 치환 규칙", "type": "character", "quality": "high"},
        {"pattern": "의심스러운 규칙", "type": "character", "quality": "low"},
        {"pattern": "안전한 구두점 규칙", "type": "punctuation", "quality": "high"}
    ]
    
    for i, rule in enumerate(candidate_rules):
        print(f"\n📋 후보 규칙 {i+1}: {rule['pattern']}")
        
        # 품질에 따라 시뮬레이션된 검증 결과 조정
        np.random.seed(42 + i)  # 재현가능한 결과
        
        passed, failures = system.regression_gate.validate_new_rule(rule)
        
        if passed:
            evidence = RuleEvidence(
                discovery_date="2026-03-04",
                sample_count=25,
                bootstrap_ci=(-0.01, -0.002),
                reproducibility_score=0.8,
                p_value=0.001,
                source_phase="Phase 3.0"
            )
            
            rule_id = system.lifecycle_manager.register_rule(rule, evidence)
            system.lifecycle_manager.promote_rule(rule_id, RuleState.VALIDATED, "Gate passed")
            system.lifecycle_manager.promote_rule(rule_id, RuleState.ACTIVE, "Production ready")
        else:
            print(f"   🚫 거부됨: {', '.join(failures)}")
    
    print(f"\n2️⃣ **Observability 시스템 데모**")
    print("-" * 30)
    
    # 활성 규칙으로 샘플 처리
    test_samples = [
        ("sample_A", "명상은 '마음의 고요'를 가져다 줍니다."),
        ("sample_B", "진정한 '자유'는 내면에서 시작됩니다."), 
        ("sample_C", "'지혜'의 길을 걸어보세요."),
        ("sample_D", "모든 '변화'는 기회입니다."),
        ("sample_E", "'평온함'을 유지하는 것이 중요합니다.")
    ]
    
    for sample_id, original in test_samples:
        processed = system.process_sample_with_observability(sample_id, original)
        print(f"   {sample_id}: {original[:40]}... → 처리됨")
    
    print(f"\n3️⃣ **Rule Lifecycle 관리 데모**")
    print("-" * 30)
    
    active_rules = system.lifecycle_manager.get_active_rules()
    print(f"📈 활성 규칙 현황:")
    
    for rule in active_rules:
        print(f"   {rule.rule_id}: {rule.pattern}")
        print(f"      상태: {rule.state.value}, 타입: {rule.rule_type}")
        print(f"      적용: {rule.metrics.application_count}회, 성공: {rule.metrics.success_count}회")
        print(f"      마지막 ΔCER: {rule.metrics.current_delta_cer:.4f}")
        
    # 성능 리포트 생성
    if active_rules:
        first_rule_id = active_rules[0].rule_id
        report = system.observability.generate_rule_report(first_rule_id)
        
        print(f"\n📊 {first_rule_id} 상세 리포트:")
        if "error" in report:
            print(f"   ⚠️ {report['error']} (아직 적용 로그 없음)")
        else:
            print(f"   총 적용: {report['total_applications']}회")
            print(f"   평균 ΔCER: {report['avg_delta_cer']:.4f}")  
            print(f"   평균 신뢰도: {report['avg_confidence']:.3f}")
    
    print(f"\n4️⃣ **User Safety 시스템 데모**")
    print("-" * 30)
    
    safety_modes = ["conservative", "standard", "aggressive"]
    
    for mode in safety_modes:
        system.safety_system.current_mode = mode
        should_apply, reason = system.safety_system.should_auto_apply("character", 0.75)
        
        print(f"🔒 {mode} 모드: 자동적용={should_apply} ({reason})")
        
    # 사용자 추천 예시
    recommendation = system.safety_system.generate_user_recommendation(
        "rule_example", 
        "명상을 통해 '내면의 평화'를 찾을 수 있습니다.",
        "명상을 통해 '내면의 평화'를 찾을 수 있습니다.",
        0.85
    )
    
    print(f"\n💡 사용자 추천 예시:")
    print(f"   추천: {recommendation['recommendation']}")
    print(f"   이유: {recommendation['reason']}")
    print(f"   사용자 액션 필요: {recommendation['user_action_required']}")
    
    print(f"\n5️⃣ **실험 레이어 관리 데모**")  
    print("-" * 30)
    
    print(f"🧪 보류된 클러스터들 (실험 상태):")
    for cluster in system.experiment_clusters:
        print(f"   {cluster} → 데이터 축적 후 재검증 대기")
    
    print(f"\n6️⃣ **시스템 상태 점검**")
    print("-" * 30)
    
    health_report = system.run_health_check()
    
    print(f"\n📈 **Phase 3.0 시스템 종합 상태**")
    print("=" * 50)
    print(f"🟢 Regression Gate: 자동 품질 검증 시스템 가동")
    print(f"🟢 Rule Lifecycle: {health_report['active_rules']}개 활성 규칙 관리 중") 
    print(f"🟢 Observability: {health_report['total_applications']}회 추적 완료")
    print(f"🟢 User Safety: 보수적/표준/적극적 모드 지원")
    print(f"🟡 실험 레이어: {len(system.experiment_clusters)}개 클러스터 대기")
    print(f"🟢 전체 상태: {health_report['system_status']}")
    
    return True

if __name__ == "__main__":
    run_detailed_demo()