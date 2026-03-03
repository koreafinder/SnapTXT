#!/usr/bin/env python3
"""
SnapTXT Production 문제 진단 3종 세트 시스템

문제/이상 징후 발생 시 아래 3개만 수집:
1. Gate 결과 JSON 1개 (최근 실패 또는 성공)
2. 적용 로그 (어떤 규칙이 적용됐는지)
3. 현재 active ruleset id + 모드

이 3개면 거의 바로 "원인 → 조치"로 들어갈 수 있음
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import zipfile

# Production 모듈들
from phase_3_0_production_api import get_production_instance
from phase_3_0_ruleset_version_manager import get_version_manager

class DiagnosticTriple:
    """진단 3종 세트"""
    
    def __init__(self, issue_description: str = ""):
        self.issue_description = issue_description
        self.diagnostic_id = f"diag_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.collection_timestamp = datetime.now().isoformat()
        
        # 수집 결과
        self.gate_result_path = None
        self.application_log_path = None
        self.system_state = None
        
    def collect_diagnostic_set(self) -> Dict:
        """진단 3종 세트 수집"""
        
        print(f"🔍 **진단 3종 세트 수집 시작**")
        print(f"📋 진단 ID: {self.diagnostic_id}")
        print(f"📝 이슈 설명: {self.issue_description or '일반 진단'}")
        print("=" * 50)
        
        # 1. Gate 결과 JSON 수집
        print("1️⃣ Gate 결과 수집...")
        self.gate_result_path = self._collect_latest_gate_result()
        
        # 2. 적용 로그 수집
        print("2️⃣ 적용 로그 수집...")
        self.application_log_path = self._collect_application_logs()
        
        # 3. 시스템 상태 수집
        print("3️⃣ 시스템 상태 수집...")
        self.system_state = self._collect_system_state()
        
        # 통합 리포트 생성
        diagnostic_report = self._generate_diagnostic_report()
        
        # 진단 패키지 생성
        package_path = self._create_diagnostic_package()
        
        print("=" * 50)
        print(f"✅ **진단 3종 세트 수집 완료**")
        print(f"📦 패키지 위치: {package_path}")
        
        return diagnostic_report
        
    def _collect_latest_gate_result(self) -> Optional[str]:
        """최신 Gate 결과 수집"""
        
        gate_files = []
        
        # production_reports에서 gate 결과 찾기
        reports_dir = Path("production_reports") 
        if reports_dir.exists():
            gate_files.extend(reports_dir.glob("gate_evaluation_*.json"))
            
        # gate_results에서도 찾기
        gate_results_dir = Path("gate_results")
        if gate_results_dir.exists():
            gate_files.extend(gate_results_dir.glob("gate_result_*.json"))
            
        if not gate_files:
            print("   ⚠️ Gate 결과 파일 없음")
            return None
            
        # 최신 파일 선택
        latest_gate = max(gate_files, key=lambda x: x.stat().st_mtime)
        
        try:
            with open(latest_gate, 'r', encoding='utf-8') as f:
                gate_data = json.load(f)
                
            gate_pass = gate_data.get("gate_pass", True)
            gate_status = "PASS" if gate_pass else "FAIL"
            fail_count = len(gate_data.get("fail_reasons", []))
            
            print(f"   📄 최신 Gate 결과: {latest_gate.name}")
            print(f"   📊 상태: {gate_status} (실패 사유: {fail_count}개)")
            
            return str(latest_gate)
            
        except Exception as e:
            print(f"   ❌ Gate 결과 읽기 실패: {e}")
            return str(latest_gate)  # 파일 경로라도 반환
            
    def _collect_application_logs(self) -> Optional[str]:
        """적용 로그 수집"""
        
        log_files = []
        
        # production_reports에서 processing 로그 찾기
        reports_dir = Path("production_reports")
        if reports_dir.exists():
            log_files.extend(reports_dir.glob("processing_report_*.json"))
            
        if not log_files:
            print("   ⚠️ 적용 로그 파일 없음")
            return None
            
        # 최신 몇 개 파일 선택 (최근 활동 패턴 분석용)
        recent_logs = sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
        
        total_applications = 0
        applied_rules = set()
        
        for log_file in recent_logs:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                    
                result = log_data.get("result", {})
                rules = result.get("applied_rules", [])
                
                total_applications += 1
                for rule in rules:
                    applied_rules.add(rule.get("rule_id", "unknown"))
                    
            except Exception as e:
                print(f"   ⚠️ 로그 파일 읽기 실패: {log_file.name} - {e}")
                
        print(f"   📄 최근 적용 로그: {len(recent_logs)}개 파일")
        print(f"   📊 총 처리 건수: {total_applications}회")
        print(f"   🔧 적용된 규칙: {len(applied_rules)}개 ({', '.join(list(applied_rules)[:3])}{'...' if len(applied_rules) > 3 else ''})")
        
        return str(recent_logs[0]) if recent_logs else None
        
    def _collect_system_state(self) -> Dict:
        """시스템 상태 수집"""
        
        try:
            # 버전 관리자에서 현재 상태
            version_manager = get_version_manager()
            
            active_version = version_manager.current_active_version
            total_versions = len(version_manager.versions)
            rollback_available = len(version_manager.rollback_history) > 0
            
            # Production 인스턴스에서 모드 정보
            production = get_production_instance()
            current_mode = production.safety_system.current_mode
            
            # 활성 규칙 정보
            active_rules = production.active_rules
            active_rule_count = len([r for r in active_rules.values() if r.get("state") == "active"])
            
            # 시스템 건강성 체크
            health_indicators = self._check_system_health()
            
            system_state = {
                "collection_timestamp": self.collection_timestamp,
                "active_ruleset_id": active_version,
                "safety_mode": current_mode,
                "total_versions": total_versions,
                "active_rules_count": active_rule_count,
                "rollback_available": rollback_available,
                "last_rollback": version_manager.rollback_history[-1].rollback_id if version_manager.rollback_history else None,
                "health_indicators": health_indicators
            }
            
            print(f"   📊 활성 RuleSet: {active_version}")
            print(f"   🔧 안전 모드: {current_mode}")
            print(f"   📦 총 버전: {total_versions}개")
            print(f"   ✅ 활성 규칙: {active_rule_count}개")
            print(f"   🔄 롤백 가능: {'Yes' if rollback_available else 'No'}")
            
            return system_state
            
        except Exception as e:
            print(f"   ❌ 시스템 상태 수집 실패: {e}")
            
            return {
                "collection_timestamp": self.collection_timestamp,
                "error": str(e),
                "active_ruleset_id": "unknown",
                "safety_mode": "unknown"
            }
            
    def _check_system_health(self) -> Dict:
        """시스템 건강성 체크"""
        
        health = {
            "disk_space_ok": True,
            "log_size_ok": True,
            "backup_ok": True,
            "isolation_ok": True
        }
        
        try:
            # 디스크 공간 체크 (간단히)
            import shutil
            total, used, free = shutil.disk_usage(Path.cwd())
            free_gb = free // (1024**3)
            health["disk_space_ok"] = free_gb > 1  # 1GB 이상 여유
            health["free_disk_gb"] = free_gb
            
            # 로그 크기 체크
            log_dirs = ["production_reports", "operation_logs", "rules_isolated/migration_logs"]
            total_log_size = 0
            
            for log_dir in log_dirs:
                log_path = Path(log_dir)
                if log_path.exists():
                    for file in log_path.rglob("*"):
                        if file.is_file():
                            total_log_size += file.stat().st_size
                            
            log_size_mb = total_log_size / (1024**2)
            health["log_size_ok"] = log_size_mb < 50  # 50MB 미만
            health["log_size_mb"] = round(log_size_mb, 2)
            
            # 백업 체크
            backup_dirs = ["ruleset_storage/backups", "C:/SnapTXT_Backup"]
            backup_file_count = 0
            
            for backup_dir in backup_dirs:
                backup_path = Path(backup_dir)
                if backup_path.exists():
                    backup_file_count += len(list(backup_path.rglob("*.json")))
                    
            health["backup_ok"] = backup_file_count > 0
            health["backup_files"] = backup_file_count
            
            # 격리 체크
            isolation_path = Path("rules_isolated")
            if isolation_path.exists():
                active_rules = len(list((isolation_path / "active").rglob("*.json")))
                experimental_rules = len(list((isolation_path / "experimental").rglob("*.json")))
                blocked_rules = len(list((isolation_path / "blocked").rglob("*.json")))
                
                health["isolation_ok"] = active_rules > 0  # 최소 1개 활성 규칙 필요
                health["isolation_distribution"] = {
                    "active": active_rules,
                    "experimental": experimental_rules, 
                    "blocked": blocked_rules
                }
            else:
                health["isolation_ok"] = False
                
        except Exception as e:
            health["health_check_error"] = str(e)
            
        return health
        
    def _generate_diagnostic_report(self) -> Dict:
        """통합 진단 리포트 생성"""
        
        diagnostic_report = {
            "diagnostic_id": self.diagnostic_id,
            "issue_description": self.issue_description,
            "collection_timestamp": self.collection_timestamp,
            "diagnostic_triple": {
                "gate_result_path": self.gate_result_path,
                "application_log_path": self.application_log_path,
                "system_state": self.system_state
            },
            "quick_diagnosis": self._perform_quick_diagnosis(),
            "recommended_actions": self._suggest_actions()
        }
        
        # 리포트 파일 저장
        report_path = Path(f"diagnostic_report_{self.diagnostic_id}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(diagnostic_report, f, indent=2, ensure_ascii=False)
            
        print(f"📋 통합 리포트: {report_path}")
        
        return diagnostic_report
        
    def _perform_quick_diagnosis(self) -> Dict:
        """빠른 진단 수행"""
        
        diagnosis = {
            "system_stability": "unknown",
            "potential_issues": [],
            "confidence_level": "low"
        }
        
        if not self.system_state:
            diagnosis["potential_issues"].append("시스템 상태 수집 실패")
            return diagnosis
            
        try:
            # 건강성 지표 체크
            health = self.system_state.get("health_indicators", {})
            
            if not health.get("disk_space_ok", True):
                diagnosis["potential_issues"].append("디스크 공간 부족")
                
            if not health.get("log_size_ok", True):
                diagnosis["potential_issues"].append("로그 크기 과대")
                
            if not health.get("backup_ok", True):
                diagnosis["potential_issues"].append("백업 파일 없음")
                
            if not health.get("isolation_ok", True):
                diagnosis["potential_issues"].append("규칙 격리 문제")
                
            # Gate 결과 분석
            if self.gate_result_path:
                try:
                    with open(self.gate_result_path, 'r', encoding='utf-8') as f:
                        gate_data = json.load(f)
                        
                    if not gate_data.get("gate_pass", True):
                        diagnosis["potential_issues"].append("최근 Gate 검증 실패")
                        
                except:
                    pass
                    
            # 안전성 평가
            if len(diagnosis["potential_issues"]) == 0:
                diagnosis["system_stability"] = "stable"
                diagnosis["confidence_level"] = "high"
            elif len(diagnosis["potential_issues"]) <= 2:
                diagnosis["system_stability"] = "warning"
                diagnosis["confidence_level"] = "medium"
            else:
                diagnosis["system_stability"] = "unstable"
                diagnosis["confidence_level"] = "high"
                
        except Exception as e:
            diagnosis["potential_issues"].append(f"진단 오류: {e}")
            
        return diagnosis
        
    def _suggest_actions(self) -> List[str]:
        """권장 조치 제안"""
        
        actions = []
        
        if not self.system_state:
            actions.append("시스템 상태 수동 확인 필요")
            return actions
            
        try:
            health = self.system_state.get("health_indicators", {})
            
            # 건강성 기반 권장 조치
            if not health.get("disk_space_ok", True):
                actions.append("디스크 정리 또는 로그 순환 정책 적용")
                
            if not health.get("backup_ok", True):
                actions.append("백업 시스템 점검 및 복구")
                
            if self.system_state.get("safety_mode") != "conservative":
                actions.append("Conservative 모드로 전환하여 안전성 확보")
                
            # Gate 실패 시 조치
            if self.gate_result_path:
                try:
                    with open(self.gate_result_path, 'r', encoding='utf-8') as f:
                        gate_data = json.load(f)
                        
                    if not gate_data.get("gate_pass", True):
                        actions.append("Gate 실패 사유 분석 후 규칙 개선")
                        actions.append("문제 규칙을 blocked 상태로 격리")
                        
                except:
                    pass
                    
            # 롤백 가능성 체크
            if self.system_state.get("rollback_available", False):
                actions.append("문제 지속 시 rollback_last() 실행 고려")
            else:
                actions.append("롤백 불가 상태 - 수동 복구 필요")
                
        except Exception as e:
            actions.append(f"권장 조치 분석 실패: {e}")
            
        if not actions:
            actions.append("시스템 정상 - 추가 조치 불필요")
            
        return actions
        
    def _create_diagnostic_package(self) -> str:
        """진단 패키지 ZIP 생성"""
        
        package_path = Path(f"diagnostic_package_{self.diagnostic_id}.zip")
        
        try:
            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                
                # 통합 리포트 추가
                report_file = f"diagnostic_report_{self.diagnostic_id}.json"
                if Path(report_file).exists():
                    zipf.write(report_file, f"diagnostic_report.json")
                    
                # Gate 결과 추가
                if self.gate_result_path and Path(self.gate_result_path).exists():
                    zipf.write(self.gate_result_path, f"gate_result.json")
                    
                # 적용 로그 추가
                if self.application_log_path and Path(self.application_log_path).exists():
                    zipf.write(self.application_log_path, f"application_log.json")
                    
                # 시스템 상태 별도 저장
                system_state_file = f"system_state_{self.diagnostic_id}.json"
                with open(system_state_file, 'w', encoding='utf-8') as f:
                    json.dump(self.system_state, f, indent=2, ensure_ascii=False)
                zipf.write(system_state_file, "system_state.json")
                
                # 정리: 임시 파일들 삭제
                for temp_file in [report_file, system_state_file]:
                    if Path(temp_file).exists():
                        Path(temp_file).unlink()
                        
        except Exception as e:
            print(f"⚠️ 패키지 생성 실패: {e}")
            
        return str(package_path)

def create_diagnostic_triple(issue_description: str = "") -> str:
    """
    문제 진단용 3종 세트 생성 (원클릭 함수)
    
    Args:
        issue_description: 문제 상황 설명
        
    Returns:
        생성된 진단 패키지 경로
    """
    
    diagnostic = DiagnosticTriple(issue_description)
    diagnostic.collect_diagnostic_set()
    
    package_path = Path(f"diagnostic_package_{diagnostic.diagnostic_id}.zip")
    
    if package_path.exists():
        return str(package_path)
    else:
        return f"diagnostic_report_{diagnostic.diagnostic_id}.json"

def main():
    """진단 3종 세트 시스템 데모"""
    
    print("🔍 **문제 진단 3종 세트 시스템**")
    print("=" * 50)
    print("📋 Gate 결과 + 적용 로그 + 시스템 상태")
    print("➡️ 문제 발생 시 2분 내 원인 파악 가능")
    
    # 시나리오 1: 일반 진단
    print(f"\n🔍 시나리오 1: 일반적인 시스템 진단")
    package1 = create_diagnostic_triple("정기 시스템 점검")
    
    print(f"\n✅ 진단 패키지 생성됨: {package1}")
    
    # 시나리오 2: 문제 상황 진단
    print(f"\n🚨 시나리오 2: 문제 상황 진단")
    package2 = create_diagnostic_triple("사용자 보고: 텍스트 처리 결과 이상")
    
    print(f"\n✅ 문제 진단 패키지 생성됨: {package2}")
    
    # 진단 결과 요약
    print(f"\n📊 **진단 3종 세트 사용법**")
    print("=" * 50)
    print("1️⃣ 문제 발생 시 create_diagnostic_triple() 실행")
    print("2️⃣ 생성된 ZIP 파일을 개발자에게 전달")
    print("3️⃣ 개발자는 3개 파일만 확인:")
    print("   - gate_result.json (검증 통과/실패)")
    print("   - application_log.json (어떤 규칙 적용됐는지)")
    print("   - system_state.json (현재 버전 + 모드)")
    print("4️⃣ 빠른 원인 파악 → 즉시 조치 가능")
    
    print(f"\n✅ **Production 문제 진단 시스템 준비 완료!**")
    
    return True

if __name__ == "__main__":
    main()