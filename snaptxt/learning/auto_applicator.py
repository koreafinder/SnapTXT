#!/usr/bin/env python3
"""
자동 규칙 적용 시스템 - Phase 2.3

실시간 학습으로 생성된 고품질 규칙들을 
기존 stage3_rules.yaml에 자동으로 적용하는 시스템
"""

import yaml
import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

class AutoRuleApplicator:
    """자동 규칙 적용 및 관리 시스템"""
    
    def __init__(self):
        self.stage3_rules_file = Path("../../stage3_rules.yaml")  # 실제 운영 규칙
        self.learned_rules_file = Path("../learning/learning_data/learned_rules.yaml")
        self.feedback_dir = Path("../learning/feedback_data")
        
        self.backup_dir = Path("rule_backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        self.application_log = Path("auto_application.log")
        
        # 자동 적용 설정
        self.auto_apply_threshold = {
            'min_confidence': 0.85,  # 최소 신뢰도
            'min_frequency': 3,      # 최소 발생 빈도
            'min_age_hours': 24      # 최소 24시간 숙성
        }
        
        self.setup_logging()
        
    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.application_log, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def analyze_learned_rules(self) -> Dict:
        """학습된 규칙 분석"""
        if not self.learned_rules_file.exists():
            return {"ready_rules": [], "pending_rules": [], "total": 0}
        
        with open(self.learned_rules_file, 'r', encoding='utf-8') as f:
            learned_data = yaml.safe_load(f) or {}
        
        stage3_rules = learned_data.get('stage3_postprocessing', {})
        ready_rules = []
        pending_rules = []
        
        current_time = datetime.now()
        
        for category in ['spacing', 'characters', 'punctuation', 'formatting']:
            for rule in stage3_rules.get(category, []):
                # 규칙 품질 평가
                confidence = rule.get('confidence', 0)
                frequency = rule.get('frequency', 0)
                learned_at = rule.get('learned_at', '')
                
                # 학습 시간 계산
                age_hours = 0
                if learned_at:
                    try:
                        learned_time = datetime.fromisoformat(learned_at)
                        age_hours = (current_time - learned_time).total_seconds() / 3600
                    except ValueError:
                        age_hours = 0
                
                rule_info = {
                    'category': category,
                    'rule': rule,
                    'confidence': confidence,
                    'frequency': frequency,
                    'age_hours': age_hours,
                    'ready_score': self._calculate_readiness_score(confidence, frequency, age_hours)
                }
                
                # 자동 적용 준비 여부 판단
                if self._is_rule_ready_for_application(confidence, frequency, age_hours):
                    ready_rules.append(rule_info)
                else:
                    pending_rules.append(rule_info)
        
        return {
            "ready_rules": ready_rules,
            "pending_rules": pending_rules, 
            "total": len(ready_rules) + len(pending_rules)
        }
    
    def _calculate_readiness_score(self, confidence: float, frequency: int, age_hours: float) -> float:
        """규칙 준비도 점수 계산"""
        confidence_score = confidence  # 0.0 - 1.0
        frequency_score = min(1.0, frequency / 10.0)  # 빈도 10회면 만점
        age_score = min(1.0, age_hours / 48.0)  # 48시간이면 만점
        
        # 가중 평균 (신뢰도 50%, 빈도 30%, 숙성 20%)
        return (confidence_score * 0.5 + frequency_score * 0.3 + age_score * 0.2)
    
    def _is_rule_ready_for_application(self, confidence: float, frequency: int, age_hours: float) -> bool:
        """규칙이 자동 적용 준비되었는지 판단"""
        return (confidence >= self.auto_apply_threshold['min_confidence'] and
                frequency >= self.auto_apply_threshold['min_frequency'] and
                age_hours >= self.auto_apply_threshold['min_age_hours'])
    
    def backup_current_rules(self) -> str:
        """현재 stage3 규칙 백업"""
        if not self.stage3_rules_file.exists():
            return ""
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"stage3_rules_auto_backup_{timestamp}.yaml"
        
        shutil.copy2(self.stage3_rules_file, backup_file)
        self.logger.info(f"현재 규칙 백업 완료: {backup_file}")
        
        return str(backup_file)
    
    def load_current_stage3_rules(self) -> Dict:
        """현재 stage3 규칙 로드"""
        if not self.stage3_rules_file.exists():
            # 기본 구조 생성
            return {
                'stage3_postprocessing': {
                    'spacing': [],
                    'characters': [],
                    'punctuation': [],
                    'formatting': []
                },
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'auto_application': True
                }
            }
        
        with open(self.stage3_rules_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def apply_ready_rules(self, ready_rules: List[Dict], dry_run: bool = False) -> Dict:
        """준비된 규칙들을 stage3에 적용"""
        if not ready_rules:
            return {"applied": 0, "skipped": 0, "errors": 0, "message": "적용할 규칙 없음"}
        
        # 현재 규칙 로드
        current_rules = self.load_current_stage3_rules()
        
        if 'stage3_postprocessing' not in current_rules:
            current_rules['stage3_postprocessing'] = {
                'spacing': [], 'characters': [], 'punctuation': [], 'formatting': []
            }
        
        stage3_rules = current_rules['stage3_postprocessing']
        
        applied_count = 0
        skipped_count = 0
        error_count = 0
        application_details = []
        
        for rule_info in ready_rules:
            try:
                category = rule_info['category']
                rule = rule_info['rule']
                pattern = rule.get('pattern', '')
                replacement = rule.get('replacement', '')
                
                # 중복 검사
                existing_patterns = [r.get('pattern', '') for r in stage3_rules[category]]
                
                if pattern in existing_patterns:
                    # 기존 규칙 업데이트 (더 높은 신뢰도/빈도면)
                    existing_idx = existing_patterns.index(pattern)
                    existing_rule = stage3_rules[category][existing_idx]
                    
                    if (rule.get('confidence', 0) > existing_rule.get('confidence', 0) or
                        rule.get('frequency', 0) > existing_rule.get('frequency', 0)):
                        
                        if not dry_run:
                            # 메타데이터 추가
                            updated_rule = rule.copy()
                            updated_rule['auto_applied'] = True
                            updated_rule['applied_at'] = datetime.now().isoformat()
                            updated_rule['replaced_rule'] = True
                            
                            stage3_rules[category][existing_idx] = updated_rule
                            
                        applied_count += 1
                        application_details.append({
                            'action': 'updated',
                            'category': category,
                            'pattern': pattern,
                            'confidence': rule.get('confidence', 0),
                            'frequency': rule.get('frequency', 0)
                        })
                        
                        self.logger.info(f"규칙 업데이트: [{category}] {pattern} → {replacement}")
                    else:
                        skipped_count += 1
                        self.logger.info(f"규칙 스킵 (기존 규칙이 더 우수): {pattern}")
                        
                else:
                    # 새 규칙 추가
                    if not dry_run:
                        # 메타데이터 추가
                        new_rule = rule.copy()
                        new_rule['auto_applied'] = True
                        new_rule['applied_at'] = datetime.now().isoformat()
                        new_rule['new_rule'] = True
                        
                        stage3_rules[category].append(new_rule)
                    
                    applied_count += 1
                    application_details.append({
                        'action': 'added',
                        'category': category,
                        'pattern': pattern,
                        'confidence': rule.get('confidence', 0),
                        'frequency': rule.get('frequency', 0)
                    })
                    
                    self.logger.info(f"새 규칙 추가: [{category}] {pattern} → {replacement}")
                    
            except Exception as e:
                error_count += 1
                self.logger.error(f"규칙 적용 오류: {e}")
        
        # 메타데이터 업데이트
        if not dry_run and applied_count > 0:
            current_rules['metadata'] = current_rules.get('metadata', {})
            current_rules['metadata'].update({
                'last_auto_application': datetime.now().isoformat(),
                'auto_applied_rules': applied_count,
                'total_rules': sum(len(stage3_rules[cat]) for cat in stage3_rules),
                'application_version': '2.0'
            })
            
            # 파일 저장
            with open(self.stage3_rules_file, 'w', encoding='utf-8') as f:
                yaml.dump(current_rules, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
                         
            self.logger.info(f"stage3_rules.yaml 업데이트 완료")
        
        result = {
            "applied": applied_count,
            "skipped": skipped_count,
            "errors": error_count,
            "total_processed": len(ready_rules),
            "dry_run": dry_run,
            "details": application_details
        }
        
        return result
    
    def validate_applied_rules(self) -> Dict:
        """적용된 규칙들의 유효성 검증"""
        if not self.stage3_rules_file.exists():
            return {"valid": False, "error": "stage3_rules.yaml 파일 없음"}
        
        try:
            # YAML 문법 검증
            with open(self.stage3_rules_file, 'r', encoding='utf-8') as f:
                rules = yaml.safe_load(f)
            
            # 구조 검증
            if 'stage3_postprocessing' not in rules:
                return {"valid": False, "error": "stage3_postprocessing 섹션 없음"}
            
            stage3 = rules['stage3_postprocessing']
            total_rules = 0
            auto_applied_rules = 0
            validation_errors = []
            
            for category in ['spacing', 'characters', 'punctuation', 'formatting']:
                if category not in stage3:
                    continue
                    
                for i, rule in enumerate(stage3[category]):
                    total_rules += 1
                    
                    # 필수 필드 검증
                    if 'pattern' not in rule or 'replacement' not in rule:
                        validation_errors.append(f"{category}[{i}]: pattern/replacement 필드 누락")
                        continue
                    
                    # 정규식 유효성 검증
                    try:
                        import re
                        re.compile(rule['pattern'])
                    except re.error as e:
                        validation_errors.append(f"{category}[{i}]: 잘못된 정규식 - {e}")
                    
                    # 자동 적용 규칙 카운트
                    if rule.get('auto_applied', False):
                        auto_applied_rules += 1
            
            return {
                "valid": len(validation_errors) == 0,
                "total_rules": total_rules,
                "auto_applied_rules": auto_applied_rules,
                "validation_errors": validation_errors,
                "yaml_valid": True
            }
            
        except yaml.YAMLError as e:
            return {"valid": False, "error": f"YAML 문법 오류: {e}"}
        except Exception as e:
            return {"valid": False, "error": f"검증 오류: {e}"}
    
    def generate_application_report(self, analysis: Dict, application_result: Dict) -> str:
        """자동 적용 리포트 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path(f"auto_application_report_{timestamp}.json")
        
        # 유효성 검증
        validation = self.validate_applied_rules()
        
        report = {
            "report_date": datetime.now().isoformat(),
            "analysis": analysis,
            "application_result": application_result,
            "validation": validation,
            "summary": {
                "total_learned_rules": analysis['total'],
                "ready_for_application": len(analysis['ready_rules']),
                "successfully_applied": application_result['applied'],
                "validation_passed": validation.get('valid', False)
            }
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"자동 적용 리포트 생성: {report_file}")
        return str(report_file)
    
    def run_auto_application(self, dry_run: bool = False) -> Dict:
        """자동 규칙 적용 프로세스 실행"""
        self.logger.info(f"자동 규칙 적용 {'시뮬레이션' if dry_run else '실행'} 시작")
        
        try:
            # 1. 학습된 규칙 분석
            analysis = self.analyze_learned_rules()
            
            if not analysis['ready_rules']:
                return {
                    "success": True,
                    "message": "적용 준비된 규칙이 없습니다",
                    "analysis": analysis
                }
            
            self.logger.info(f"적용 준비된 규칙: {len(analysis['ready_rules'])}개")
            
            # 2. 현재 규칙 백업 (실제 적용 시에만)
            backup_file = ""
            if not dry_run:
                backup_file = self.backup_current_rules()
            
            # 3. 규칙 적용
            application_result = self.apply_ready_rules(analysis['ready_rules'], dry_run)
            
            # 4. 리포트 생성
            report_file = self.generate_application_report(analysis, application_result)
            
            result = {
                "success": True,
                "analysis": analysis,
                "application_result": application_result,
                "backup_file": backup_file,
                "report_file": report_file,
                "dry_run": dry_run
            }
            
            if not dry_run and application_result['applied'] > 0:
                self.logger.info(f"자동 적용 완료: {application_result['applied']}개 규칙 적용")
            
            return result
            
        except Exception as e:
            self.logger.error(f"자동 적용 프로세스 오류: {e}")
            return {
                "success": False,
                "error": str(e)
            }


def main():
    """자동 규칙 적용 시스템 테스트"""
    applicator = AutoRuleApplicator()
    
    print("🔧 자동 규칙 적용 시스템 테스트")
    
    # 1. 시뮬레이션 실행
    print("\n🧪 시뮬레이션 모드 실행...")
    dry_result = applicator.run_auto_application(dry_run=True)
    
    if dry_result['success']:
        analysis = dry_result.get('analysis', {})
        app_result = dry_result.get('application_result', {})
        
        print(f"📊 분석 결과:")
        print(f"   전체 학습된 규칙: {analysis.get('total', 0)}개")
        print(f"   적용 준비 완료: {len(analysis.get('ready_rules', []))}개")
        print(f"   대기 중: {len(analysis.get('pending_rules', []))}개")
        
        if app_result:  # application_result가 있는 경우만 출력
            print(f"\n📝 적용 예상 결과:")
            print(f"   적용될 규칙: {app_result.get('applied', 0)}개")
            print(f"   스킵될 규칙: {app_result.get('skipped', 0)}개")
            print(f"   오류 규칙: {app_result.get('errors', 0)}개")
        else:
            print(f"\n📝 결과: {dry_result.get('message', '처리할 규칙이 없습니다')}")
        
        # 실제 적용 여부 확인
        if analysis.get('ready_rules', []):
            print(f"\n🤔 실제 적용하시겠습니까? (y/n): ", end="")
            # 테스트에서는 자동으로 'n'
            choice = 'n'
            print(choice)
            
            if choice.lower() == 'y':
                print(f"\n🚀 실제 적용 실행...")
                real_result = applicator.run_auto_application(dry_run=False)
                
                if real_result['success']:
                    print(f"✅ 자동 적용 완료!")
                    print(f"   백업 파일: {real_result.get('backup_file', 'N/A')}")
                    print(f"   리포트: {real_result.get('report_file', 'N/A')}")
                else:
                    print(f"❌ 적용 실패: {real_result.get('error', 'Unknown')}")
            else:
                print(f"⏸️ 실제 적용을 건너뜁니다")
        else:
            print(f"\n⏸️ 적용할 규칙이 없습니다")
    else:
        print(f"❌ 시뮬레이션 실패: {dry_result.get('error', 'Unknown')}")
    
    print(f"\n✅ 자동 규칙 적용 시스템 테스트 완료")


if __name__ == "__main__":
    main()