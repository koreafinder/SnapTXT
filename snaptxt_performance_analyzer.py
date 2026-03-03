"""
SnapTXT Performance Analysis System
실제 OCR 오류 수정 성능 향상을 위한 종합 분석 도구

목표: "엔지니어 검증 통과" → "실제 사용자 체감 품질 개선"
전략: 오류 유형 분석 → 규칙 생성 → 효과 측정 루프
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict, Counter
import difflib
from dataclasses import dataclass
import yaml


@dataclass
class OCRError:
    """OCR 오류 정보"""
    original: str
    corrected: str
    error_type: str
    frequency: int
    confidence: float
    context: str


@dataclass
class RuleEffectiveness:
    """규칙 효과성 정보"""
    rule_id: str
    category: str
    applications: int
    actual_changes: int
    effectiveness_ratio: float
    rule_type: str  # Dead/Cosmetic/Effective


class SnapTXTPerformanceAnalyzer:
    """SnapTXT 성능 분석기"""
    
    def __init__(self):
        self.reports_dir = Path("production_reports")
        self.rules_dir = Path("rules_isolated/active")
        self.output_dir = Path("performance_analysis")
        self.output_dir.mkdir(exist_ok=True)
        
        self.active_rules = self._load_current_rules()
        
    def run_comprehensive_analysis(self):
        """종합 성능 분석 실행"""
        print("🔍 SnapTXT 성능 종합 분석 시작...")
        print("="*70)
        
        # 1. 25% 개선률 원인 분해
        improvement_analysis = self._analyze_improvement_causes()
        
        # 2. 현재 활성 규칙 분류
        rule_classification = self._classify_active_rules()
        
        # 3. 가짜 개선 분석
        fake_improvement_analysis = self._analyze_fake_improvements()
        
        # 4. 폴백률 상세 분석
        fallback_analysis = self._analyze_fallback_patterns()
        
        # 5. 현재 상태 객관적 평가
        current_state_assessment = self._assess_current_state()
        
        # 6. OCR 오류 유형 클러스터링
        ocr_error_clustering = self._analyze_ocr_error_patterns()
        
        # 종합 리포트 생성
        comprehensive_report = {
            "timestamp": datetime.now().isoformat(),
            "analysis_type": "comprehensive_performance",
            "improvement_causes": improvement_analysis,
            "rule_classification": rule_classification,
            "fake_improvement_analysis": fake_improvement_analysis,
            "fallback_analysis": fallback_analysis,
            "current_state": current_state_assessment,
            "ocr_error_patterns": ocr_error_clustering,
            "action_plan": self._generate_action_plan()
        }
        
        # 리포트 저장
        report_file = self.output_dir / f"comprehensive_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(comprehensive_report, f, ensure_ascii=False, indent=2)
        
        # 사용자 친화적 출력
        self._print_analysis_results(comprehensive_report, report_file)
        
        return comprehensive_report
    
    def _load_current_rules(self) -> Dict:
        """현재 활성 규칙 로드"""
        rules = {}
        
        if not self.rules_dir.exists():
            return rules
            
        for rule_file in self.rules_dir.rglob("*.json"):
            try:
                with open(rule_file, 'r', encoding='utf-8') as f:
                    rule_data = json.load(f)
                    
                rule_id = rule_data.get("rule_id", rule_file.stem)
                rules[rule_id] = rule_data
                
            except Exception as e:
                print(f"⚠️ 규칙 로드 실패: {rule_file.name} - {e}")
                
        return rules
    
    def _analyze_improvement_causes(self) -> Dict:
        """25% 개선률 원인 정량 분해"""
        print("📊 1️⃣ 개선률 원인 분해 분석...")
        
        # 리포트 수집
        reports = self._collect_recent_processing_reports()
        
        if not reports:
            return {"error": "분석할 리포트가 없음"}
        
        # 원인별 분석
        total_pages = len(reports)
        rules_applied_pages = 0
        actual_change_pages = 0
        conservative_blocked_pages = 0
        cosmetic_only_pages = 0
        
        rule_applications = Counter()
        
        for report in reports:
            result = report.get("result", {})
            context = report.get("context", {})
            
            applied_rules = result.get("applied_rules", [])
            original = result.get("original_text", "")
            fixed = result.get("fixed_text", "")
            
            # 규칙 적용 카운트
            if applied_rules:
                rules_applied_pages += 1
                for rule in applied_rules:
                    rule_id = rule.get("rule_id", "unknown")
                    rule_applications[rule_id] += 1
            
            # 실제 변화 확인
            if original != fixed:
                actual_change_pages += 1
                
                # 변화 타입 분석
                change_significance = self._analyze_change_significance(original, fixed)
                if change_significance == "cosmetic":
                    cosmetic_only_pages += 1
            
            # Conservative 모드 차단 확인
            if context.get("safety_mode") == "conservative":
                conservative_blocked_pages += 1
        
        # 원인 분해 계산
        rule_coverage_issue = (total_pages - rules_applied_pages) / total_pages * 100
        conservative_blocking_issue = conservative_blocked_pages / total_pages * 100
        cosmetic_rule_issue = cosmetic_only_pages / total_pages * 100
        implementation_gap = (rules_applied_pages - actual_change_pages) / total_pages * 100
        
        return {
            "total_pages_analyzed": total_pages,
            "current_improvement_rate": round(actual_change_pages / total_pages * 100, 1),
            "cause_breakdown": {
                "rule_coverage_gap": round(rule_coverage_issue, 1),
                "conservative_blocking": round(conservative_blocking_issue, 1),
                "cosmetic_rule_dominance": round(cosmetic_rule_issue, 1),
                "implementation_gap": round(implementation_gap, 1)
            },
            "rule_application_frequency": dict(rule_applications.most_common()),
            "diagnosis": self._diagnose_improvement_bottleneck(
                rule_coverage_issue, conservative_blocking_issue, 
                cosmetic_rule_issue, implementation_gap
            )
        }
    
    def _classify_active_rules(self) -> Dict:
        """현재 활성 규칙 분류 (Dead/Cosmetic/Effective)"""
        print("📋 2️⃣ 활성 규칙 분류 분석...")
        
        # 리포트에서 실제 적용 결과 수집
        reports = self._collect_recent_processing_reports()
        rule_performance = defaultdict(lambda: {
            "applications": 0,
            "actual_changes": 0,
            "character_changes": [],
            "improvement_types": []
        })
        
        for report in reports:
            result = report.get("result", {})
            applied_rules = result.get("applied_rules", [])
            original = result.get("original_text", "")
            fixed = result.get("fixed_text", "")
            
            for rule in applied_rules:
                rule_id = rule.get("rule_id", "unknown")
                rule_performance[rule_id]["applications"] += 1
                
                if original != fixed:
                    rule_performance[rule_id]["actual_changes"] += 1
                    char_diff = len(fixed) - len(original)
                    rule_performance[rule_id]["character_changes"].append(char_diff)
                    
                    improvement_type = self._analyze_change_significance(original, fixed)
                    rule_performance[rule_id]["improvement_types"].append(improvement_type)
        
        # 규칙 분류
        classified_rules = {
            "dead_rules": [],
            "cosmetic_rules": [],
            "effective_rules": []
        }
        
        for rule_id, rule_info in self.active_rules.items():
            perf = rule_performance.get(rule_id, {"applications": 0, "actual_changes": 0})
            
            if perf["applications"] == 0:
                # 적용된 적 없음 = Dead
                classified_rules["dead_rules"].append({
                    "rule_id": rule_id,
                    "pattern": rule_info.get("pattern", ""),
                    "reason": "적용 기록 없음"
                })
            elif perf["actual_changes"] == 0:
                # 적용되었지만 변화 없음 = Dead
                classified_rules["dead_rules"].append({
                    "rule_id": rule_id,
                    "pattern": rule_info.get("pattern", ""),
                    "reason": "텍스트 변화 없음",
                    "applications": perf["applications"]
                })
            else:
                effectiveness = perf["actual_changes"] / perf["applications"]
                avg_char_change = sum(perf["character_changes"]) / len(perf["character_changes"]) if perf["character_changes"] else 0
                improvement_types = Counter(perf["improvement_types"])
                
                if effectiveness < 0.3 or abs(avg_char_change) < 1:
                    # 효과성 낮음 또는 미미한 변화 = Cosmetic
                    classified_rules["cosmetic_rules"].append({
                        "rule_id": rule_id,
                        "pattern": rule_info.get("pattern", ""),
                        "effectiveness": round(effectiveness, 2),
                        "avg_char_change": round(avg_char_change, 1),
                        "applications": perf["applications"],
                        "dominant_type": improvement_types.most_common(1)[0][0] if improvement_types else "unknown"
                    })
                else:
                    # 명확한 효과 = Effective
                    classified_rules["effective_rules"].append({
                        "rule_id": rule_id,
                        "pattern": rule_info.get("pattern", ""),
                        "effectiveness": round(effectiveness, 2),
                        "avg_char_change": round(avg_char_change, 1),
                        "applications": perf["applications"],
                        "dominant_type": improvement_types.most_common(1)[0][0] if improvement_types else "unknown"
                    })
        
        # 비율 계산
        total_rules = len(self.active_rules)
        effective_ratio = len(classified_rules["effective_rules"]) / total_rules * 100 if total_rules > 0 else 0
        
        return {
            "total_active_rules": total_rules,
            "classification": classified_rules,
            "ratios": {
                "dead_ratio": round(len(classified_rules["dead_rules"]) / total_rules * 100, 1) if total_rules > 0 else 0,
                "cosmetic_ratio": round(len(classified_rules["cosmetic_rules"]) / total_rules * 100, 1) if total_rules > 0 else 0,
                "effective_ratio": round(effective_ratio, 1)
            },
            "improvement_strategies": self._generate_rule_improvement_strategies(effective_ratio)
        }
    
    def _analyze_fake_improvements(self) -> Dict:
        """가짜 개선 현상 분석"""
        print("🎭 3️⃣ 가짜 개선 현상 분석...")
        
        reports = self._collect_recent_processing_reports()
        
        fake_improvement_cases = []
        for i, report in enumerate(reports):
            result = report.get("result", {})
            applied_rules = result.get("applied_rules", [])
            original = result.get("original_text", "")
            fixed = result.get("fixed_text", "")
            
            # 규칙 적용되었지만 텍스트 변화 없음 = 가짜 개선
            if applied_rules and original == fixed:
                fake_improvement_cases.append({
                    "report_index": i,
                    "applied_rules": [rule.get("rule_id", "") for rule in applied_rules],
                    "text_sample": original[:100],
                    "suspected_cause": self._diagnose_fake_improvement_cause(applied_rules, original)
                })
        
        return {
            "total_fake_cases": len(fake_improvement_cases),
            "fake_improvement_rate": round(len(fake_improvement_cases) / len(reports) * 100, 1) if reports else 0,
            "fake_cases_sample": fake_improvement_cases[:5],  # 상위 5개 사례
            "elimination_strategy": {
                "diff_based_filtering": "실행 전후 char-level diff 검증",
                "minimum_change_threshold": "최소 1자 이상 변화 요구",
                "semantic_improvement_priority": "의미 단위 교정 우선도 부여"
            }
        }
    
    def _analyze_fallback_patterns(self) -> Dict:
        """폴백 패턴 상세 분석"""
        print("⚠️ 4️⃣ 폴백 패턴 분석...")
        
        # Production reports + approval requests 모두 분석
        all_files = list(self.reports_dir.glob("*.json")) if self.reports_dir.exists() else []
        
        fallback_causes = {
            "conservative_mode": 0,
            "gate_blocking": 0,
            "rule_loading_failure": 0,
            "exception_handling": 0
        }
        
        total_processed = 0
        
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # approval_request = Conservative 모드 폴백
                if "approval_request" in file_path.name:
                    fallback_causes["conservative_mode"] += 1
                
                # processing_report에서 context 확인
                elif "processing_report" in file_path.name:
                    total_processed += 1
                    context = data.get("context", {})
                    
                    if context.get("safety_mode") == "conservative":
                        fallback_causes["conservative_mode"] += 1
                
                # gate_evaluation = 게이트 차단
                elif "gate_evaluation" in file_path.name:
                    fallback_causes["gate_blocking"] += 1
                    
            except Exception as e:
                fallback_causes["exception_handling"] += 1
        
        total_operations = total_processed + sum(fallback_causes.values())
        current_fallback_rate = sum(fallback_causes.values()) / total_operations * 100 if total_operations > 0 else 0
        
        return {
            "current_fallback_rate": round(current_fallback_rate, 1),
            "fallback_breakdown": fallback_causes,
            "target_fallback_rate": 10.0,
            "reduction_required": round(current_fallback_rate - 10.0, 1),
            "specific_actions": self._generate_fallback_reduction_actions(fallback_causes, current_fallback_rate)
        }
    
    def _assess_current_state(self) -> Dict:
        """객관적 현재 상태 평가 (A/B/C/D 등급)"""
        print("🎯 5️⃣ 현재 상태 객관적 평가...")
        
        # 핵심 지표 수집
        reports = self._collect_recent_processing_reports()
        
        if not reports:
            return {"grade": "A", "reason": "분석 데이터 부족"}
        
        # 핵심 KPI 계산
        total_pages = len(reports)
        actual_improvements = sum(1 for r in reports 
                                 if r.get("result", {}).get("original_text", "") != 
                                    r.get("result", {}).get("fixed_text", ""))
        
        improvement_rate = actual_improvements / total_pages * 100 if total_pages > 0 else 0
        
        # Conservative 모드 비율
        conservative_pages = sum(1 for r in reports 
                               if r.get("context", {}).get("safety_mode") == "conservative")
        conservative_rate = conservative_pages / total_pages * 100 if total_pages > 0 else 0
        
        # 규칙 적용률  
        rule_applied_pages = sum(1 for r in reports 
                               if r.get("result", {}).get("applied_rules", []))
        rule_application_rate = rule_applied_pages / total_pages * 100 if total_pages > 0 else 0
        
        # 등급 판정 기준
        if improvement_rate >= 70 and conservative_rate <= 10:
            grade = "D"  # 상용 출시 가능
            stage_name = "상용 출시 가능 단계"
        elif improvement_rate >= 50 and conservative_rate <= 20:
            grade = "C"  # 베타 사용자
            stage_name = "베타 사용자 단계"
        elif improvement_rate >= 30 and rule_application_rate >= 50:
            grade = "B"  # 내부 테스트
            stage_name = "내부 테스트 단계"
        else:
            grade = "A"  # 엔지니어 검증
            stage_name = "엔지니어 검증 단계"
        
        return {
            "current_grade": grade,
            "stage_name": stage_name,
            "kpi_scores": {
                "improvement_rate": round(improvement_rate, 1),
                "conservative_rate": round(conservative_rate, 1),
                "rule_application_rate": round(rule_application_rate, 1)
            },
            "next_stage_requirements": self._get_next_stage_requirements(grade),
            "estimated_timeline": self._estimate_development_timeline(grade, improvement_rate)
        }
    
    def _analyze_ocr_error_patterns(self) -> Dict:
        """OCR 오류 유형 클러스터링 (상위 20개)"""
        print("🔍 6️⃣ OCR 오류 패턴 클러스터링...")
        
        # 실제 Before/After 변화에서 오류 패턴 추출
        reports = self._collect_recent_processing_reports()
        error_patterns = []
        
        for report in reports:
            result = report.get("result", {})
            original = result.get("original_text", "")
            fixed = result.get("fixed_text", "")
            
            if original != fixed:
                # 변화 부분 추출
                changes = self._extract_text_changes(original, fixed)
                for change in changes:
                    error_patterns.append({
                        "before": change["before"],
                        "after": change["after"],
                        "error_type": self._classify_error_type(change["before"], change["after"]),
                        "context": change["context"]
                    })
        
        # 오류 유형별 클러스터링
        error_clusters = defaultdict(list)
        for error in error_patterns:
            error_clusters[error["error_type"]].append(error)
        
        # 상위 20개 오류 유형 정리
        top_error_types = []
        for error_type, errors in error_clusters.items():
            frequency = len(errors)
            
            # 현재 규칙으로 해결 가능한지 확인
            coverage = self._check_rule_coverage(error_type, errors)
            
            top_error_types.append({
                "error_type": error_type,
                "frequency": frequency,
                "percentage": round(frequency / len(error_patterns) * 100, 1) if error_patterns else 0,
                "rule_coverage": coverage["covered_count"],
                "coverage_rate": round(coverage["coverage_rate"], 1),
                "resolution_status": "해결 가능" if coverage["coverage_rate"] >= 80 else "개선 필요",
                "sample_errors": errors[:3]  # 샘플 3개
            })
        
        # 빈도순 정렬
        top_error_types.sort(key=lambda x: x["frequency"], reverse=True)
        
        return {
            "total_error_instances": len(error_patterns),
            "unique_error_types": len(error_clusters),
            "top_20_error_types": top_error_types[:20],
            "overall_coverage": self._calculate_overall_coverage(top_error_types),
            "priority_improvements": self._identify_priority_improvements(top_error_types[:20])
        }
    
    def _collect_recent_processing_reports(self) -> List[Dict]:
        """최근 processing_report 수집"""
        if not self.reports_dir.exists():
            return []
        
        reports = []
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for file_path in self.reports_dir.glob("processing_report_*.json"):
            try:
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time >= cutoff_time:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        report = json.load(f)
                        reports.append(report)
            except Exception as e:
                continue
                
        return reports
    
    def _analyze_change_significance(self, original: str, fixed: str) -> str:
        """텍스트 변화의 중요도 분석"""
        char_diff = abs(len(fixed) - len(original))
        
        # 문자 단위 차이 분석
        if char_diff == 0:
            return "cosmetic"  # 길이 변화 없음
        elif char_diff <= 2:
            return "minor"     # 미미한 변화
        elif char_diff <= 5:
            return "moderate"  # 중간 변화
        else:
            return "major"     # 큰 변화
    
    def _extract_text_changes(self, original: str, fixed: str) -> List[Dict]:
        """텍스트 변화 부분 추출"""
        changes = []
        
        # 간단한 diff 기반 변화 추출
        diff = list(difflib.unified_diff(
            original.splitlines(keepends=True),
            fixed.splitlines(keepends=True),
            n=1
        ))
        
        if diff:
            for line in diff:
                if line.startswith('-') and not line.startswith('---'):
                    before = line[1:].strip()
                elif line.startswith('+') and not line.startswith('+++'):
                    after = line[1:].strip()
                    if 'before' in locals():
                        changes.append({
                            "before": before,
                            "after": after,
                            "context": original[:50] + "..."
                        })
        
        return changes
    
    def _classify_error_type(self, before: str, after: str) -> str:
        """오류 타입 분류"""
        if not before or not after:
            return "unknown"
        
        # 간단한 패턴 기반 분류
        if re.search(r'[‛′]', before) and re.search(r"[']", after):
            return "quote_normalization"
        elif len(before.split()) != len(after.split()):
            return "spacing_error"
        elif before.isdigit() != after.isdigit():
            return "digit_character_confusion"
        elif len(before) == len(after):
            return "character_substitution"
        else:
            return "complex_error"
    
    def _check_rule_coverage(self, error_type: str, errors: List[Dict]) -> Dict:
        """오류 타입에 대한 현재 규칙 커버리지 확인"""
        # 현재 활성 규칙들과 매칭
        covered_count = 0
        
        for error in errors:
            # 간단한 패턴 매칭으로 커버리지 확인
            if self._is_covered_by_current_rules(error_type, error):
                covered_count += 1
        
        coverage_rate = covered_count / len(errors) * 100 if errors else 0
        
        return {
            "covered_count": covered_count,
            "total_count": len(errors),
            "coverage_rate": coverage_rate
        }
    
    def _is_covered_by_current_rules(self, error_type: str, error: Dict) -> bool:
        """현재 규칙으로 해당 오류가 커버되는지 확인"""
        # 현재 활성 규칙과 오류 타입 매칭
        rule_patterns = {
            "test_punctuation_rule": ["quote_normalization"],
            "smoke_test_rule": ["spacing_error", "character_substitution"]
        }
        
        for rule_id, covered_types in rule_patterns.items():
            if rule_id in self.active_rules and error_type in covered_types:
                return True
        return False
    
    def _generate_action_plan(self) -> Dict:
        """종합 액션 플랜 생성"""
        return {
            "immediate_actions": [
                "Dead Rules 제거 (효과 없는 규칙들)",
                "Conservative 모드 트리거 조건 완화",
                "가짜 개선 필터링 구현"
            ],
            "short_term_goals": [
                "Effective Rules 비율 50% 이상 달성",
                "폴백률 15% 이하로 감소",
                "실제 개선률 40% 이상 달성"
            ],
            "long_term_strategy": [
                "OCR 오류 패턴 기반 신규 규칙 생성",
                "도메인별 특화 규칙 확충",
                "사용자 체감 품질 75점 이상 달성"
            ]
        }
    
    def _print_analysis_results(self, report: Dict, report_file: Path):
        """분석 결과 출력"""
        print("\n" + "="*80)
        print("🚀 **SnapTXT 성능 종합 분석 결과**")
        print("="*80)
        
        # 현재 상태 평가
        current_state = report["current_state"]
        print(f"📊 현재 등급: {current_state['current_grade']} - {current_state['stage_name']}")
        kpi = current_state["kpi_scores"]
        print(f"📈 핵심 KPI: 개선률 {kpi['improvement_rate']}% | 폴백률 {kpi['conservative_rate']}% | 규칙 적용률 {kpi['rule_application_rate']}%")
        print()
        
        # 개선률 원인 분해
        improvement = report["improvement_causes"]
        print("🔍 **25% 개선률 원인 분해:**")
        causes = improvement["cause_breakdown"]
        print(f"   📋 규칙 커버리지 부족: {causes['rule_coverage_gap']}%")
        print(f"   🚫 Conservative 차단: {causes['conservative_blocking']}%")  
        print(f"   💄 표면적 규칙 위주: {causes['cosmetic_rule_dominance']}%")
        print(f"   ⚙️ 구현 갭: {causes['implementation_gap']}%")
        print()
        
        # 규칙 분류
        rule_class = report["rule_classification"]
        ratios = rule_class["ratios"]
        print("📋 **활성 규칙 분류:**")
        print(f"   💀 Dead Rules: {ratios['dead_ratio']}%")
        print(f"   💄 Cosmetic Rules: {ratios['cosmetic_ratio']}%")
        print(f"   ✅ Effective Rules: {ratios['effective_ratio']}%")
        print()
        
        # 폴백 분석
        fallback = report["fallback_analysis"]
        print(f"⚠️ **폴백률 분석:** 현재 {fallback['current_fallback_rate']}% (목표: 10% 이하)")
        breakdown = fallback["fallback_breakdown"]
        print(f"   📊 Conservative 모드: {breakdown['conservative_mode']}회")
        print(f"   🚫 게이트 차단: {breakdown['gate_blocking']}회")
        print(f"   💥 예외 처리: {breakdown['exception_handling']}회")
        print()
        
        # OCR 오류 패턴
        ocr_patterns = report.get("ocr_error_patterns", {})
        if ocr_patterns.get("top_20_error_types"):
            print("🎯 **상위 OCR 오류 유형:**")
            for i, error_type in enumerate(ocr_patterns["top_20_error_types"][:5]):
                print(f"   {i+1}. {error_type['error_type']}: {error_type['frequency']}회 ({error_type['percentage']}%) - 커버리지 {error_type['coverage_rate']}%")
        
        print()
        print("🎯 **종합 판정**")
        print(f"   ⭐ 현재 단계: {current_state['stage_name']}")
        print(f"   📅 다음 단계까지 예상 기간: {current_state.get('estimated_timeline', '미정')}")
        
        print(f"\n📄 상세 분석 리포트: {report_file}")
        print("="*80)
    
    # 헬퍼 메소드들
    def _diagnose_improvement_bottleneck(self, rule_gap, conservative_gap, cosmetic_gap, impl_gap):
        primary_issue = max(
            ("규칙 커버리지 부족", rule_gap),
            ("Conservative 과다 차단", conservative_gap),
            ("표면적 규칙 위주", cosmetic_gap),
            ("구현 갭", impl_gap)
        )
        return f"주요 원인: {primary_issue[0]} ({primary_issue[1]:.1f}%)"
    
    def _generate_rule_improvement_strategies(self, effective_ratio):
        if effective_ratio < 30:
            return "규칙 전면 재설계 필요 - 대부분이 Dead/Cosmetic 규칙"
        elif effective_ratio < 50:
            return "Effective Rules 확충 필요 - 의미있는 교정 규칙 추가"
        else:
            return "현재 규칙 품질 양호 - 적용 범위 확대에 집중"
    
    def _diagnose_fake_improvement_cause(self, applied_rules, text):
        if not applied_rules:
            return "규칙 적용 로직 오류"
        elif any("test" in rule.get("rule_id", "") for rule in applied_rules):
            return "테스트 규칙의 잘못된 실행"
        else:
            return "규칙 패턴과 텍스트 불일치"
    
    def _generate_fallback_reduction_actions(self, causes, current_rate):
        actions = []
        if causes["conservative_mode"] > 0:
            actions.append("Conservative 모드 트리거 조건 완화")
        if causes["gate_blocking"] > 0:
            actions.append("Regression Gate 기준 조정") 
        if causes["rule_loading_failure"] > 0:
            actions.append("규칙 로딩 안정성 개선")
        if current_rate > 20:
            actions.append("긴급: 폴백률 20% 초과 - 즉시 조치 필요")
        return actions
    
    def _get_next_stage_requirements(self, current_grade):
        requirements = {
            "A": "개선률 30% + 규칙 적용률 50% (B단계로 진입)",
            "B": "개선률 50% + 폴백률 20% 이하 (C단계로 진입)", 
            "C": "개선률 70% + 폴백률 10% 이하 (D단계로 진입)",
            "D": "현재 상용 출시 가능 상태"
        }
        return requirements.get(current_grade, "알 수 없음")
    
    def _estimate_development_timeline(self, grade, improvement_rate):
        timelines = {
            "A": "3-6개월 (기초 규칙 확충 필요)",
            "B": "1-3개월 (폴백률 개선 집중)",
            "C": "2-4주 (최종 품질 조정)",
            "D": "즉시 출시 가능"
        }
        return timelines.get(grade, "추정 불가")
    
    def _calculate_overall_coverage(self, error_types):
        if not error_types:
            return 0.0
        total_weighted_coverage = sum(
            et["frequency"] * et["coverage_rate"] / 100 
            for et in error_types
        )
        total_frequency = sum(et["frequency"] for et in error_types)
        return round(total_weighted_coverage / total_frequency * 100, 1) if total_frequency > 0 else 0
    
    def _identify_priority_improvements(self, top_errors):
        priority_list = []
        for error in top_errors[:10]:  # 상위 10개만
            if error["coverage_rate"] < 50:  # 커버리지 50% 미만
                priority_list.append({
                    "error_type": error["error_type"],
                    "frequency": error["frequency"],
                    "current_coverage": error["coverage_rate"],
                    "priority": "높음" if error["frequency"] > 10 else "중간"
                })
        return priority_list


def main():
    """메인 실행 함수"""
    analyzer = SnapTXTPerformanceAnalyzer()
    
    print("🚀 SnapTXT 실제 성능 향상 분석 시작")
    print("전략: 엔지니어 검증 → 사용자 체감 품질 개선")
    print("목표: 오류 유형 분석 → 규칙 생성 → 효과 측정 루프\n")
    
    result = analyzer.run_comprehensive_analysis()
    
    print("\n✅ 종합 분석 완료!")
    print("📊 이제 '실제 OCR 오류 수정률' 향상에 집중하세요.")


if __name__ == "__main__":
    main()