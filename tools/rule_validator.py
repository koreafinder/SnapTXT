#!/usr/bin/env python3
"""
규칙 검증 및 테스트 시스템 - Phase 1.3
생성된 YAML 규칙의 정확성 검증 및 성능 테스트

Usage:
    python tools/rule_validator.py --test-rules stage3_rules.yaml
    python tools/rule_validator.py --benchmark
    python tools/rule_validator.py --validate-all
"""

import re
import yaml
import json
import time
from typing import Dict, List, Tuple, Any
from pathlib import Path
import argparse

class RuleValidator:
    """YAML 규칙 검증 및 테스트"""
    
    def __init__(self, rules_file: str = "stage3_rules.yaml"):
        self.rules_file = Path(rules_file)
        self.rules = self.load_rules()
        
    def load_rules(self) -> Dict:
        """YAML 규칙 파일 로드"""
        if not self.rules_file.exists():
            print(f"❌ 규칙 파일이 없습니다: {self.rules_file}")
            return {}
            
        with open(self.rules_file, 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f)
            
        stage3 = rules.get('stage3_postprocessing', {})
        total_rules = sum(len(stage3.get(category, [])) for category in ['spacing', 'characters', 'punctuation', 'formatting'])
        
        print(f"✅ 규칙 로드됨: {total_rules}개 규칙")
        return rules
    
    def create_test_cases(self) -> List[Dict]:
        """테스트 케이스 생성"""
        test_cases = [
            # 자동 생성된 규칙 테스트
            {
                "input": "마이 클 싱 어의 책을 읽었습니다.",
                "expected": "마이클 싱어의 책을 읽었습니다.",
                "rule_type": "spacing",
                "description": "인명 분리 오류 수정"
            },
            {
                "input": "명 상 가처럼 살고 싶습니다.",
                "expected": "명상가처럼 살고 싶습니다.",
                "rule_type": "spacing",
                "description": "명사 분리 오류 수정"
            },
            {
                "input": "그것이 드러워습니다.",
                "expected": "그것이 드러났습니다.",
                "rule_type": "characters",
                "description": "어미 오인식 수정"
            },
            {
                "input": "깊이 돌두했습니다.",
                "expected": "깊이 몰두했습니다.",
                "rule_type": "characters",
                "description": "초성 오인식 수정"
            },
            # 복잡한 케이스들
            {
                "input": "마이 클 싱 어는 유명한 명 상 가입니다.",
                "expected": "마이클 싱어는 유명한 명상가입니다.",
                "rule_type": "mixed",
                "description": "복합 오류 수정"
            },
            {
                "input": "연구에 돌두했습니다. 결과가 드러워습니다.",
                "expected": "연구에 몰두했습니다. 결과가 드러났습니다.",
                "rule_type": "mixed",
                "description": "다중 문장 수정"
            },
            # 부정적 테스트 (수정되지 말아야 하는 경우)
            {
                "input": "정상적인 텍스트입니다.",
                "expected": "정상적인 텍스트입니다.",
                "rule_type": "negative",
                "description": "정상 텍스트는 변경되지 않아야 함"
            }
        ]
        
        return test_cases
    
    def apply_stage3_rules(self, text: str) -> str:
        """Stage3 규칙 적용 (실제 snaptxt 모듈을 시뮬레이션)"""
        result = text
        applied_rules = []
        
        stage3_rules = self.rules.get('stage3_postprocessing', {})
        
        for category in ['spacing', 'characters', 'punctuation', 'formatting']:
            rules_in_category = stage3_rules.get(category, [])
            
            for rule in rules_in_category:
                pattern = rule.get('pattern', '')
                replacement = rule.get('replacement', '')
                
                if pattern and replacement:
                    # 정규식 플래그 설정
                    old_result = result
                    result = re.sub(pattern, replacement, result)
                    
                    if result != old_result:
                        applied_rules.append({
                            "category": category,
                            "pattern": pattern,
                            "replacement": replacement,
                            "description": rule.get('description', '')
                        })
        
        return result, applied_rules
    
    def run_test_case(self, test_case: Dict) -> Dict:
        """개별 테스트 케이스 실행"""
        input_text = test_case['input']
        expected = test_case['expected']
        
        start_time = time.time()
        actual, applied_rules = self.apply_stage3_rules(input_text)
        duration = time.time() - start_time
        
        passed = (actual == expected)
        
        result = {
            "input": input_text,
            "expected": expected,
            "actual": actual,
            "passed": passed,
            "duration": duration,
            "applied_rules": applied_rules,
            "rule_type": test_case.get('rule_type', ''),
            "description": test_case.get('description', '')
        }
        
        return result
    
    def run_all_tests(self) -> Dict:
        """모든 테스트 케이스 실행"""
        test_cases = self.create_test_cases()
        results = []
        
        print("🧪 규칙 검증 테스트 실행...")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"   테스트 {i}/{len(test_cases)}: {test_case['description']}")
            result = self.run_test_case(test_case)
            results.append(result)
            
            # 결과 출력
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"      {status} ({result['duration']:.4f}초)")
            if not result['passed']:
                print(f"      예상: {result['expected']}")
                print(f"      실제: {result['actual']}")
            if result['applied_rules']:
                print(f"      적용된 규칙: {len(result['applied_rules'])}개")
        
        # 전체 결과 집계
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r['passed'])
        failed_tests = total_tests - passed_tests
        
        summary = {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "pass_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "avg_duration": sum(r['duration'] for r in results) / total_tests if total_tests > 0 else 0,
            "test_results": results
        }
        
        print(f"\n📊 테스트 결과 요약:")
        print(f"   전체 테스트: {total_tests}개")
        print(f"   통과: {passed_tests}개")
        print(f"   실패: {failed_tests}개") 
        print(f"   통과율: {summary['pass_rate']:.1%}")
        print(f"   평균 처리 시간: {summary['avg_duration']:.4f}초")
        
        return summary
    
    def benchmark_performance(self, iterations: int = 100) -> Dict:
        """성능 벤치마크"""
        test_text = "마이 클 싱 어는 유명한 명 상 가입니다. 그의 연구에 돌두했습니다. 결과가 드러워습니다."
        
        print(f"⚡ 성능 벤치마크 ({iterations}회 반복)...")
        
        times = []
        rule_applications = []
        
        for i in range(iterations):
            start_time = time.time()
            result, applied_rules = self.apply_stage3_rules(test_text)
            duration = time.time() - start_time
            
            times.append(duration)
            rule_applications.append(len(applied_rules))
        
        benchmark = {
            "iterations": iterations,
            "avg_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times),
            "total_time": sum(times),
            "avg_rules_applied": sum(rule_applications) / len(rule_applications),
            "chars_per_second": len(test_text) * iterations / sum(times),
            "text_length": len(test_text)
        }
        
        print(f"   평균 처리 시간: {benchmark['avg_time']:.6f}초")
        print(f"   최소/최대 시간: {benchmark['min_time']:.6f}초 / {benchmark['max_time']:.6f}초")
        print(f"   처리 속도: {benchmark['chars_per_second']:.0f} 자/초")
        print(f"   평균 규칙 적용: {benchmark['avg_rules_applied']:.1f}개")
        
        return benchmark
    
    def validate_rule_syntax(self) -> List[Dict]:
        """규칙 문법 유효성 검사"""
        issues = []
        stage3_rules = self.rules.get('stage3_postprocessing', {})
        
        print("🔍 규칙 문법 검증...")
        
        for category, rules_list in stage3_rules.items():
            for i, rule in enumerate(rules_list):
                rule_id = f"{category}[{i}]"
                
                # 필수 필드 확인
                if 'pattern' not in rule:
                    issues.append({
                        "rule_id": rule_id,
                        "severity": "error",
                        "message": "pattern 필드 누락"
                    })
                    continue
                
                if 'replacement' not in rule:
                    issues.append({
                        "rule_id": rule_id,
                        "severity": "error", 
                        "message": "replacement 필드 누락"
                    })
                    continue
                
                # 정규식 패턴 유효성 확인
                try:
                    re.compile(rule['pattern'])
                except re.error as e:
                    issues.append({
                        "rule_id": rule_id,
                        "severity": "error",
                        "message": f"잘못된 정규식 패턴: {e}"
                    })
                
                # 선택적 필드 확인
                if 'description' not in rule:
                    issues.append({
                        "rule_id": rule_id,
                        "severity": "warning",
                        "message": "description 필드 권장"
                    })
        
        if issues:
            print(f"⚠️  발견된 문제: {len(issues)}개")
            for issue in issues[:5]:  # 최대 5개까지 출력
                print(f"   [{issue['severity']}] {issue['rule_id']}: {issue['message']}")
        else:
            print("✅ 모든 규칙이 유효합니다")
        
        return issues
    
    def generate_validation_report(self, test_results: Dict, benchmark: Dict, syntax_issues: List[Dict]) -> str:
        """검증 리포트 생성"""
        report = {
            "validation_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "rules_file": str(self.rules_file),
            "test_summary": {
                "total_tests": test_results["total_tests"],
                "passed": test_results["passed"],
                "failed": test_results["failed"],
                "pass_rate": test_results["pass_rate"]
            },
            "performance": {
                "avg_processing_time": benchmark["avg_time"],
                "processing_speed_chars_per_sec": benchmark["chars_per_second"],
                "avg_rules_applied": benchmark["avg_rules_applied"]
            },
            "syntax_validation": {
                "total_issues": len(syntax_issues),
                "errors": len([i for i in syntax_issues if i['severity'] == 'error']),
                "warnings": len([i for i in syntax_issues if i['severity'] == 'warning'])
            },
            "overall_status": "PASS" if test_results["failed"] == 0 and 
                             len([i for i in syntax_issues if i['severity'] == 'error']) == 0
                             else "FAIL",
            "detailed_results": {
                "test_cases": test_results["test_results"],
                "benchmark_data": benchmark,
                "syntax_issues": syntax_issues
            }
        }
        
        report_file = f"reports/rule_validation_report_{int(time.time())}.json"
        Path("reports").mkdir(exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 검증 리포트 저장: {report_file}")
        return report_file
    
    def run_full_validation(self) -> Dict:
        """전체 검증 프로세스 실행"""
        print("🔧 규칙 검증 프로세스 시작...")
        
        # 1. 문법 검증
        syntax_issues = self.validate_rule_syntax()
        
        # 2. 기능 테스트
        test_results = self.run_all_tests()
        
        # 3. 성능 벤치마크
        benchmark = self.benchmark_performance(50)
        
        # 4. 리포트 생성
        report_file = self.generate_validation_report(test_results, benchmark, syntax_issues)
        
        result = {
            "success": test_results["failed"] == 0 and len([i for i in syntax_issues if i['severity'] == 'error']) == 0,
            "test_results": test_results,
            "benchmark": benchmark,
            "syntax_issues": syntax_issues,
            "report_file": report_file
        }
        
        print(f"\n✅ 검증 완료!")
        print(f"   결과: {'성공' if result['success'] else '실패'}")
        print(f"   리포트: {report_file}")
        
        return result


def main():
    parser = argparse.ArgumentParser(description="SnapTXT 규칙 검증기")
    parser.add_argument("--test-rules", default="stage3_rules.yaml", help="테스트할 규칙 파일")
    parser.add_argument("--benchmark", action="store_true", help="성능 벤치마크만 실행")
    parser.add_argument("--validate-all", action="store_true", help="전체 검증 실행")
    parser.add_argument("--iterations", type=int, default=50, help="벤치마크 반복 횟수")
    
    args = parser.parse_args()
    
    validator = RuleValidator(args.test_rules)
    
    if args.benchmark:
        return validator.benchmark_performance(args.iterations)
    elif args.validate_all or not any(vars(args).values()):
        return validator.run_full_validation()
    else:
        return validator.run_all_tests()


if __name__ == "__main__":
    main()