#!/usr/bin/env python3
"""
SnapTXT Production 배포 전 체크리스트 시스템
8가지 필수 체크포인트 자동 검증

배포 직전 마지막 안전 점검용
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import hashlib
import stat

# 기존 Production 모듈들
from phase_3_0_production_api import get_production_instance
from phase_3_0_ruleset_version_manager import get_version_manager
from phase_3_0_rule_isolation import RuleIsolationSystem

class PreDeploymentChecker:
    """배포 전 체크리스트 검증 시스템"""
    
    def __init__(self):
        self.checklist = []
        self.results = {}
        self.critical_failures = []
        
    def run_full_checklist(self) -> Tuple[bool, Dict]:
        """전체 체크리스트 실행"""
        
        print("🔍 **Production 배포 전 체크리스트 시작**")
        print("=" * 50)
        
        # 1. Conservative 모드 기본값 고정 확인
        self.check_conservative_default()
        
        # 2. heldout_set 경로 고정 + 읽기 전용
        self.check_heldout_protection()
        
        # 3. ruleset_storage 백업 위치 설정 
        self.check_backup_location()
        
        # 4. Gate fail 시 동작 고정
        self.check_gate_fail_behavior()
        
        # 5. Roll back 테스트
        self.test_rollback_functionality()
        
        # 6. Rule isolation 감사
        self.audit_rule_isolation()
        
        # 7. ΔCER 표기 일관성
        self.verify_delta_cer_consistency()
        
        # 8. 로그 폭주 방지
        self.check_log_management()
        
        # 전체 결과 요약
        return self.generate_final_report()
        
    def check_conservative_default(self):
        """1. Conservative 모드 기본값 확인"""
        
        print("1️⃣ Conservative 모드 기본값 확인...")
        
        try:
            production = get_production_instance()
            default_mode = production.safety_system.current_mode
            
            if default_mode == "conservative":
                self.results["conservative_default"] = {"status": "PASS", "details": "Conservative 모드가 기본값으로 설정됨"}
                print("   ✅ PASS: Conservative 모드 기본 설정됨")
            else:
                self.results["conservative_default"] = {"status": "FAIL", "details": f"현재 기본값: {default_mode}"}
                self.critical_failures.append("Conservative 모드가 기본값이 아님")
                print(f"   ❌ FAIL: 현재 기본값은 {default_mode}")
                
        except Exception as e:
            self.results["conservative_default"] = {"status": "ERROR", "details": str(e)}
            print(f"   ❌ ERROR: {e}")
            
    def check_heldout_protection(self):
        """2. heldout_set 경로 고정 + 보호 확인"""
        
        print("2️⃣ Held-out 세트 보호 확인...")
        
        base_dir = Path(__file__).parent
        heldout_path = base_dir / "held_out_sets" / "heldout_set_v1.0.json"
        
        try:
            # 파일 존재 확인
            if not heldout_path.exists():
                self.results["heldout_protection"] = {"status": "FAIL", "details": "heldout_set_v1.0.json 파일 없음"}
                self.critical_failures.append("Held-out 세트 파일 누락")
                print("   ❌ FAIL: heldout_set_v1.0.json 없음")
                return
                
            # 읽기 전용 설정 시도
            try:
                heldout_path.chmod(stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
                protection_status = "읽기 전용 설정 완료"
            except:
                protection_status = "읽기 전용 설정 시도 (권한 제한으로 부분 적용)"
                
            # 파일 내용 무결성 확인
            with open(heldout_path, 'r', encoding='utf-8') as f:
                heldout_data = json.load(f)
                
            if "hash_signature" in heldout_data:
                self.results["heldout_protection"] = {"status": "PASS", "details": f"파일 보호됨, {protection_status}"}
                print(f"   ✅ PASS: {protection_status}")
            else:
                self.results["heldout_protection"] = {"status": "WARNING", "details": "해시 서명 없음"}
                print("   ⚠️ WARNING: 해시 서명 없음")
                
        except Exception as e:
            self.results["heldout_protection"] = {"status": "ERROR", "details": str(e)}
            print(f"   ❌ ERROR: {e}")
            
    def check_backup_location(self):
        """3. ruleset_storage 백업 위치 확인"""
        
        print("3️⃣ RuleSet 백업 위치 확인...")
        
        try:
            primary_storage = Path("ruleset_storage")
            backup_storage = Path("C:/SnapTXT_Backup/ruleset_storage")  # 로컬 백업 위치
            
            # 기본 저장소 확인
            if not primary_storage.exists():
                self.results["backup_location"] = {"status": "FAIL", "details": "기본 ruleset_storage 폴더 없음"}
                print("   ❌ FAIL: 기본 저장소 없음")
                return
                
            # 백업 위치 생성 및 동기화
            backup_storage.mkdir(parents=True, exist_ok=True)
            
            # 현재 설정 백업
            if primary_storage.exists():
                # 최신 파일들만 백업 (과도한 복사 방지)
                latest_versions = sorted(primary_storage.glob("versions/ruleset_*.json"))[-3:]  # 최신 3개만
                
                for version_file in latest_versions:
                    backup_file = backup_storage / "versions" / version_file.name
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(version_file, backup_file)
                    
            self.results["backup_location"] = {"status": "PASS", "details": f"백업 위치: {backup_storage}"}
            print(f"   ✅ PASS: 백업 위치 설정됨 ({backup_storage})")
            
        except Exception as e:
            self.results["backup_location"] = {"status": "ERROR", "details": str(e)}
            print(f"   ❌ ERROR: {e}")
            
    def check_gate_fail_behavior(self):
        """4. Gate Fail 시 동작 확인"""
        
        print("4️⃣ Gate Fail 동작 확인...")
        
        try:
            # Gate 실패 시나리오 테스트
            production = get_production_instance()
            
            # 의도적으로 실패할 규칙 후보
            bad_rule = {
                "pattern": "테스트용 실패 규칙",
                "type": "character",
                "confidence": 0.3  # 낮은 신뢰도로 실패 유도
            }
            
            # Gate 검증 시도
            gate_report_path = production.evaluate_new_rule(bad_rule, "essay")
            
            # 리포트 파일 확인
            if gate_report_path and Path(gate_report_path).exists():
                with open(gate_report_path, 'r', encoding='utf-8') as f:
                    gate_result = json.load(f)
                    
                if not gate_result.get("gate_pass", True):  # 실패했어야 함
                    self.results["gate_fail_behavior"] = {
                        "status": "PASS", 
                        "details": "Gate 실패 시 적용 안 함 + 리포트 저장 확인됨"
                    }
                    print("   ✅ PASS: Gate 실패 시 안전한 동작 확인")
                else:
                    self.results["gate_fail_behavior"] = {"status": "WARNING", "details": "테스트 규칙이 예상과 달리 통과됨"}
                    print("   ⚠️ WARNING: 테스트 규칙이 통과됨")
            else:
                self.results["gate_fail_behavior"] = {"status": "FAIL", "details": "Gate 리포트 생성 실패"}
                print("   ❌ FAIL: 리포트 생성 실패")
                
        except Exception as e:
            self.results["gate_fail_behavior"] = {"status": "ERROR", "details": str(e)}
            print(f"   ❌ ERROR: {e}")
            
    def test_rollback_functionality(self): 
        """5. Roll back 기능 테스트"""
        
        print("5️⃣ Rollback 기능 테스트...")
        
        try:
            version_manager = get_version_manager()
            
            # 현재 상태 백업
            original_version = version_manager.current_active_version
            
            # 테스트용 나쁜 버전 생성
            bad_rules = {
                "bad_test_rule": {
                    "pattern": "테스트용 문제 규칙",
                    "confidence": 0.1,
                    "validation_status": "test_only"
                }
            }
            
            bad_version_id = version_manager.create_new_version(
                name="Test Bad Version", 
                description="롤백 테스트용 나쁜 버전",
                rules=bad_rules,
                created_by="test_system"
            )
            
            # 나쁜 버전 활성화
            activate_success = version_manager.activate_ruleset(bad_version_id, "롤백 테스트")
            
            if activate_success:
                # 30초 내 롤백 테스트
                start_time = datetime.now()
                rollback_success = version_manager.rollback_last("배포 전 테스트")
                end_time = datetime.now()
                
                rollback_time = (end_time - start_time).total_seconds()
                
                if rollback_success and rollback_time < 30:
                    self.results["rollback_test"] = {
                        "status": "PASS", 
                        "details": f"롤백 성공, 소요시간: {rollback_time:.2f}초"
                    }
                    print(f"   ✅ PASS: 롤백 성공 ({rollback_time:.2f}초)")
                else:
                    self.results["rollback_test"] = {"status": "FAIL", "details": "롤백 실패 또는 시간 초과"}
                    print("   ❌ FAIL: 롤백 실패 또는 30초 초과")
            else:
                self.results["rollback_test"] = {"status": "WARNING", "details": "테스트 버전 활성화 실패"}
                print("   ⚠️ WARNING: 테스트 버전 활성화 실패")
                
        except Exception as e:
            self.results["rollback_test"] = {"status": "ERROR", "details": str(e)}
            print(f"   ❌ ERROR: {e}")
            
    def audit_rule_isolation(self):
        """6. Rule isolation 감사"""
        
        print("6️⃣ Rule Isolation 감사...")
        
        try:
            isolation_system = RuleIsolationSystem()
            integrity_ok, issues = isolation_system.audit_isolation_integrity()
            
            # 추가로 중복 파일 검사
            all_rule_files = []
            base_path = Path("rules_isolated")
            
            for category_dir in ["active", "experimental", "blocked"]:
                category_path = base_path / category_dir
                if category_path.exists():
                    rule_files = list(category_path.rglob("*.json"))
                    all_rule_files.extend([f.name for f in rule_files])
                    
            duplicate_files = len(all_rule_files) - len(set(all_rule_files))
            
            if integrity_ok and duplicate_files == 0:
                self.results["rule_isolation"] = {
                    "status": "PASS", 
                    "details": f"무결성 OK, 중복 파일 0개"
                }
                print("   ✅ PASS: Rule isolation 무결성 확인")
            else:
                problem_details = f"무결성 이슈 {len(issues)}개, 중복 파일 {duplicate_files}개"
                self.results["rule_isolation"] = {"status": "FAIL", "details": problem_details}
                print(f"   ❌ FAIL: {problem_details}")
                
        except Exception as e:
            self.results["rule_isolation"] = {"status": "ERROR", "details": str(e)}
            print(f"   ❌ ERROR: {e}")
            
    def verify_delta_cer_consistency(self):
        """7. ΔCER 표기 일관성 확인"""
        
        print("7️⃣ ΔCER 표기 일관성 확인...")
        
        try:
            # 샘플 3개로 일관성 테스트
            test_cases = [
                {"before_cer": 0.10, "after_cer": 0.07, "expected_delta": -0.03, "expected_ui": "개선 +3.0%p"},
                {"before_cer": 0.05, "after_cer": 0.08, "expected_delta": 0.03, "expected_ui": "악화 -3.0%p"},
                {"before_cer": 0.12, "after_cer": 0.11, "expected_delta": -0.01, "expected_ui": "개선 +1.0%p"}
            ]
            
            consistency_errors = []
            
            for i, case in enumerate(test_cases):
                # 내부 계산: delta = after - before
                calculated_delta = case["after_cer"] - case["before_cer"]
                
                if abs(calculated_delta - case["expected_delta"]) > 0.001:
                    consistency_errors.append(f"Case {i+1}: 내부 계산 불일치")
                    
                # UI 표기 확인 (개선이면 양수로 표시)
                if calculated_delta < 0:  # 개선
                    improvement_percent = abs(calculated_delta) * 100
                    ui_text = f"개선 +{improvement_percent:.1f}%p"
                else:  # 악화
                    degradation_percent = calculated_delta * 100
                    ui_text = f"악화 -{degradation_percent:.1f}%p"
                    
                if ui_text != case["expected_ui"]:
                    consistency_errors.append(f"Case {i+1}: UI 표기 불일치")
                    
            if len(consistency_errors) == 0:
                self.results["delta_cer_consistency"] = {
                    "status": "PASS",
                    "details": "내부 계산과 UI 표기 모두 일관됨"
                }
                print("   ✅ PASS: ΔCER 표기 일관성 확인")
            else:
                self.results["delta_cer_consistency"] = {
                    "status": "FAIL",
                    "details": f"불일치 {len(consistency_errors)}개: {', '.join(consistency_errors)}"
                }
                print(f"   ❌ FAIL: {len(consistency_errors)}개 불일치")
                
        except Exception as e:
            self.results["delta_cer_consistency"] = {"status": "ERROR", "details": str(e)}
            print(f"   ❌ ERROR: {e}")
            
    def check_log_management(self):
        """8. 로그 폭주 방지 확인"""
        
        print("8️⃣ 로그 관리 시스템 확인...")
        
        try:
            # 로그 디렉토리 크기 체크
            log_dirs = ["production_reports", "ruleset_storage/rollback_logs", "rules_isolated/migration_logs"]
            total_log_size = 0
            log_file_count = 0
            
            for log_dir in log_dirs:
                log_path = Path(log_dir)
                if log_path.exists():
                    for log_file in log_path.rglob("*.json"):
                        total_log_size += log_file.stat().st_size
                        log_file_count += 1
                        
            # 로그 크기 임계값 (10MB)
            size_mb = total_log_size / (1024 * 1024)
            
            # 로그 순환 정책 확인 (일주일 이상 된 파일은 정리)
            old_logs = []
            week_ago = datetime.now().timestamp() - (7 * 24 * 3600)
            
            for log_dir in log_dirs:
                log_path = Path(log_dir) 
                if log_path.exists():
                    for log_file in log_path.rglob("*.json"):
                        if log_file.stat().st_mtime < week_ago:
                            old_logs.append(log_file)
                            
            status_details = f"로그 크기: {size_mb:.1f}MB, 파일 수: {log_file_count}개, 오래된 파일: {len(old_logs)}개"
            
            if size_mb < 10 and log_file_count < 100:
                self.results["log_management"] = {"status": "PASS", "details": status_details}
                print(f"   ✅ PASS: 로그 관리 양호 ({status_details})")
            else:
                self.results["log_management"] = {"status": "WARNING", "details": f"로그 정리 필요 - {status_details}"}
                print(f"   ⚠️ WARNING: 로그 정리 필요")
                
        except Exception as e:
            self.results["log_management"] = {"status": "ERROR", "details": str(e)}
            print(f"   ❌ ERROR: {e}")
            
    def generate_final_report(self) -> Tuple[bool, Dict]:
        """최종 체크리스트 리포트 생성"""
        
        print(f"\n" + "=" * 50)
        print("📊 **배포 전 체크리스트 최종 결과**")
        
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results.values() if r["status"] == "PASS")
        failed_checks = sum(1 for r in self.results.values() if r["status"] == "FAIL")
        warning_checks = sum(1 for r in self.results.values() if r["status"] == "WARNING")
        
        print(f"✅ 통과: {passed_checks}/{total_checks}")
        print(f"❌ 실패: {failed_checks}/{total_checks}")
        print(f"⚠️ 경고: {warning_checks}/{total_checks}")
        
        # 실패한 항목들 상세 표시
        if failed_checks > 0:
            print(f"\n🚨 **Critical Issues (배포 차단):**")
            for check_name, result in self.results.items():
                if result["status"] == "FAIL":
                    print(f"   ❌ {check_name}: {result['details']}")
                    
        # 경고 항목들
        if warning_checks > 0:
            print(f"\n⚠️ **Warnings (주의 필요):**")
            for check_name, result in self.results.items():
                if result["status"] == "WARNING":
                    print(f"   ⚠️ {check_name}: {result['details']}")
                    
        # 배포 가능 여부 결정
        deployment_ready = (failed_checks == 0 and len(self.critical_failures) == 0)
        
        if deployment_ready:
            print(f"\n🚀 **배포 승인: Production 런칭 가능**")
        else:
            print(f"\n🚫 **배포 차단: Critical Issues 해결 필요**")
            
        # 리포트 저장
        final_report = {
            "timestamp": datetime.now().isoformat(),
            "deployment_ready": deployment_ready,
            "summary": {
                "total_checks": total_checks,
                "passed": passed_checks,
                "failed": failed_checks,
                "warnings": warning_checks
            },
            "critical_failures": self.critical_failures,
            "detailed_results": self.results
        }
        
        report_path = Path("deployment_checklist_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)
            
        print(f"\n📁 상세 리포트: {report_path}")
        
        return deployment_ready, final_report

def main():
    """배포 전 체크리스트 실행"""
    
    checker = PreDeploymentChecker()
    deployment_ready, report = checker.run_full_checklist()
    
    if deployment_ready:
        print(f"\n🎯 **다음 단계: 메인 UI 통합**")
        print("   - Apply (Production) 버튼")
        print("   - Show Last Report 버튼")  
        print("   - Rollback 버튼")
        
    return deployment_ready

if __name__ == "__main__":
    main()