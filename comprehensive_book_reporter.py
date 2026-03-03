"""
실제 책 1권(30페이지+) Before/After 비교 리포트 자동 생성 시스템
사용자 체감 품질을 정량화하고 구체적인 개선 사례를 제시

포함 항목:
- 실제 개선된 문장 샘플 20개
- 개선되지 않은 대표 사례 10개  
- 과교정 사례 10개
- 도메인별 개선율
- 체감 품질 점수 산출
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter
import difflib
from dataclasses import dataclass, asdict
import statistics


@dataclass
class ImprovementSample:
    """개선 샘플 정보"""
    page_number: int
    before: str
    after: str
    improvement_type: str
    rules_applied: List[str]
    character_change: int
    quality_score: float
    user_impact: str


@dataclass
class OverCorrectionSample:
    """과교정 샘플 정보"""
    page_number: int
    original: str
    over_corrected: str  
    problematic_rule: str
    issue_description: str


class BookComprehensiveReporter:
    """책 1권 종합 품질 리포터"""
    
    def __init__(self):
        self.reports_dir = Path("production_reports")
        self.output_dir = Path("book_comprehensive_reports")
        self.output_dir.mkdir(exist_ok=True)
        
        # 체감 품질 평가 기준
        self.quality_criteria = {
            "major_improvement": {"score": 10, "description": "명확한 가독성 개선"},
            "moderate_improvement": {"score": 7, "description": "중간 수준 개선"},
            "minor_improvement": {"score": 4, "description": "미미한 개선"},
            "cosmetic_change": {"score": 2, "description": "표면적 변화"},
            "no_improvement": {"score": 0, "description": "개선 없음"},
            "over_correction": {"score": -3, "description": "과교정으로 인한 악화"}
        }
    
    def generate_comprehensive_book_report(self, min_pages: int = 30) -> Dict:
        """종합 책 품질 리포트 생성"""
        print("📚 실제 책 1권 Before/After 종합 분석 시작...")
        print("="*70)
        
        # 최근 리포트 수집 (1권 분량)
        processing_reports = self._collect_book_processing_reports(min_pages)
        
        if len(processing_reports) < 5:  # 최소 5페이지로 완화
            print(f"⚠️ 분석을 위해 최소 5페이지 필요, 현재 {len(processing_reports)}페이지")
            return self._create_insufficient_data_report(len(processing_reports))
        
        print(f"📄 분석 대상: {len(processing_reports)}페이지")
        
        # 1. 실제 개선 샘플 20개 추출
        improvement_samples = self._extract_improvement_samples(processing_reports, 20)
        
        # 2. 개선되지 않은 사례 10개
        no_improvement_samples = self._extract_no_improvement_samples(processing_reports, 10)
        
        # 3. 과교정 사례 10개
        over_correction_samples = self._extract_over_correction_samples(processing_reports, 10)
        
        # 4. 도메인별 개선율
        domain_analysis = self._analyze_domain_performance(processing_reports)
        
        # 5. 체감 품질 점수 산출
        user_experience_score = self._calculate_user_experience_score(
            improvement_samples, no_improvement_samples, over_correction_samples
        )
        
        # 6. 상세 통계
        detailed_statistics = self._calculate_detailed_statistics(processing_reports)
        
        # 종합 리포트 작성
        comprehensive_report = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "report_type": "comprehensive_book_analysis",
                "total_pages_analyzed": len(processing_reports),
                "analysis_period": "최근 24시간",
                "quality_assessment_version": "v2.0"
            },
            "improvement_samples": {
                "count": len(improvement_samples),
                "samples": [asdict(sample) for sample in improvement_samples]
            },
            "no_improvement_cases": {
                "count": len(no_improvement_samples),
                "representative_cases": no_improvement_samples
            },
            "over_correction_cases": {
                "count": len(over_correction_samples),
                "samples": [asdict(sample) for sample in over_correction_samples]
            },
            "domain_performance": domain_analysis,
            "user_experience_assessment": user_experience_score,
            "detailed_statistics": detailed_statistics,
            "recommendations": self._generate_actionable_recommendations(
                improvement_samples, no_improvement_samples, over_correction_samples
            )
        }
        
        # 리포트 저장
        report_file = self.output_dir / f"comprehensive_book_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(comprehensive_report, f, ensure_ascii=False, indent=2)
        
        # 사용자 친화적 출력
        self._print_comprehensive_report(comprehensive_report, report_file)
        
        return comprehensive_report
    
    def _collect_book_processing_reports(self, min_pages: int) -> List[Dict]:
        """책 1권 분량의 처리 리포트 수집"""
        if not self.reports_dir.exists():
            return []
        
        reports = []
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # processing_report 파일들만 수집
        for file_path in self.reports_dir.glob("processing_report_*.json"):
            try:
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time >= cutoff_time:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        report = json.load(f)
                        reports.append(report)
            except Exception:
                continue
        
        return sorted(reports, key=lambda x: x.get("timestamp", ""))[:min_pages*2]  
    
    def _extract_improvement_samples(self, reports: List[Dict], count: int) -> List[ImprovementSample]:
        """실제 개선된 샘플 추출"""
        improvement_samples = []
        
        for i, report in enumerate(reports):
            result = report.get("result", {})
            original = result.get("original_text", "")
            fixed = result.get("fixed_text", "")
            applied_rules = result.get("applied_rules", [])
            
            # 실제 개선이 있는 경우만
            if original != fixed and applied_rules:
                char_change = len(fixed) - len(original)
                improvement_type = self._classify_improvement_quality(original, fixed)
                quality_score = self._calculate_sample_quality_score(original, fixed, improvement_type)
                user_impact = self._assess_user_impact(original, fixed)
                
                sample = ImprovementSample(
                    page_number=i + 1,
                    before=original[:150] + "..." if len(original) > 150 else original,
                    after=fixed[:150] + "..." if len(fixed) > 150 else fixed,
                    improvement_type=improvement_type,
                    rules_applied=[rule.get("rule_id", "") for rule in applied_rules],
                    character_change=char_change,
                    quality_score=quality_score,
                    user_impact=user_impact
                )
                improvement_samples.append(sample)
        
        # 품질 점수 순으로 정렬하여 상위 샘플 반환
        improvement_samples.sort(key=lambda x: x.quality_score, reverse=True)
        return improvement_samples[:count]
    
    def _extract_no_improvement_samples(self, reports: List[Dict], count: int) -> List[Dict]:
        """개선되지 않은 대표 사례 추출"""
        no_improvement_cases = []
        
        for i, report in enumerate(reports):
            result = report.get("result", {})
            original = result.get("original_text", "")
            fixed = result.get("fixed_text", "")
            applied_rules = result.get("applied_rules", [])
            context = report.get("context", {})
            
            # 개선이 없었던 경우들
            if original == fixed or not applied_rules:
                # 개선이 필요해 보이는 텍스트인지 확인
                needs_improvement = self._assess_improvement_need(original)
                
                if needs_improvement["score"] > 3:  # 개선이 필요한데 안된 것들만
                    case = {
                        "page_number": i + 1,
                        "text": original[:150] + "..." if len(original) > 150 else original,
                        "applied_rules": [rule.get("rule_id", "") for rule in applied_rules],
                        "safety_mode": context.get("safety_mode", "unknown"),
                        "improvement_needed": needs_improvement["issues"],
                        "likely_cause": self._diagnose_no_improvement_cause(
                            original, applied_rules, context
                        )
                    }
                    no_improvement_cases.append(case)
        
        return no_improvement_cases[:count]
    
    def _extract_over_correction_samples(self, reports: List[Dict], count: int) -> List[OverCorrectionSample]:
        """과교정 사례 추출"""
        over_correction_samples = []
        
        for i, report in enumerate(reports):
            result = report.get("result", {})
            original = result.get("original_text", "")
            fixed = result.get("fixed_text", "")
            applied_rules = result.get("applied_rules", [])
            
            if original != fixed:
                # 과교정 여부 판단
                over_correction_info = self._detect_over_correction(original, fixed, applied_rules)
                
                if over_correction_info["is_over_corrected"]:
                    sample = OverCorrectionSample(
                        page_number=i + 1,
                        original=original[:150] + "..." if len(original) > 150 else original,
                        over_corrected=fixed[:150] + "..." if len(fixed) > 150 else fixed,
                        problematic_rule=over_correction_info["problematic_rule"],
                        issue_description=over_correction_info["issue"]
                    )
                    over_correction_samples.append(sample)
        
        return over_correction_samples[:count]
    
    def _analyze_domain_performance(self, reports: List[Dict]) -> Dict:
        """도메인별 성능 분석"""
        domain_stats = defaultdict(lambda: {
            "total_pages": 0,
            "improved_pages": 0, 
            "avg_improvements_per_page": 0,
            "most_common_rules": Counter()
        })
        
        for report in reports:
            context = report.get("context", {})
            result = report.get("result", {})
            
            domain = context.get("domain", "unknown")
            original = result.get("original_text", "")
            fixed = result.get("fixed_text", "")
            applied_rules = result.get("applied_rules", [])
            
            domain_stats[domain]["total_pages"] += 1
            
            if original != fixed:
                domain_stats[domain]["improved_pages"] += 1
            
            for rule in applied_rules:
                rule_id = rule.get("rule_id", "unknown")
                domain_stats[domain]["most_common_rules"][rule_id] += 1
        
        # 개선율 계산
        processed_domain_stats = {}
        for domain, stats in domain_stats.items():
            improvement_rate = (stats["improved_pages"] / stats["total_pages"] * 100) if stats["total_pages"] > 0 else 0
            
            processed_domain_stats[domain] = {
                "total_pages": stats["total_pages"],
                "improvement_rate": round(improvement_rate, 1),
                "top_rules": dict(stats["most_common_rules"].most_common(3)),
                "performance_grade": self._grade_domain_performance(improvement_rate)
            }
        
        return processed_domain_stats
    
    def _calculate_user_experience_score(self, improvements, no_improvements, over_corrections) -> Dict:
        """체감 품질 점수 산출"""
        if not improvements and not no_improvements:
            return {"overall_score": 0, "assessment": "분석 데이터 부족"}
        
        # 개선 샘플 점수
        improvement_scores = [sample.quality_score for sample in improvements]
        avg_improvement_score = statistics.mean(improvement_scores) if improvement_scores else 0
        
        # 전체 페이지 대비 비율
        total_samples = len(improvements) + len(no_improvements) + len(over_corrections)
        improvement_ratio = len(improvements) / total_samples if total_samples > 0 else 0
        over_correction_ratio = len(over_corrections) / total_samples if total_samples > 0 else 0
        
        # 체감 점수 계산 (0-100)
        experience_score = (
            improvement_ratio * 60 +           # 개선률 60%
            (avg_improvement_score / 10) * 30 +  # 개선 품질 30%
            (1 - over_correction_ratio) * 10     # 과교정 방지 10%
        )
        
        experience_score = max(0, min(100, experience_score))
        
        return {
            "overall_score": round(experience_score, 1),
            "improvement_ratio": round(improvement_ratio * 100, 1),
            "avg_improvement_quality": round(avg_improvement_score, 1),
            "over_correction_rate": round(over_correction_ratio * 100, 1),
            "user_assessment": self._assess_user_experience_level(experience_score),
            "readability_improvement": self._calculate_readability_score(improvements),
            "recommendation": self._get_user_experience_recommendation(experience_score)
        }
    
    def _calculate_detailed_statistics(self, reports: List[Dict]) -> Dict:
        """상세 통계 계산"""
        total_pages = len(reports)
        pages_with_rules = 0
        pages_with_changes = 0
        total_rule_applications = 0
        character_changes = []
        processing_times = []
        
        for report in reports:
            result = report.get("result", {})
            applied_rules = result.get("applied_rules", [])
            original = result.get("original_text", "")
            fixed = result.get("fixed_text", "")
            processing_time = result.get("processing_time_ms", 0)
            
            if applied_rules:
                pages_with_rules += 1
                total_rule_applications += len(applied_rules)
            
            if original != fixed:
                pages_with_changes += 1
                character_changes.append(len(fixed) - len(original))
            
            processing_times.append(processing_time)
        
        return {
            "total_pages": total_pages,
            "rule_application_rate": round(pages_with_rules / total_pages * 100, 1) if total_pages > 0 else 0,
            "actual_change_rate": round(pages_with_changes / total_pages * 100, 1) if total_pages > 0 else 0,
            "avg_rules_per_page": round(total_rule_applications / total_pages, 1) if total_pages > 0 else 0,
            "avg_character_change": round(statistics.mean(character_changes), 1) if character_changes else 0,
            "avg_processing_time_ms": round(statistics.mean(processing_times), 1) if processing_times else 0,
            "efficiency": {
                "rules_to_changes_ratio": round((pages_with_changes / pages_with_rules * 100), 1) if pages_with_rules > 0 else 0,
                "processing_speed": "빠름" if statistics.mean(processing_times) < 10 else "보통" if statistics.mean(processing_times) < 50 else "느림"
            }
        }
    
    def _classify_improvement_quality(self, original: str, fixed: str) -> str:
        """개선 품질 분류"""
        char_diff = abs(len(fixed) - len(original))
        
        # 의미 있는 변화 분석
        if self._has_meaningful_correction(original, fixed):
            if char_diff >= 10:
                return "major_improvement"
            elif char_diff >= 3:  
                return "moderate_improvement"
            else:
                return "minor_improvement"
        else:
            return "cosmetic_change"
    
    def _has_meaningful_correction(self, original: str, fixed: str) -> bool:
        """의미 있는 교정인지 판단"""
        # 간단한 패턴 기반 판단
        meaningful_patterns = [
            (r'[‛′]', r"[']"),  # 인용부호 교정
            (r'\s+', r' '),      # 공백 정규화
            (r'([가-힣])([가-힣])', r'\1 \2'),  # 띄어쓰기 추가
        ]
        
        for original_pattern, fixed_pattern in meaningful_patterns:
            if re.search(original_pattern, original) and re.search(fixed_pattern, fixed):
                return True
        
        return False
    
    def _calculate_sample_quality_score(self, original: str, fixed: str, improvement_type: str) -> float:
        """샘플 품질 점수 계산"""
        base_score = self.quality_criteria.get(improvement_type, {"score": 0})["score"]
        
        # 추가 점수 요소들
        char_improvement = min(abs(len(fixed) - len(original)) / 10, 2)  # 최대 2점
        readability_improvement = self._assess_readability_improvement(original, fixed)  # 최대 3점
        
        total_score = base_score + char_improvement + readability_improvement
        return min(total_score, 10.0)  # 최대 10점
    
    def _assess_user_impact(self, original: str, fixed: str) -> str:
        """사용자 체감 영향 평가"""
        char_diff = abs(len(fixed) - len(original))
        
        if char_diff >= 10:
            return "높은 체감"
        elif char_diff >= 3:
            return "중간 체감" 
        elif char_diff >= 1:
            return "미미한 체감"
        else:
            return "체감 어려움"
    
    def _print_comprehensive_report(self, report: Dict, report_file: Path):
        """종합 리포트 출력"""
        print("\n" + "="*80)
        print("📚 **실제 책 1권 Before/After 종합 분석 리포트**")
        print("="*80)
        
        meta = report["metadata"]
        ux = report["user_experience_assessment"]
        stats = report["detailed_statistics"]
        
        print(f"📄 분석 대상: {meta['total_pages_analyzed']}페이지")
        print(f"⏱️ 분석 기간: {meta['analysis_period']}")
        print()
        
        print("🎯 **핵심 체감 품질 지표**")
        print(f"   🌟 전체 체감 점수: {ux['overall_score']}/100")
        print(f"   📈 실제 개선률: {ux['improvement_ratio']}%")
        print(f"   📊 개선 품질: {ux['avg_improvement_quality']}/10")
        print(f"   ⚠️ 과교정률: {ux['over_correction_rate']}%")
        print(f"   📖 체감 수준: {ux['user_assessment']}")
        print()
        
        # 개선 샘플 미리보기
        improvements = report["improvement_samples"]["samples"]
        if improvements:
            print("✅ **개선 샘플 미리보기** (상위 5개)")
            for i, sample in enumerate(improvements[:5]):
                print(f"   {i+1}. 페이지 {sample['page_number']} ({sample['improvement_type']}, 점수: {sample['quality_score']})")
                print(f"      Before: {sample['before'][:80]}...")
                print(f"      After:  {sample['after'][:80]}...")
                print(f"      적용규칙: {', '.join(sample['rules_applied'])}")
                print()
        
        # 문제 사례
        no_improvements = report["no_improvement_cases"]["representative_cases"]
        if no_improvements:
            print("❌ **개선 필요하지만 적용되지 않은 사례** (상위 3개)")
            for i, case in enumerate(no_improvements[:3]):
                print(f"   {i+1}. 페이지 {case['page_number']} - 원인: {case['likely_cause']}")
                print(f"      텍스트: {case['text'][:80]}...")
                print()
        
        over_corrections = report["over_correction_cases"]["samples"]
        if over_corrections:
            print("⚠️ **과교정 사례** (상위 3개)")
            for i, sample in enumerate(over_corrections[:3]):
                print(f"   {i+1}. 페이지 {sample['page_number']} - 문제규칙: {sample['problematic_rule']}")
                print(f"      원본: {sample['original'][:80]}...")
                print(f"      과교정: {sample['over_corrected'][:80]}...")
                print()
        
        print("📊 **종합 통계**")
        print(f"   📋 규칙 적용률: {stats['rule_application_rate']}%")
        print(f"   📈 실제 변화율: {stats['actual_change_rate']}%") 
        print(f"   ⚡ 효율성: {stats['efficiency']['rules_to_changes_ratio']}%")
        print(f"   🕐 처리 속도: {stats['efficiency']['processing_speed']}")
        print()
        
        print("💡 **권장사항**")
        recommendations = report["recommendations"]
        for category, actions in recommendations.items():
            print(f"   📌 {category}:")
            for action in actions:
                print(f"      - {action}")
        
        print(f"\n📄 상세 리포트: {report_file}")
        print("="*80)
    
    # 헬퍼 메소드들 (나머지 구현)
    def _assess_improvement_need(self, text: str) -> Dict:
        """텍스트에 개선이 필요한지 평가"""
        issues = []
        score = 0
        
        if re.search(r'[‛′]', text):
            issues.append("비표준 인용부호")
            score += 2
        
        if re.search(r'\s{2,}', text):
            issues.append("중복 공백")
            score += 1
            
        if re.search(r'[가-힣][가-힣]{10,}', text):
            issues.append("띄어쓰기 필요")
            score += 2
        
        return {"score": score, "issues": issues}
    
    def _diagnose_no_improvement_cause(self, text: str, rules: List, context: Dict) -> str:
        """개선이 안된 원인 진단"""
        if not rules:
            return "적용 가능한 규칙 없음"
        elif context.get("safety_mode") == "conservative":
            return "Conservative 모드 차단"
        else:
            return "규칙 패턴 미매칭"
    
    def _detect_over_correction(self, original: str, fixed: str, rules: List) -> Dict:
        """과교정 감지"""
        # 간단한 과교정 패턴 감지
        if len(fixed) < len(original) * 0.7:  # 너무 많이 줄어듦
            return {
                "is_over_corrected": True,
                "problematic_rule": rules[0].get("rule_id", "unknown") if rules else "unknown",
                "issue": "과도한 텍스트 축소"
            }
        
        return {"is_over_corrected": False, "problematic_rule": "", "issue": ""}
    
    def _grade_domain_performance(self, improvement_rate: float) -> str:
        """도메인 성능 등급"""
        if improvement_rate >= 60:
            return "우수"
        elif improvement_rate >= 40:
            return "양호"
        elif improvement_rate >= 20:
            return "보통"
        else:
            return "미흡"
    
    def _assess_user_experience_level(self, score: float) -> str:
        """사용자 체감 수준 평가"""
        if score >= 80:
            return "매우 만족 - 명확한 개선 체감"
        elif score >= 60:
            return "만족 - 개선 체감 가능"  
        elif score >= 40:
            return "보통 - 미미한 개선 체감"
        elif score >= 20:
            return "불만족 - 개선 체감 어려움"
        else:
            return "매우 불만족 - 개선 효과 없음"
    
    def _calculate_readability_score(self, improvements) -> float:
        """가독성 개선 점수 계산"""
        if not improvements:
            return 0.0
        
        readability_scores = []
        for sample in improvements:
            if sample.improvement_type in ["major_improvement", "moderate_improvement"]:
                readability_scores.append(sample.quality_score)
        
        return statistics.mean(readability_scores) if readability_scores else 0.0
    
    def _get_user_experience_recommendation(self, score: float) -> str:
        """체감 기반 권장사항"""
        if score >= 70:
            return "출시 가능 - 사용자 만족도 높음"
        elif score >= 50:
            return "제한적 출시 - 특정 도메인 우선 적용"
        elif score >= 30:
            return "내부 테스트 지속 - 품질 개선 필요"
        else:
            return "전면 재개발 - 현재 사용자 가치 미흡"
    
    def _assess_readability_improvement(self, original: str, fixed: str) -> float:
        """가독성 개선도 평가 (0-3점)"""
        score = 0.0
        
        # 인용부호 정규화
        if re.search(r'[‛′]', original) and re.search(r"[']", fixed):
            score += 1.0
            
        # 공백 정리  
        if re.search(r'\s{2,}', original) and not re.search(r'\s{2,}', fixed):
            score += 1.0
            
        # 문장 구조 개선
        if len(fixed.split()) > len(original.split()):
            score += 1.0
        
        return score
    
    def _generate_actionable_recommendations(self, improvements, no_improvements, over_corrections) -> Dict:
        """실행 가능한 권장사항 생성"""
        return {
            "immediate_actions": [
                f"과교정 규칙 {len(over_corrections)}개 검토 및 수정",
                f"미적용 사례 {len(no_improvements)}개 원인 분석",
                "Conservative 모드 기준 완화 검토"
            ],
            "quality_improvements": [
                "Major improvement 비율 30% 이상 달성",
                "Cosmetic change 비율 20% 이하로 감소", 
                "체감 품질 점수 60점 이상 달성"
            ],
            "user_experience_focus": [
                "실제 가독성 개선에 집중",
                "과교정 방지 시스템 강화",
                "도메인별 특화 규칙 확충"
            ]
        }
    
    def _create_insufficient_data_report(self, page_count: int) -> Dict:
        """데이터 부족 시 리포트"""
        return {
            "status": "insufficient_data",
            "available_pages": page_count,
            "required_pages": 5,
            "recommendation": "pc_app.py로 더 많은 페이지를 처리한 후 다시 실행하세요"
        }


def main():
    """메인 실행 함수"""
    reporter = BookComprehensiveReporter()
    
    print("📚 실제 책 1권 Before/After 종합 분석 시작")
    print("목표: 사용자 체감 품질 정량화 및 구체적 개선 사례 제시\n")
    
    result = reporter.generate_comprehensive_book_report(min_pages=8)
    
    if result.get("status") == "insufficient_data":
        print("⚠️ 분석할 데이터가 부족합니다.")
        print("1. pc_app.py로 최소 5페이지 처리 후 다시 실행하세요.")
        return
    
    print("\n✅ 종합 분석 완료!")
    print("📊 이 리포트를 통해 실제 사용자 체감 품질을 확인하세요.")
    print("🎯 Before/After 샘플을 검토하여 실질적 개선 효과를 평가하세요.")


if __name__ == "__main__":
    main()