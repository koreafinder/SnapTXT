#!/usr/bin/env python3
"""
자동 규칙 적용 시스템 실행 스크립트
"""

import sys
from auto_applicator import AutoRuleApplicator

def run_real_application():
    """실제 자동 규칙 적용 실행"""
    applicator = AutoRuleApplicator()
    
    print("🚀 자동 규칙 적용 실행")
    print("="*50)
    
    # 실제 적용 실행
    result = applicator.run_auto_application(dry_run=False)
    
    if result['success']:
        analysis = result.get('analysis', {})
        app_result = result.get('application_result', {})
        
        print(f"\n📊 적용 결과:")
        print(f"   총 학습된 규칙: {analysis.get('total', 0)}개")
        print(f"   적용된 규칙: {app_result.get('applied', 0)}개")
        print(f"   스킵된 규칙: {app_result.get('skipped', 0)}개")
        print(f"   오류 규칙: {app_result.get('errors', 0)}개")
        
        if result.get('backup_file'):
            print(f"\n💾 백업 파일: {result['backup_file']}")
        
        if result.get('report_file'):
            print(f"📋 리포트 파일: {result['report_file']}")
        
        # 유효성 검증
        validation = applicator.validate_applied_rules()
        if validation.get('valid', False):
            print(f"\n✅ 규칙 적용 성공!")
            print(f"   전체 규칙: {validation.get('total_rules', 0)}개")
            print(f"   자동 적용 규칙: {validation.get('auto_applied_rules', 0)}개")
        else:
            print(f"\n❌ 검증 실패: {validation.get('error', 'Unknown')}")
    
    else:
        print(f"\n❌ 적용 실패: {result.get('error', 'Unknown')}")

if __name__ == "__main__":
    run_real_application()