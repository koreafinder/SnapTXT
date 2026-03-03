#!/usr/bin/env python3
"""
Phase 3.0 실험 레이어 디스크 격리 시스템

폴더 구조 강제 분리:
/rules/active/     - 운영에서 사용되는 활성 규칙
/rules/experimental/  - 실험 중인 규칙 (보류된 3개 클러스터 포함)  
/rules/blocked/    - 차단된 규칙 (FP 높음, 재현성 낮음 등)

실수로 섞일 확률 원천 차단
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

class RuleCategory(Enum):
    """규칙 카테고리"""
    ACTIVE = "active"
    EXPERIMENTAL = "experimental"
    BLOCKED = "blocked"

@dataclass
class IsolatedRule:
    """격리된 규칙"""
    rule_id: str
    pattern: str
    category: RuleCategory
    confidence: float
    validation_status: str
    performance_metrics: Dict[str, float]
    isolation_reason: str
    created_at: str
    last_moved: str
    file_path: str

class RuleIsolationSystem:
    """규칙 격리 시스템"""
    
    def __init__(self, base_path: str = "rules_isolated"):
        # 절대경로로 통일 (CWD 차이 방지)
        if Path(base_path).is_absolute():
            self.base_path = Path(base_path)
        else:
            self.base_path = Path(__file__).parent / base_path
            
        print(f"🔍 규칙 격리 시스템 초기화: {self.base_path.absolute()}")
        self._setup_directory_structure()
        
        self.rules_registry: Dict[str, IsolatedRule] = {}
        self._load_existing_rules()
        
    def _setup_directory_structure(self):
        """디렉토리 구조 생성"""
        
        # 기본 구조 생성
        self.active_dir = self.base_path / "active"
        self.experimental_dir = self.base_path / "experimental"
        self.blocked_dir = self.base_path / "blocked"
        
        # 각 카테고리별 하위 폴더
        for main_dir in [self.active_dir, self.experimental_dir, self.blocked_dir]:
            main_dir.mkdir(parents=True, exist_ok=True)
            
            # 타입별 하위 폴더
            (main_dir / "punctuation").mkdir(exist_ok=True)
            (main_dir / "character").mkdir(exist_ok=True)
            (main_dir / "layout").mkdir(exist_ok=True)
            (main_dir / "space").mkdir(exist_ok=True)
            
        # 메타데이터 폴더
        (self.base_path / "metadata").mkdir(exist_ok=True)
        (self.base_path / "migration_logs").mkdir(exist_ok=True)
        
        print(f"📁 격리 디렉토리 구조 생성: {self.base_path}")
        
    def _load_existing_rules(self):
        """기존 규칙 로드"""
        
        for category in RuleCategory:
            category_dir = self.base_path / category.value
            
            if not category_dir.exists():
                continue
                
            # 각 타입별 폴더에서 규칙 파일 검색
            for rule_file in category_dir.rglob("*.json"):
                try:
                    with open(rule_file, 'r', encoding='utf-8') as f:
                        rule_data = json.load(f)
                        
                    # category 문자열을 Enum으로 변환
                    if "category" in rule_data and isinstance(rule_data["category"], str):
                        rule_data["category"] = RuleCategory(rule_data["category"])
                        
                    rule = IsolatedRule(**rule_data)
                    self.rules_registry[rule.rule_id] = rule
                    
                except Exception as e:
                    print(f"⚠️ 규칙 로드 실패: {rule_file} - {e}")
                    
    def isolate_rule(self, rule_id: str, pattern: str, rule_type: str,
                    category: RuleCategory, confidence: float,
                    validation_status: str, performance_metrics: Dict[str, float],
                    isolation_reason: str) -> bool:
        """규칙을 해당 카테고리로 격리"""
        
        print(f"🔒 규칙 격리: {rule_id} → {category.value}")
        
        # 규칙 객체 생성
        isolated_rule = IsolatedRule(
            rule_id=rule_id,
            pattern=pattern,
            category=category,
            confidence=confidence,
            validation_status=validation_status,
            performance_metrics=performance_metrics,
            isolation_reason=isolation_reason,
            created_at=datetime.now().isoformat(),
            last_moved=datetime.now().isoformat(),
            file_path=""  # 아래에서 설정
        )
        
        # 저장 경로 결정
        target_dir = self.base_path / category.value / rule_type
        rule_filename = f"{rule_id}.json"
        rule_filepath = target_dir / rule_filename
        
        isolated_rule.file_path = str(rule_filepath)
        
        # 파일 저장
        # Enum을 문자열로 변환하여 저장
        rule_dict = asdict(isolated_rule)
        rule_dict["category"] = isolated_rule.category.value
        
        with open(rule_filepath, 'w', encoding='utf-8') as f:
            json.dump(rule_dict, f, indent=2, ensure_ascii=False)
            
        # 레지스트리 업데이트
        self.rules_registry[rule_id] = isolated_rule
        
        # 이동 로그 기록
        self._log_isolation(isolated_rule)
        
        print(f"   저장 위치: {rule_filepath}")
        print(f"   격리 사유: {isolation_reason}")
        
        return True
        
    def migrate_rule(self, rule_id: str, new_category: RuleCategory, reason: str) -> bool:
        """규칙을 다른 카테고리로 이동"""
        
        if rule_id not in self.rules_registry:
            print(f"❌ 규칙 {rule_id} 찾을 수 없음")
            return False
            
        current_rule = self.rules_registry[rule_id]
        old_category = current_rule.category
        
        print(f"📦 규칙 이동: {rule_id}")
        print(f"   {old_category.value} → {new_category.value}")
        
        # 기존 파일 삭제
        old_file = Path(current_rule.file_path)
        if old_file.exists():
            old_file.unlink()
            
        # 새 위치에 저장
        rule_type = self._get_rule_type_from_path(current_rule.file_path)
        new_dir = self.base_path / new_category.value / rule_type
        new_filepath = new_dir / f"{rule_id}.json"
        
        # 규칙 정보 업데이트
        current_rule.category = new_category
        current_rule.last_moved = datetime.now().isoformat()
        current_rule.isolation_reason = f"{current_rule.isolation_reason} | Migrated: {reason}"
        current_rule.file_path = str(new_filepath)
        
        # 새 파일 저장
        # Enum을 문자열로 변환하여 저장
        rule_dict = asdict(current_rule)
        rule_dict["category"] = current_rule.category.value
        
        with open(new_filepath, 'w', encoding='utf-8') as f:
            json.dump(rule_dict, f, indent=2, ensure_ascii=False)
            
        # 이동 로그
        self._log_migration(rule_id, old_category, new_category, reason)
        
        print(f"   ✅ 이동 완료: {new_filepath}")
        
        return True
        
    def get_category_summary(self) -> Dict[str, Dict]:
        """카테고리별 규칙 현황"""
        
        summary = {
            "active": {"count": 0, "rules": [], "avg_confidence": 0.0},
            "experimental": {"count": 0, "rules": [], "avg_confidence": 0.0},
            "blocked": {"count": 0, "rules": [], "avg_confidence": 0.0}
        }
        
        for rule in self.rules_registry.values():
            category_key = rule.category.value
            summary[category_key]["count"] += 1
            summary[category_key]["rules"].append({
                "rule_id": rule.rule_id,
                "pattern": rule.pattern[:50] + "..." if len(rule.pattern) > 50 else rule.pattern,
                "confidence": rule.confidence,
                "status": rule.validation_status
            })
            
        # 평균 신뢰도 계산
        for category_key in summary:
            if summary[category_key]["count"] > 0:
                total_confidence = sum(r["confidence"] for r in summary[category_key]["rules"])
                summary[category_key]["avg_confidence"] = total_confidence / summary[category_key]["count"]
                
        return summary
        
    def audit_isolation_integrity(self) -> Tuple[bool, List[str]]:
        """격리 무결성 감사"""
        
        issues = []
        
        print(f"🔍 격리 무결성 감사 시작...")
        
        # 1. 파일 시스템 vs 레지스트리 일치성 검사
        for rule_id, rule in self.rules_registry.items():
            file_path = Path(rule.file_path)
            
            if not file_path.exists():
                issues.append(f"Missing file: {rule_id} - {file_path}")
                
            # 카테고리 폴더와 실제 카테고리 일치성
            expected_category = rule.category.value
            actual_category = file_path.parent.parent.name
            
            if expected_category != actual_category:
                issues.append(f"Category mismatch: {rule_id} - expected {expected_category}, found {actual_category}")
                
        # 2. 고아 파일 검사 (레지스트리에 없는 파일)
        for category in RuleCategory:
            category_dir = self.base_path / category.value
            
            for rule_file in category_dir.rglob("*.json"):
                rule_id = rule_file.stem
                
                if rule_id not in self.rules_registry:
                    issues.append(f"Orphaned file: {rule_file}")
                    
        # 3. 활성 규칙 신뢰도 검사
        for rule in self.rules_registry.values():
            if rule.category == RuleCategory.ACTIVE and rule.confidence < 0.8:
                issues.append(f"Low confidence active rule: {rule.rule_id} - {rule.confidence}")
                
        integrity_ok = len(issues) == 0
        
        print(f"   검사 완료: {'✅ OK' if integrity_ok else f'❌ {len(issues)}개 문제'}")
        
        return integrity_ok, issues
        
    def safe_activate_rule(self, rule_id: str) -> bool:
        """안전한 규칙 활성화 (experimental → active)"""
        
        if rule_id not in self.rules_registry:
            print(f"❌ 규칙 {rule_id} 존재하지 않음")
            return False
            
        rule = self.rules_registry[rule_id]
        
        if rule.category != RuleCategory.EXPERIMENTAL:
            print(f"❌ 규칙 {rule_id}는 실험 상태가 아님 (현재: {rule.category.value})")
            return False
            
        # 활성화 조건 검사
        if rule.confidence < 0.8:
            print(f"❌ 신뢰도 부족: {rule.confidence} < 0.8")
            return False
            
        if rule.validation_status != "passed":
            print(f"❌ 검증 미통과: {rule.validation_status}")
            return False
            
        # experimental → active 이동
        return self.migrate_rule(rule_id, RuleCategory.ACTIVE, "Validated and ready for production")
        
    def emergency_block_rule(self, rule_id: str, reason: str) -> bool:
        """긴급 규칙 차단 (active → blocked)"""
        
        if rule_id not in self.rules_registry:
            print(f"❌ 규칙 {rule_id} 존재하지 않음")
            return False
            
        rule = self.rules_registry[rule_id]
        
        print(f"🚨 긴급 규칙 차단: {rule_id}")
        print(f"   사유: {reason}")
        
        # 어떤 상태에서든 blocked로 이동 가능
        return self.migrate_rule(rule_id, RuleCategory.BLOCKED, f"EMERGENCY BLOCK: {reason}")
        
    def _get_rule_type_from_path(self, file_path: str) -> str:
        """파일 경로에서 규칙 타입 추출"""
        
        path_obj = Path(file_path)
        return path_obj.parent.name
        
    def _log_isolation(self, rule: IsolatedRule):
        """격리 로그 기록"""
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "ISOLATE",
            "rule_id": rule.rule_id,
            "category": rule.category.value,
            "reason": rule.isolation_reason,
            "file_path": rule.file_path
        }
        
        log_file = self.base_path / "migration_logs" / f"isolation_{datetime.now().strftime('%Y%m%d')}.json"
        
        # 기존 로그 읽기
        logs = []
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
                
        logs.append(log_entry)
        
        # 로그 저장
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
            
    def _log_migration(self, rule_id: str, from_category: RuleCategory, 
                      to_category: RuleCategory, reason: str):
        """이동 로그 기록"""
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "MIGRATE",
            "rule_id": rule_id,
            "from_category": from_category.value,
            "to_category": to_category.value,
            "reason": reason
        }
        
        log_file = self.base_path / "migration_logs" / f"migration_{datetime.now().strftime('%Y%m%d')}.json"
        
        # 기존 로그 읽기
        logs = []
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
                
        logs.append(log_entry)
        
        # 로그 저장
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

def init_phase3_isolated_rules():
    """Phase 3.0에서 보류된 클러스터들을 실험 레이어로 격리"""
    
    isolation_system = RuleIsolationSystem()
    
    # 보류된 3개 클러스터를 실험 상태로 격리
    experimental_rules = [
        {
            "rule_id": "character_cluster_001",
            "pattern": "빈발 문자 치환 규칙 (재현성 0.000)",
            "rule_type": "character",
            "confidence": 0.45,
            "validation_status": "failed_reproducibility",
            "performance_metrics": {"delta_cer": -0.008, "fp_rate": 0.25, "reproducibility": 0.000},
            "isolation_reason": "낮은 재현성으로 인한 실험 격리 (Phase 2.4 results)"
        },
        {
            "rule_id": "layout_cluster_001", 
            "pattern": "레이아웃 최적화 규칙 (재현성 0.307)",
            "rule_type": "layout",
            "confidence": 0.62,
            "validation_status": "failed_reproducibility", 
            "performance_metrics": {"delta_cer": -0.003, "fp_rate": 0.15, "reproducibility": 0.307},
            "isolation_reason": "부족한 재현성으로 인한 실험 격리"
        },
        {
            "rule_id": "mixed_cluster_001",
            "pattern": "혼합 패턴 규칙 (재현성 0.669)",
            "rule_type": "character",
            "confidence": 0.73,
            "validation_status": "pending_validation",
            "performance_metrics": {"delta_cer": -0.005, "fp_rate": 0.12, "reproducibility": 0.669},
            "isolation_reason": "재현성 임계치 미달 (< 0.7) - 추가 데이터 대기"
        }
    ]
    
    # 검증된 안정 규칙
    active_rules = [
        {
            "rule_id": "punctuation_normalizer_validated",
            "pattern": "표준 인용부호 정규화 (검증완료)",
            "rule_type": "punctuation", 
            "confidence": 0.95,
            "validation_status": "passed",
            "performance_metrics": {"delta_cer": -0.003, "fp_rate": 0.02, "reproducibility": 0.848},
            "isolation_reason": "held-out 검증 통과, 운영 배포 승인"
        }
    ]
    
    # 차단된 위험 규칙  
    blocked_rules = [
        {
            "rule_id": "aggressive_char_substitution",
            "pattern": "적극적 문자 치환 (위험)",
            "rule_type": "character",
            "confidence": 0.65,
            "validation_status": "blocked_high_fp",
            "performance_metrics": {"delta_cer": -0.010, "fp_rate": 0.35, "reproducibility": 0.201},
            "isolation_reason": "높은 False Positive rate (35%) - 운영 위험"
        }
    ]
    
    # 실험 레이어로 격리
    for rule in experimental_rules:
        isolation_system.isolate_rule(
            rule_id=rule["rule_id"],
            pattern=rule["pattern"],
            rule_type=rule["rule_type"],
            category=RuleCategory.EXPERIMENTAL,
            confidence=rule["confidence"],
            validation_status=rule["validation_status"],
            performance_metrics=rule["performance_metrics"],
            isolation_reason=rule["isolation_reason"]
        )
        
    # 활성 규칙으로 격리
    for rule in active_rules:
        isolation_system.isolate_rule(
            rule_id=rule["rule_id"],
            pattern=rule["pattern"],
            rule_type=rule["rule_type"],
            category=RuleCategory.ACTIVE,
            confidence=rule["confidence"],
            validation_status=rule["validation_status"],
            performance_metrics=rule["performance_metrics"],
            isolation_reason=rule["isolation_reason"]
        )
        
    # 차단 규칙으로 격리
    for rule in blocked_rules:
        isolation_system.isolate_rule(
            rule_id=rule["rule_id"],
            pattern=rule["pattern"],
            rule_type=rule["rule_type"],
            category=RuleCategory.BLOCKED,
            confidence=rule["confidence"],
            validation_status=rule["validation_status"],
            performance_metrics=rule["performance_metrics"],
            isolation_reason=rule["isolation_reason"]
        )
    
    return isolation_system

def main():
    """실험 레이어 디스크 격리 시스템 데모"""
    
    print("🗂️ **실험 레이어 디스크 격리 시스템**")
    print("=" * 45)
    print("📁 /rules/active/ - 운영 승인된 규칙")
    print("📁 /rules/experimental/ - 보류된 실험 규칙")
    print("📁 /rules/blocked/ - 차단된 위험 규칙")
    
    # 1. 초기화 및 규칙 격리
    print(f"\n1️⃣ Phase 3.0 규칙 격리 초기화:")
    
    isolation_system = init_phase3_isolated_rules()
    
    # 2. 카테고리별 현황
    print(f"\n2️⃣ 카테고리별 현황:")
    
    summary = isolation_system.get_category_summary()
    
    for category, info in summary.items():
        print(f"   📂 {category.upper()}: {info['count']}개 규칙 (평균 신뢰도: {info['avg_confidence']:.2f})")
        for rule in info['rules'][:2]:  # 최대 2개만 표시
            print(f"      - {rule['rule_id']}: {rule['pattern'][:40]}... (신뢰도: {rule['confidence']})")
            
    # 3. 안전 작업 데모
    print(f"\n3️⃣ 안전 작업 데모:")
    
    # 실험 → 활성 이동 시도 (실패 예상)
    print(f"   실험 규칙 활성화 시도:")
    success = isolation_system.safe_activate_rule("mixed_cluster_001")
    if not success:
        print(f"     ❌ 조건 미충족으로 실패 (예상됨)")
        
    # 활성 → 차단 이동 (긴급 상황 시뮬레이션)
    print(f"\n   긴급 규칙 차단 테스트:")
    isolation_system.emergency_block_rule(
        "punctuation_normalizer_validated", 
        "운영에서 예상치 못한 부작용 발견"
    )
    
    # 4. 무결성 감사
    print(f"\n4️⃣ 무결성 감사:")
    
    integrity_ok, issues = isolation_system.audit_isolation_integrity()
    
    if integrity_ok:
        print(f"   ✅ 격리 무결성 OK")
    else:
        print(f"   ⚠️ {len(issues)}개 문제 발견:")
        for issue in issues[:3]:  # 최대 3개만 표시
            print(f"      - {issue}")
            
    # 5. 최종 상태
    print(f"\n5️⃣ 최종 격리 상태:")
    
    final_summary = isolation_system.get_category_summary()
    
    for category, info in final_summary.items():
        icon = {"active": "🟢", "experimental": "🟡", "blocked": "🔴"}[category]
        print(f"   {icon} {category}: {info['count']}개")
        
    # 6. 파일 구조 확인
    print(f"\n📁 생성된 디렉토리 구조:")
    
    base_path = Path("rules_isolated")
    
    for root, dirs, files in os.walk(base_path):
        level = root.replace(str(base_path), '').count(os.sep)
        indent = ' ' * 2 * level
        folder_name = os.path.basename(root) or "rules_isolated"
        print(f"{indent}{folder_name}/")
        
        if len(files) > 0:
            sub_indent = ' ' * 2 * (level + 1)
            for file in files[:2]:  # 최대 2개 파일만 표시
                print(f"{sub_indent}{file}")
            if len(files) > 2:
                print(f"{sub_indent}... (+{len(files)-2} more)")
                
    print(f"\n" + "=" * 45)
    print(f"✅ **실험 레이어 디스크 격리 완료!**")
    print(f"🗂️ 물리적 폴더 분리로 혼합 방지")
    print(f"🔒 카테고리별 안전 장치 적용")  
    print(f"📊 완전한 이동 이력 추적")
    print(f"🔍 자동 무결성 감사 시스템")
    
    return True

if __name__ == "__main__":
    main()