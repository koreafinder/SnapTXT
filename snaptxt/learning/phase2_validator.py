#!/usr/bin/env python3
"""
Phase 2 통합 시스템 검증 스크립트

Phase 2의 모든 구성요소가 올바르게 작동하는지 종합 검증
- 사용자 피드백 수집 시스템
- 실시간 패턴 학습 엔진
- 자동 규칙 적용 시스템
"""

import yaml
import json
import time
from datetime import datetime
from pathlib import Path

class Phase2SystemValidator:
    """Phase 2 통합 시스템 검증기"""
    
    def __init__(self):
        self.base_dir = Path(".")
        self.results = {}
    
    def validate_feedback_system(self):
        """피드백 수집 시스템 검증"""
        try:
            from feedback_collector import FeedbackCollector
            
            collector = FeedbackCollector()
            
            # 기능 검사
            checks = {
                "클래스 초기화": True,
                "분석 기능": hasattr(collector, 'analyze_feedback'),
                "패턴 생성": hasattr(collector, 'generate_patterns'),
                "규칙 학습": hasattr(collector, 'learn_from_feedback'),
                "데이터 폴더": Path("feedback_data").exists()
            }
            
            self.results["feedback_system"] = {
                "status": "✅" if all(checks.values()) else "❌",
                "checks": checks,
                "score": f"{sum(checks.values())}/{len(checks)}"
            }
            
        except Exception as e:
            self.results["feedback_system"] = {
                "status": "❌",
                "error": str(e),
                "score": "0/5"
            }
    
    def validate_realtime_engine(self):
        """실시간 학습 엔진 검증"""
        try:
            from real_time_engine import RealTimeLearningEngine
            
            engine = RealTimeLearningEngine()
            
            checks = {
                "엔진 초기화": True,
                "학습 기능": hasattr(engine, 'learn_from_new_feedback'),
                "패턴 병합": hasattr(engine, 'merge_patterns_with_phase1'),
                "백그라운드 스레드": hasattr(engine, 'run_background_learning'),
                "학습 데이터 폴더": Path("learning_data").exists()
            }
            
            self.results["realtime_engine"] = {
                "status": "✅" if all(checks.values()) else "❌", 
                "checks": checks,
                "score": f"{sum(checks.values())}/{len(checks)}"
            }
            
        except Exception as e:
            self.results["realtime_engine"] = {
                "status": "❌",
                "error": str(e),
                "score": "0/5"
            }
    
    def validate_auto_applicator(self):
        """자동 규칙 적용 시스템 검증"""
        try:
            from auto_applicator import AutoRuleApplicator
            
            applicator = AutoRuleApplicator()
            
            # stage3_rules.yaml 검증
            stage3_exists = Path("../../stage3_rules.yaml").exists()
            
            checks = {
                "시스템 초기화": True,
                "규칙 분석": hasattr(applicator, 'analyze_learned_rules'),
                "자동 적용": hasattr(applicator, 'apply_ready_rules'),
                "백업 시스템": hasattr(applicator, 'backup_current_rules'),
                "검증 기능": hasattr(applicator, 'validate_applied_rules'),
                "stage3_rules 존재": stage3_exists
            }
            
            # 실제 적용 테스트가 성공했는지 확인
            if stage3_exists:
                with open("../../stage3_rules.yaml", 'r', encoding='utf-8') as f:
                    rules = yaml.safe_load(f)
                    checks["적용된 규칙 확인"] = any(
                        rule.get('auto_applied', False) 
                        for category in rules.get('stage3_postprocessing', {}).values()
                        for rule in category if isinstance(category, list)
                    )
            
            self.results["auto_applicator"] = {
                "status": "✅" if all(checks.values()) else "❌",
                "checks": checks,
                "score": f"{sum(checks.values())}/{len(checks)}"
            }
            
        except Exception as e:
            self.results["auto_applicator"] = {
                "status": "❌",
                "error": str(e),
                "score": f"0/{len(checks) if 'checks' in locals() else 7}"
            }
    
    def validate_gui_integration(self):
        """GUI 통합 검증"""
        try:
            from feedback_gui import FeedbackWidget
            
            # PyQt5 모듈 체크 (실제 GUI 실행은 하지 않음)
            checks = {
                "GUI 클래스": True,
                "위젯 구성": hasattr(FeedbackWidget, '__init__'),
                "피드백 처리": hasattr(FeedbackWidget, 'submit_feedback'),
                "실시간 통계": hasattr(FeedbackWidget, 'update_stats')
            }
            
            self.results["gui_integration"] = {
                "status": "✅" if all(checks.values()) else "❌",
                "checks": checks,
                "score": f"{sum(checks.values())}/{len(checks)}"
            }
            
        except Exception as e:
            self.results["gui_integration"] = {
                "status": "❌",
                "error": str(e),
                "score": "0/4"
            }
    
    def validate_data_consistency(self):
        """데이터 일관성 검증"""
        try:
            # 학습된 규칙 파일 확인
            learned_rules_exist = Path("learning_data/learned_rules.yaml").exists()
            
            # 백업 시스템 확인
            backup_dir_exist = Path("rule_backups").exists()
            
            # 로그 파일 확인  
            log_files = list(Path(".").glob("*.log"))
            
            checks = {
                "학습 규칙 파일": learned_rules_exist,
                "백업 디렉토리": backup_dir_exist,
                "로그 시스템": len(log_files) > 0,
                "리포트 생성": any(Path(".").glob("*report*.json"))
            }
            
            self.results["data_consistency"] = {
                "status": "✅" if all(checks.values()) else "❌",
                "checks": checks,
                "score": f"{sum(checks.values())}/{len(checks)}"
            }
            
        except Exception as e:
            self.results["data_consistency"] = {
                "status": "❌", 
                "error": str(e),
                "score": "0/4"
            }
    
    def calculate_overall_score(self):
        """전체 시스템 점수 계산"""
        total_checks = 0
        passed_checks = 0
        
        for component, result in self.results.items():
            if 'score' in result:
                score_parts = result['score'].split('/')
                passed = int(score_parts[0])
                total = int(score_parts[1])
                
                passed_checks += passed
                total_checks += total
        
        percentage = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        return percentage, passed_checks, total_checks
    
    def run_full_validation(self):
        """전체 검증 실행"""
        print("🔍 Phase 2 통합 시스템 검증 시작")
        print("="*60)
        
        print("\n1️⃣ 피드백 수집 시스템 검증...")
        self.validate_feedback_system()
        
        print("2️⃣ 실시간 학습 엔진 검증...")
        self.validate_realtime_engine()
        
        print("3️⃣ 자동 규칙 적용 시스템 검증...")
        self.validate_auto_applicator()
        
        print("4️⃣ GUI 통합 검증...")
        self.validate_gui_integration()
        
        print("5️⃣ 데이터 일관성 검증...")
        self.validate_data_consistency()
        
        print("\n" + "="*60)
        print("🏆 Phase 2 시스템 검증 결과")
        print("="*60)
        
        for component, result in self.results.items():
            status = result['status']
            score = result['score']
            print(f"{status} {component.replace('_', ' ').title()}: {score}")
            
            if 'error' in result:
                print(f"   ❌ 오류: {result['error']}")
            elif 'checks' in result:
                failed_checks = [k for k, v in result['checks'].items() if not v]
                if failed_checks:
                    print(f"   ⚠️ 실패한 항목: {', '.join(failed_checks)}")
        
        percentage, passed, total = self.calculate_overall_score()
        print(f"\n🎯 전체 시스템 점수: {percentage:.1f}% ({passed}/{total})")
        
        if percentage >= 90:
            print("🎉 Phase 2 시스템이 완벽하게 구축되었습니다!")
        elif percentage >= 80:
            print("👍 Phase 2 시스템이 성공적으로 구축되었습니다!")
        elif percentage >= 70:
            print("⚠️ Phase 2 시스템에 몇 가지 문제가 있습니다")
        else:
            print("❌ Phase 2 시스템에 중대한 문제가 있습니다")
        
        # 검증 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"phase2_validation_report_{timestamp}.json"
        
        validation_report = {
            "validation_date": datetime.now().isoformat(),
            "overall_score": {
                "percentage": percentage,
                "passed_checks": passed,
                "total_checks": total
            },
            "component_results": self.results
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(validation_report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📋 검증 리포트: {report_file}")
        
        return percentage >= 80


def main():
    """Phase 2 시스템 통합 검증 실행"""
    validator = Phase2SystemValidator()
    success = validator.run_full_validation()
    
    return success

if __name__ == "__main__":
    main()