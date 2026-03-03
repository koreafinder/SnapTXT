#!/usr/bin/env python3
"""
SnapTXT Production 배포 후 운영 전략 시스템

1. 하루 1번만 ruleset 변경
2. punctuation/space부터 점진적 Standard 승격
3. character는 끝까지 승인제 유지
4. 완전한 운영 로그 추적

첫 1주일 안정화 기간용
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Production 모듈들
from phase_3_0_ruleset_version_manager import get_version_manager
from phase_3_0_production_api import get_production_instance

class OperationStage(Enum):
    """운영 단계"""
    CONSERVATIVE_ONLY = "conservative_only"      # 0-2일: 모든 것 승인제
    PUNCTUATION_AUTO = "punctuation_auto"       # 3-4일: punctuation만 자동
    SPACE_AUTO = "space_auto"                   # 5-6일: punctuation + space 자동
    STANDARD_STABLE = "standard_stable"         # 7일+: standard 모드 안정화

@dataclass
class OperationSchedule:
    """운영 스케줄"""
    deployment_date: str
    current_stage: OperationStage
    stage_start_date: str
    next_stage_date: Optional[str]
    daily_change_allowed: bool
    last_change_date: Optional[str]

@dataclass
class RulePromotionCandidate:
    """규칙 승격 후보"""
    rule_id: str
    rule_type: str  # punctuation, space, character, layout
    current_confidence: float
    validation_status: str
    promotion_readiness: str  # ready, pending, blocked
    promotion_target_stage: OperationStage

class PostDeploymentOperationManager:
    """배포 후 운영 관리자"""
    
    def __init__(self, deployment_date: str = None):
        self.deployment_date = deployment_date or datetime.now().strftime("%Y-%m-%d")
        self.operation_schedule = self._initialize_schedule()
        self.promotion_candidates = []
        
        # 운영 로그 경로
        self.operation_log_path = Path("operation_logs")
        self.operation_log_path.mkdir(exist_ok=True)
        
        self._load_operation_state()
        
    def _initialize_schedule(self) -> OperationSchedule:
        """운영 스케줄 초기화"""
        
        deployment_dt = datetime.strptime(self.deployment_date, "%Y-%m-%d")
        
        return OperationSchedule(
            deployment_date=self.deployment_date,
            current_stage=OperationStage.CONSERVATIVE_ONLY,
            stage_start_date=self.deployment_date,
            next_stage_date=(deployment_dt + timedelta(days=3)).strftime("%Y-%m-%d"),
            daily_change_allowed=True,
            last_change_date=None
        )
        
    def _load_operation_state(self):
        """운영 상태 로드"""
        
        state_file = self.operation_log_path / "operation_state.json"
        
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    
                # Enum 변환
                if "current_stage" in state_data and isinstance(state_data["current_stage"], str):
                    state_data["current_stage"] = OperationStage(state_data["current_stage"])
                    
                self.operation_schedule = OperationSchedule(**state_data)
                
            except Exception as e:
                print(f"⚠️ 운영 상태 로드 실패: {e}")
                
    def _save_operation_state(self):
        """운영 상태 저장"""
        
        state_file = self.operation_log_path / "operation_state.json"
        
        # Enum을 문자열로 변환하여 저장
        state_dict = asdict(self.operation_schedule)
        state_dict["current_stage"] = self.operation_schedule.current_stage.value
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state_dict, f, indent=2, ensure_ascii=False)
            
    def check_daily_change_quota(self) -> Tuple[bool, str]:
        """하루 1번 변경 제한 체크"""
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        if self.operation_schedule.last_change_date == today:
            return False, f"오늘({today}) 이미 변경이 실행됨"
        
        return True, "변경 가능"
        
    def check_stage_progression(self) -> Tuple[bool, OperationStage]:
        """단계 진행 체크"""
        
        today = datetime.now().strftime("%Y-%m-%d")
        next_stage_date = self.operation_schedule.next_stage_date
        
        if next_stage_date and today >= next_stage_date:
            # 다음 단계로 진행 시간
            current_stage = self.operation_schedule.current_stage
            
            if current_stage == OperationStage.CONSERVATIVE_ONLY:
                return True, OperationStage.PUNCTUATION_AUTO
            elif current_stage == OperationStage.PUNCTUATION_AUTO:
                return True, OperationStage.SPACE_AUTO
            elif current_stage == OperationStage.SPACE_AUTO:
                return True, OperationStage.STANDARD_STABLE
            else:
                return False, current_stage  # 이미 마지막 단계
                
        return False, self.operation_schedule.current_stage
        
    def progress_to_next_stage(self, force: bool = False) -> bool:
        """다음 단계로 진행"""
        
        if not force:
            can_progress, next_stage = self.check_stage_progression()
            if not can_progress:
                print(f"⚠️ 단계 진행 불가: 아직 진행 시기 아님")
                return False
        else:
            # 강제 진행
            _, next_stage = self.check_stage_progression()
            
        print(f"📈 단계 진행: {self.operation_schedule.current_stage.value} → {next_stage.value}")
        
        # 스케줄 업데이트
        today = datetime.now().strftime("%Y-%m-%d")
        self.operation_schedule.current_stage = next_stage
        self.operation_schedule.stage_start_date = today
        
        # 다음 전환 일정 설정
        if next_stage == OperationStage.PUNCTUATION_AUTO:
            self.operation_schedule.next_stage_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        elif next_stage == OperationStage.SPACE_AUTO:
            self.operation_schedule.next_stage_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        elif next_stage == OperationStage.STANDARD_STABLE:
            self.operation_schedule.next_stage_date = None  # 마지막 단계
            
        # Production 시스템 모드 변경
        self._apply_stage_settings(next_stage)
        
        # 로그 기록
        self._log_stage_progression(next_stage)
        
        # 상태 저장
        self._save_operation_state()
        
        return True
        
    def _apply_stage_settings(self, stage: OperationStage):
        """단계별 설정 적용"""
        
        try:
            production = get_production_instance()
            
            if stage == OperationStage.CONSERVATIVE_ONLY:
                production.safety_system.current_mode = "conservative"
                print("   🔒 Conservative 모드 설정")
                
            elif stage in [OperationStage.PUNCTUATION_AUTO, OperationStage.SPACE_AUTO]:
                production.safety_system.current_mode = "standard"
                print("   ⚖️ Standard 모드 설정")
                
            elif stage == OperationStage.STANDARD_STABLE:
                production.safety_system.current_mode = "standard"
                print("   ✅ Standard 모드 안정화")
                
        except Exception as e:
            print(f"⚠️ 설정 적용 실패: {e}")
            
    def identify_promotion_candidates(self) -> List[RulePromotionCandidate]:
        """승격 후보 식별"""
        
        candidates = []
        current_stage = self.operation_schedule.current_stage
        
        # 실험 레이어에서 규칙 조회
        try:
            from phase_3_0_rule_isolation import RuleIsolationSystem
            isolation_system = RuleIsolationSystem()
            
            experimental_rules = [rule for rule in isolation_system.rules_registry.values() 
                                 if rule.category.value == "experimental"]
            
            for rule in experimental_rules:
                rule_type = self._extract_rule_type(rule.file_path)
                readiness = self._assess_promotion_readiness(rule, current_stage)
                target_stage = self._determine_target_stage(rule_type)
                
                candidate = RulePromotionCandidate(
                    rule_id=rule.rule_id,
                    rule_type=rule_type,
                    current_confidence=rule.confidence,
                    validation_status=rule.validation_status,
                    promotion_readiness=readiness,
                    promotion_target_stage=target_stage
                )
                
                candidates.append(candidate)
                
        except Exception as e:
            print(f"⚠️ 승격 후보 식별 실패: {e}")
            
        self.promotion_candidates = candidates
        return candidates
        
    def _assess_promotion_readiness(self, rule, current_stage: OperationStage) -> str:
        """승격 준비도 평가"""
        
        # 기본 조건: 신뢰도 0.8 이상
        if rule.confidence < 0.8:
            return "blocked"  # 신뢰도 부족
            
        # 검증 통과 여부
        if rule.validation_status != "passed":
            return "pending"  # 검증 대기
            
        # 단계별 승격 조건
        rule_type = self._extract_rule_type(rule.file_path)
        
        if current_stage == OperationStage.CONSERVATIVE_ONLY:
            return "pending"  # 아직 승격 시기 아님
        elif current_stage == OperationStage.PUNCTUATION_AUTO:
            return "ready" if rule_type == "punctuation" else "pending"
        elif current_stage == OperationStage.SPACE_AUTO:
            return "ready" if rule_type in ["punctuation", "space"] else "pending"
        elif current_stage == OperationStage.STANDARD_STABLE:
            return "ready" if rule_type != "character" else "pending"  # character는 여전히 승인제
            
        return "pending"
        
    def _extract_rule_type(self, file_path: str) -> str:
        """파일 경로에서 규칙 타입 추출"""
        
        path_obj = Path(file_path)
        return path_obj.parent.name  # punctuation, character, space, layout
        
    def _determine_target_stage(self, rule_type: str) -> OperationStage:
        """규칙 타입별 목표 단계 결정"""
        
        if rule_type == "punctuation":
            return OperationStage.PUNCTUATION_AUTO
        elif rule_type == "space":
            return OperationStage.SPACE_AUTO
        elif rule_type in ["layout"]:
            return OperationStage.STANDARD_STABLE
        else:  # character
            return OperationStage.CONSERVATIVE_ONLY  # 계속 승인제
            
    def execute_safe_promotion(self, rule_id: str, reason: str = "") -> bool:
        """안전한 규칙 승격 실행"""
        
        # 일일 변경 제한 체크
        can_change, change_reason = self.check_daily_change_quota()
        if not can_change:
            print(f"❌ 승격 차단: {change_reason}")
            return False
            
        try:
            from phase_3_0_rule_isolation import RuleIsolationSystem
            isolation_system = RuleIsolationSystem()
            
            # 승격 실행
            success = isolation_system.safe_activate_rule(rule_id)
            
            if success:
                # 일일 변경 기록
                today = datetime.now().strftime("%Y-%m-%d")
                self.operation_schedule.last_change_date = today
                self._save_operation_state()
                
                # 승격 로그
                self._log_rule_promotion(rule_id, reason)
                
                print(f"✅ 규칙 승격 완료: {rule_id}")
                return True
            else:
                print(f"❌ 승격 실패: {rule_id}")
                return False
                
        except Exception as e:
            print(f"❌ 승격 오류: {e}")
            return False
            
    def _log_stage_progression(self, new_stage: OperationStage):
        """단계 진행 로그"""
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "STAGE_PROGRESSION",
            "new_stage": new_stage.value,
            "deployment_day": (datetime.now() - datetime.strptime(self.deployment_date, "%Y-%m-%d")).days
        }
        
        log_file = self.operation_log_path / f"stage_progression_{datetime.now().strftime('%Y%m')}.json"
        
        # 기존 로그 읽기
        logs = []
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
                
        logs.append(log_entry)
        
        # 로그 저장
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
            
    def _log_rule_promotion(self, rule_id: str, reason: str):
        """규칙 승격 로그"""
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "RULE_PROMOTION",
            "rule_id": rule_id,
            "reason": reason,
            "current_stage": self.operation_schedule.current_stage.value
        }
        
        log_file = self.operation_log_path / f"rule_promotions_{datetime.now().strftime('%Y%m')}.json"
        
        # 기존 로그 읽기
        logs = []
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
                
        logs.append(log_entry)
        
        # 로그 저장
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
            
    def get_operation_status(self) -> Dict:
        """현재 운영 상태 조회"""
        
        deployment_dt = datetime.strptime(self.deployment_date, "%Y-%m-%d")
        days_since_deployment = (datetime.now() - deployment_dt).days
        
        # 단계 진행 체크
        can_progress, next_stage = self.check_stage_progression()
        
        # 변경 가능 여부 체크
        can_change, change_reason = self.check_daily_change_quota()
        
        return {
            "deployment_date": self.deployment_date,
            "days_since_deployment": days_since_deployment,
            "current_stage": self.operation_schedule.current_stage.value,
            "stage_start_date": self.operation_schedule.stage_start_date,
            "next_stage_date": self.operation_schedule.next_stage_date,
            "can_progress_stage": can_progress,
            "next_stage": next_stage.value if can_progress else None,
            "can_change_today": can_change,
            "change_status": change_reason,
            "last_change_date": self.operation_schedule.last_change_date
        }

def main():
    """배포 후 운영 관리 시스템 데모"""
    
    print("📅 **배포 후 첫 1주일 운영 전략 시스템**")
    print("=" * 50)
    
    # 운영 관리자 초기화 (오늘을 배포일로 가정)
    operation_manager = PostDeploymentOperationManager()
    
    print(f"🚀 배포일: {operation_manager.deployment_date}")
    
    # 1. 현재 운영 상태 확인
    print(f"\n1️⃣ 현재 운영 상태:")
    status = operation_manager.get_operation_status()
    
    print(f"   배포 후 {status['days_since_deployment']}일 경과")
    print(f"   현재 단계: {status['current_stage']}")
    print(f"   오늘 변경 가능: {status['can_change_today']} ({status['change_status']})")
    
    if status['can_progress_stage']:
        print(f"   단계 진행 가능: → {status['next_stage']}")
    
    # 2. 승격 후보 식별
    print(f"\n2️⃣ 승격 후보 식별:")
    candidates = operation_manager.identify_promotion_candidates()
    
    if candidates:
        for candidate in candidates:
            readiness_icon = {"ready": "✅", "pending": "⏳", "blocked": "❌"}[candidate.promotion_readiness]
            print(f"   {readiness_icon} {candidate.rule_id} ({candidate.rule_type})")
            print(f"      신뢰도: {candidate.current_confidence:.2f}, 상태: {candidate.validation_status}")
            print(f"      승격 준비도: {candidate.promotion_readiness}")
    else:
        print(f"   승격 후보 없음")
    
    # 3. 단계 진행 시뮬레이션
    print(f"\n3️⃣ 단계 진행 시뮬레이션:")
    
    if status['can_progress_stage']:
        print(f"   다음 단계로 진행 시도...")
        success = operation_manager.progress_to_next_stage()
        
        if success:
            print(f"   ✅ 단계 진행 성공")
        else:
            print(f"   ❌ 단계 진행 실패")
    else:
        print(f"   아직 단계 진행 시기 아님 (다음 진행일: {status['next_stage_date']})")
    
    # 4. 안전한 승격 시뮬레이션
    print(f"\n4️⃣ 안전한 승격 시뮬레이션:")
    
    ready_candidates = [c for c in candidates if c.promotion_readiness == "ready"]
    
    if ready_candidates and status['can_change_today']:
        target_candidate = ready_candidates[0]
        print(f"   승격 대상: {target_candidate.rule_id}")
        
        # 실제로는 실행하지 않고 시뮬레이션만
        print(f"   승격 시뮬레이션... (실제 실행 안 함)")
        print(f"   ✅ 승격 준비 완료")
    else:
        if not ready_candidates:
            print(f"   승격 준비된 후보 없음")
        if not status['can_change_today']:
            print(f"   오늘 변경 할당량 소진됨")
    
    # 5. 운영 로그 요약
    print(f"\n5️⃣ 운영 로그 현황:")
    
    log_dirs = ["operation_logs"]
    total_events = 0
    
    for log_dir in log_dirs:
        log_path = Path(log_dir)
        if log_path.exists():
            log_files = list(log_path.glob("*.json"))
            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        logs = json.load(f)
                        total_events += len(logs)
                except:
                    pass
    
    print(f"   총 {total_events}개 운영 이벤트 기록됨")
    print(f"   로그 위치: operation_logs/")
    
    print(f"\n" + "=" * 50)
    print(f"✅ **첫 1주일 운영 전략 시스템 가동 중!**")
    print(f"📋 하루 1번 변경 제한 적용")
    print(f"🔄 점진적 단계 승격 (punctuation → space → layout)")
    print(f"🔒 character 규칙은 끝까지 승인제 유지")
    print(f"📊 모든 변경사항 완전 추적")
    
    return True

if __name__ == "__main__":
    main()