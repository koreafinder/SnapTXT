#!/usr/bin/env python3
"""
Phase 3.0 RuleSet 버전 관리 + 원클릭 롤백 시스템

activate_ruleset(version_id)
rollback_last()

"버전 교체"는 무조건 이 경로로만 - 품질 무너짐 방지
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

class RulesetStatus(Enum):
    """RuleSet 상태"""
    ACTIVE = "active"
    STANDBY = "standby" 
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"

@dataclass
class RuleSetVersion:
    """버전화된 RuleSet"""
    version_id: str
    name: str
    description: str
    rules: Dict[str, Dict]
    created_at: str
    created_by: str
    status: RulesetStatus
    validation_report: Optional[Dict] = None
    performance_metrics: Optional[Dict] = None
    hash_signature: str = ""

@dataclass
class RollbackPoint:
    """롤백 지점"""
    rollback_id: str
    from_version: str
    to_version: str
    timestamp: str
    reason: str
    backup_path: str

class RuleSetVersionManager:
    """RuleSet 버전 관리자"""
    
    def __init__(self, storage_path: str = "ruleset_storage"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # 디렉토리 구조 생성
        (self.storage_path / "versions").mkdir(exist_ok=True)
        (self.storage_path / "backups").mkdir(exist_ok=True)
        (self.storage_path / "rollback_logs").mkdir(exist_ok=True)
        
        self.versions: Dict[str, RuleSetVersion] = {}
        self.rollback_history: List[RollbackPoint] = []
        self.current_active_version: Optional[str] = None
        
        # 초기 데이터 로드
        self._load_existing_versions()
        self._initialize_default_rulesets()
        
    def _load_existing_versions(self):
        """기존 버전들 로드"""
        
        versions_dir = self.storage_path / "versions"
        
        for version_file in versions_dir.glob("ruleset_v*.json"):
            try:
                with open(version_file, 'r', encoding='utf-8') as f:
                    version_data = json.load(f)
                    
                # status 문자열을 Enum으로 변환
                if "status" in version_data and isinstance(version_data["status"], str):
                    version_data["status"] = RulesetStatus(version_data["status"])
                    
                version = RuleSetVersion(**version_data)
                self.versions[version.version_id] = version
                
                if version.status == RulesetStatus.ACTIVE:
                    self.current_active_version = version.version_id
                    
            except Exception as e:
                print(f"⚠️ 버전 로드 실패: {version_file} - {e}")
                
    def _initialize_default_rulesets(self):
        """기본 RuleSet 초기화"""
        
        if not self.versions:  # 처음 실행 시에만
            self._create_initial_rulesets()
            
    def _create_initial_rulesets(self):
        """초기 RuleSet 생성"""
        
        # Stable 버전 (검증된 규칙들)
        stable_rules = {
            "punctuation_normalizer_v1": {
                "pattern": "비표준 인용부호 → 표준 인용부호", 
                "category": "punctuation",
                "confidence": 0.95,
                "delta_cer_avg": -0.003,
                "validation_status": "passed"
            },
            "space_cleaner_v1": {
                "pattern": "중복 공백 정리",
                "category": "space", 
                "confidence": 0.98,
                "delta_cer_avg": -0.001,
                "validation_status": "passed"
            }
        }
        
        stable_version = self.create_new_version(
            name="Stable Baseline",
            description="검증된 안정적인 규칙 세트",
            rules=stable_rules,
            created_by="system"
        )
        
        # 활성화
        self.activate_ruleset(stable_version, "초기 안정 버전 활성화")
        
        # Experimental 버전
        experimental_rules = {
            **stable_rules,
            "aggressive_corrector_v1": {
                "pattern": "적극적 오타 교정",
                "category": "character",
                "confidence": 0.75,
                "delta_cer_avg": -0.008,
                "validation_status": "experimental"
            },
            "layout_optimizer_v1": {
                "pattern": "레이아웃 최적화", 
                "category": "layout",
                "confidence": 0.68,
                "delta_cer_avg": -0.002,
                "validation_status": "experimental"
            }
        }
        
        experimental_version = self.create_new_version(
            name="Experimental Advanced",
            description="실험적 고급 규칙 포함",
            rules=experimental_rules,
            created_by="system"
        )
        
        self.versions[experimental_version].status = RulesetStatus.EXPERIMENTAL
        
    def create_new_version(self, name: str, description: str, rules: Dict[str, Dict], 
                          created_by: str) -> str:
        """새 RuleSet 버전 생성"""
        
        # 버전 ID 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_id = f"v{len(self.versions) + 1:03d}_{timestamp}"
        
        # 해시 서명 생성 (변조 감지용)
        content_hash = hashlib.sha256(
            json.dumps(rules, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        # 버전 객체 생성
        new_version = RuleSetVersion(
            version_id=version_id,
            name=name,
            description=description,
            rules=rules,
            created_at=datetime.now().isoformat(),
            created_by=created_by,
            status=RulesetStatus.STANDBY,
            hash_signature=content_hash
        )
        
        # 저장
        self.versions[version_id] = new_version
        self._save_version(new_version)
        
        print(f"📦 새 RuleSet 버전 생성: {version_id} ({name})")
        print(f"   규칙 수: {len(rules)}개")
        print(f"   해시: {content_hash}")
        
        return version_id
        
    def activate_ruleset(self, version_id: str, reason: str = "") -> bool:
        """RuleSet 버전 활성화 (원클릭 전환)"""
        
        if version_id not in self.versions:
            print(f"❌ 버전 {version_id} 존재하지 않음")
            return False
            
        target_version = self.versions[version_id]
        
        print(f"🔄 RuleSet 활성화: {version_id} ({target_version.name})")
        
        # 1. 현재 활성 버전 백업
        old_version_id = None
        if self.current_active_version:
            old_version_id = self.current_active_version
            old_version = self.versions[self.current_active_version]
            
            # 백업 생성
            backup_path = self._create_backup(old_version)
            print(f"   백업 생성: {backup_path}")
            
            # 상태 변경
            old_version.status = RulesetStatus.STANDBY
            
        # 2. 새 버전 활성화
        target_version.status = RulesetStatus.ACTIVE
        self.current_active_version = version_id
        
        # 3. 롤백 지점 생성
        rollback_point = RollbackPoint(
            rollback_id=f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            from_version=old_version_id or "none",
            to_version=version_id,
            timestamp=datetime.now().isoformat(),
            reason=reason,
            backup_path=backup_path if old_version_id else ""
        )
        
        self.rollback_history.append(rollback_point)
        
        # 4. 변경사항 저장
        if old_version_id:
            self._save_version(self.versions[old_version_id])
        self._save_version(target_version)
        self._save_rollback_log(rollback_point)
        self._save_system_state()
        
        print(f"✅ RuleSet 활성화 완료: {version_id}")
        print(f"   이전: {old_version_id} → 현재: {version_id}")
        print(f"   롤백 가능: rollback_last()")
        
        return True
        
    def rollback_last(self, reason: str = "") -> bool:
        """마지막 변경 롤백 (원클릭 롤백)"""
        
        if not self.rollback_history:
            print(f"❌ 롤백 가능한 이력 없음")
            return False
            
        last_rollback = self.rollback_history[-1]
        
        if last_rollback.from_version == "none":
            print(f"❌ 초기 상태로는 롤백 불가")
            return False
            
        print(f"🔙 마지막 변경 롤백 시작")
        print(f"   {last_rollback.to_version} → {last_rollback.from_version}")
        
        # 1. 이전 버전으로 복원
        success = self.activate_ruleset(
            last_rollback.from_version, 
            f"Rollback: {reason if reason else 'User requested rollback'}"
        )
        
        if success:
            print(f"✅ 롤백 완료")
            print(f"   복원된 버전: {last_rollback.from_version}")
        else:
            print(f"❌ 롤백 실패")
            
        return success
        
    def get_version_status(self) -> Dict:
        """현재 버전 상태 조회"""
        
        status = {
            "current_active": self.current_active_version,
            "total_versions": len(self.versions),
            "rollback_available": len(self.rollback_history) > 0,
            "versions": {}
        }
        
        for version_id, version in self.versions.items():
            status["versions"][version_id] = {
                "name": version.name,
                "status": version.status.value,
                "rule_count": len(version.rules),
                "created_at": version.created_at,
                "hash": version.hash_signature
            }
            
        return status
    
    def list_available_versions(self) -> List[Dict]:
        """사용 가능한 버전 목록"""
        
        versions_list = []
        
        for version_id, version in self.versions.items():
            version_info = {
                "version_id": version_id,
                "name": version.name,
                "description": version.description,
                "rule_count": len(version.rules), 
                "status": version.status.value,
                "created_at": version.created_at,
                "is_active": version_id == self.current_active_version
            }
            
            versions_list.append(version_info)
            
        # 활성 → Standby → 기타 순으로 정렬
        versions_list.sort(key=lambda x: (
            0 if x["is_active"] else 1,  # 활성 버전 우선
            1 if x["status"] == "standby" else 2,  # Standby 다음
            -datetime.fromisoformat(x["created_at"]).timestamp()  # 최신순
        ))
            
        return versions_list
        
    def verify_version_integrity(self, version_id: str) -> Tuple[bool, str]:
        """버전 무결성 검증"""
        
        if version_id not in self.versions:
            return False, f"Version {version_id} not found"
            
        version = self.versions[version_id]
        
        # 해시 재계산
        current_hash = hashlib.sha256(
            json.dumps(version.rules, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        if current_hash != version.hash_signature:
            return False, f"Hash mismatch: expected {version.hash_signature}, got {current_hash}"
            
        return True, "Integrity verified"
        
    def _create_backup(self, version: RuleSetVersion) -> str:
        """버전 백업 생성"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{version.version_id}_{timestamp}.json"
        backup_path = self.storage_path / "backups" / backup_filename
        
        # Enum을 문자열로 변환하여 백업
        version_dict = asdict(version)
        version_dict["status"] = version.status.value
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(version_dict, f, indent=2, ensure_ascii=False)
            
        return str(backup_path)
        
    def _save_version(self, version: RuleSetVersion):
        """버전 저장"""
        
        version_file = self.storage_path / "versions" / f"ruleset_{version.version_id}.json"
        
        # Enum을 문자열로 변환하여 저장
        version_dict = asdict(version)
        version_dict["status"] = version.status.value
        
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(version_dict, f, indent=2, ensure_ascii=False)
            
    def _save_rollback_log(self, rollback_point: RollbackPoint):
        """롤백 로그 저장"""
        
        log_file = self.storage_path / "rollback_logs" / f"{rollback_point.rollback_id}.json"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(rollback_point), f, indent=2, ensure_ascii=False)
            
    def _save_system_state(self):
        """시스템 전체 상태 저장"""
        
        state = {
            "current_active_version": self.current_active_version,
            "last_updated": datetime.now().isoformat(),
            "rollback_history": [asdict(rp) for rp in self.rollback_history[-10:]]  # 최근 10개만
        }
        
        state_file = self.storage_path / "system_state.json"
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

# 간편 API 함수들 (원클릭 운영)
_version_manager_instance = None

def get_version_manager() -> RuleSetVersionManager:
    """버전 관리자 인스턴스 (싱글톤)"""
    global _version_manager_instance
    
    if _version_manager_instance is None:
        _version_manager_instance = RuleSetVersionManager()
        
    return _version_manager_instance

def activate_ruleset(version_id: str, reason: str = "") -> bool:
    """
    RuleSet 버전 활성화 (원클릭 API)
    
    사용 예시:
        activate_ruleset("v002_20260304_120000", "성능 개선 버전 적용")
    """
    manager = get_version_manager()
    return manager.activate_ruleset(version_id, reason)

def rollback_last(reason: str = "") -> bool:
    """
    마지막 변경 롤백 (원클릭 API)
    
    사용 예시:
        rollback_last("문제 발생으로 인한 긴급 롤백")
    """
    manager = get_version_manager()
    return manager.rollback_last(reason)

def list_versions() -> List[Dict]:
    """사용 가능한 버전 목록 조회"""
    manager = get_version_manager()
    return manager.list_available_versions()

def get_current_version() -> Optional[str]:
    """현재 활성 버전 조회"""
    manager = get_version_manager()
    return manager.current_active_version

def main():
    """RuleSet 버전 관리 데모"""
    
    print("📦 **RuleSet 버전 관리 + 롤백 시스템**")
    print("=" * 45)
    
    # 1. 초기 상태 확인
    print("1️⃣ 초기 상태:")
    versions = list_versions()
    current = get_current_version()
    
    print(f"   현재 활성 버전: {current}")
    print(f"   사용 가능한 버전: {len(versions)}개")
    
    for version in versions:
        status_icon = "🟢" if version["is_active"] else "⚪"
        print(f"     {status_icon} {version['version_id']}: {version['name']} ({version['rule_count']}개 규칙)")
    
    # 2. 새 버전 생성 
    print(f"\n2️⃣ 새 버전 생성:")
    
    manager = get_version_manager()
    
    enhanced_rules = {
        "punctuation_normalizer_v2": {
            "pattern": "향상된 인용부호 정규화",
            "category": "punctuation", 
            "confidence": 0.97,
            "delta_cer_avg": -0.004
        },
        "smart_corrector_v1": {
            "pattern": "스마트 오타 교정",
            "category": "character",
            "confidence": 0.88,
            "delta_cer_avg": -0.006
        },
        "space_cleaner_v2": {
            "pattern": "고급 공백 정리",
            "category": "space",
            "confidence": 0.99,
            "delta_cer_avg": -0.002
        }
    }
    
    new_version_id = manager.create_new_version(
        name="Enhanced v2.0",
        description="향상된 규칙과 스마트 교정 추가",
        rules=enhanced_rules,
        created_by="developer"
    )
    
    # 3. 버전 활성화 테스트
    print(f"\n3️⃣ 버전 활성화:")
    
    success = activate_ruleset(new_version_id, "Enhanced 버전 배포")
    
    if success:
        print(f"   ✅ {new_version_id} 활성화 성공")
        print(f"   현재 활성: {get_current_version()}")
    
    # 4. 롤백 테스트
    print(f"\n4️⃣ 롤백 테스트:")
    
    rollback_success = rollback_last("테스트 목적 롤백")
    
    if rollback_success:
        print(f"   ✅ 롤백 성공") 
        print(f"   현재 활성: {get_current_version()}")
    
    # 5. 무결성 검증
    print(f"\n5️⃣ 무결성 검증:")
    
    for version in list(manager.versions.keys())[:3]:  # 최근 3개만
        integrity_ok, message = manager.verify_version_integrity(version)
        status_icon = "✅" if integrity_ok else "❌"
        print(f"   {status_icon} {version}: {message}")
    
    # 6. 시스템 상태 조회  
    print(f"\n6️⃣ 시스템 상태:")
    
    status = manager.get_version_status()
    print(f"   총 버전: {status['total_versions']}개")
    print(f"   활성 버전: {status['current_active']}")
    print(f"   롤백 가능: {'Yes' if status['rollback_available'] else 'No'}")
    
    print(f"\n📁 저장된 파일:")
    print(f"   버전: ruleset_storage/versions/")
    print(f"   백업: ruleset_storage/backups/") 
    print(f"   로그: ruleset_storage/rollback_logs/")
    
    print(f"\n" + "=" * 45)
    print(f"✅ **RuleSet 버전 관리 시스템 완료!**")
    print(f"🔄 원클릭 버전 전환: activate_ruleset()")
    print(f"🔙 원클릭 롤백: rollback_last()")
    print(f"🔒 무결성 검증 + 백업 보장")
    print(f"📋 완전한 변경 이력 추적")
    
    return True

if __name__ == "__main__":
    main()