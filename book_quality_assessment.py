"""
책 1권(30페이지) 실제 품질 비교 시스템
사용자 체감 품질 개선을 객관적으로 측정

사용법:
1. pc_app.py로 책 1권 처리
2. python book_quality_assessment.py 실행
3. 20개 Before/After 샘플 자동 추출 및 품질 분석
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import List, Dict, Tuple
import difflib

class BookQualityAssessment:
    """1권 책 전체 품질 평가 시스템"""
    
    def __init__(self):
        self.reports_dir = Path("production_reports")
        self.output_dir = Path("book_quality_reports")
        self.output_dir.mkdir(exist_ok=True)
    
    def analyze_book_quality(self, min_pages: int = 30) -> Dict:
        """1권 책 전체 품질 분석"""
        print("📚 책 1권 품질 분석 시작...")
        
        # 최근 리포트 수집 (1권 분량)
        recent_reports = self._collect_recent_reports(min_pages)
        
        if len(recent_reports) < 5:  # 최소 5페이지로 낮춤
            print(f"⚠️ 최소 5페이지 필요, 현재 {len(recent_reports)}페이지")
            return {}
        
        print(f"📄 분석 대상: {len(recent_reports)}개 페이지")
        
        # 전체 품질 메트릭 계산
        quality_metrics = self._calculate_quality_metrics(recent_reports)
        
        # Top 20 개선 샘플 추출
        improvement_samples = self._extract_improvement_samples(recent_reports, 20)
        
        # 사용자 체감 분석
        user_experience_analysis = self._analyze_user_experience(quality_metrics, improvement_samples)
        
        # 리포트 생성
        assessment_report = {
            "timestamp": datetime.now().isoformat(),
            "book_info": {
                "total_pages": len(recent_reports),
                "analysis_period": "최근 24시간"
            },
            "quality_metrics": quality_metrics,
            "improvement_samples": improvement_samples,
            "user_experience": user_experience_analysis,
            "verdict": self._make_quality_verdict(quality_metrics)
        }
        
        # 리포트 저장
        output_file = self.output_dir / f"book_quality_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(assessment_report, f, ensure_ascii=False, indent=2)
        
        # 사용자 친화적 출력
        self._print_user_report(assessment_report, output_file)
        
        return assessment_report
    
    def _collect_recent_reports(self, min_pages: int) -> List[Dict]:
        """최근 리포트 수집"""
        if not self.reports_dir.exists():
            return []
        
        # 24시간 내 processing_report 파일들
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_files = []
        
        for file_path in self.reports_dir.glob("processing_report_*.json"):
            try:
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time >= cutoff_time:
                    recent_files.append(file_path)
            except:
                continue
        
        # 파일 내용 로드
        reports = []
        for file_path in sorted(recent_files)[:min_pages*2]:  # 충분히 수집
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                    reports.append(report)
            except:
                continue
        
        return reports
    
    def _calculate_quality_metrics(self, reports: List[Dict]) -> Dict:
        """전체 품질 메트릭 계산"""
        total_pages = len(reports)
        pages_with_rules = 0
        pages_with_actual_changes = 0
        total_text_before = 0
        total_text_after = 0
        rule_applications = []
        fallback_count = 0
        
        for report in reports:
            result = report.get("result", {})
            
            # 규칙 적용 페이지 카운트
            applied_rules = result.get("applied_rules", [])
            if applied_rules:
                pages_with_rules += 1
                rule_applications.extend([rule.get("rule_id", "") for rule in applied_rules])
            
            # 실제 변화 확인
            original = result.get("original_text", "")
            fixed = result.get("fixed_text", "")
            
            total_text_before += len(original)
            total_text_after += len(fixed)
            
            if original != fixed:
                pages_with_actual_changes += 1
            
            # 폴백 확인 (context에서)
            context = report.get("context", {})
            if context.get("safety_mode") == "conservative":
                fallback_count += 1
        
        return {
            "total_pages": total_pages,
            "rule_application_rate": round(pages_with_rules / total_pages * 100, 1) if total_pages > 0 else 0,
            "actual_improvement_rate": round(pages_with_actual_changes / total_pages * 100, 1) if total_pages > 0 else 0,
            "fallback_rate": round(fallback_count / total_pages * 100, 1) if total_pages > 0 else 0,
            "avg_text_length": round(total_text_before / total_pages) if total_pages > 0 else 0,
            "length_change_ratio": round((total_text_after - total_text_before) / total_text_before * 100, 2) if total_text_before > 0 else 0,
            "most_used_rules": self._get_top_rules(rule_applications),
            "total_rule_applications": len(rule_applications)
        }
    
    def _get_top_rules(self, rule_applications: List[str]) -> List[Dict]:
        """상위 규칙 사용 통계"""
        if not rule_applications:
            return []
        
        rule_counts = {}
        for rule_id in rule_applications:
            rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1
        
        top_rules = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        return [{"rule_id": rule, "count": count} for rule, count in top_rules]
    
    def _extract_improvement_samples(self, reports: List[Dict], count: int) -> List[Dict]:
        """개선 샘플 추출 (Before/After 비교용)"""
        samples = []
        
        for i, report in enumerate(reports):
            result = report.get("result", {})
            original = result.get("original_text", "")
            fixed = result.get("fixed_text", "")
            applied_rules = result.get("applied_rules", [])
            
            # 실제 변화가 있는 것만 샘플로 추출
            if original != fixed and applied_rules:
                # diff 생성
                diff_lines = list(difflib.unified_diff(
                    original.splitlines(keepends=True),
                    fixed.splitlines(keepends=True),
                    fromfile="Before",
                    tofile="After",
                    n=1
                ))
                
                sample = {
                    "page_number": i + 1,
                    "before": original[:200] + "..." if len(original) > 200 else original,
                    "after": fixed[:200] + "..." if len(fixed) > 200 else fixed,
                    "applied_rules": [rule.get("rule_id", "") for rule in applied_rules],
                    "character_change": len(fixed) - len(original),
                    "diff_preview": "".join(diff_lines)[:500],
                    "improvement_type": self._classify_improvement(original, fixed, applied_rules)
                }
                samples.append(sample)
        
        # 개선 타입별, 변화량별로 정렬하여 대표 샘플 선택
        samples.sort(key=lambda x: (
            x["improvement_type"] != "meaningful", 
            abs(x["character_change"])
        ))
        
        return samples[:count]
    
    def _classify_improvement(self, original: str, fixed: str, applied_rules: List[Dict]) -> str:
        """개선 타입 분류"""
        char_diff = abs(len(fixed) - len(original))
        
        if char_diff == 0:
            return "cosmetic"  # 표면적 (길이 변화 없음)
        elif char_diff < 5:
            return "minor"     # 소폭
        elif char_diff >= 10:
            return "major"     # 대폭
        else:
            return "moderate"  # 중간
    
    def _analyze_user_experience(self, metrics: Dict, samples: List[Dict]) -> Dict:
        """사용자 체감 품질 분석"""
        # 실제 개선 비율이 핵심 지표
        actual_improvement = metrics["actual_improvement_rate"]
        fallback_rate = metrics["fallback_rate"]
        
        # 개선 샘플의 품질 분석
        meaningful_improvements = len([s for s in samples if s["improvement_type"] in ["moderate", "major"]])
        total_improvements = len(samples)
        
        if total_improvements == 0:
            meaningful_ratio = 0
        else:
            meaningful_ratio = meaningful_improvements / total_improvements * 100
        
        # 사용자 체감 점수 계산 (0-100)
        experience_score = (
            actual_improvement * 0.4 +       # 실제 개선률 40%
            (100 - fallback_rate) * 0.3 +   # 안정성 30%
            meaningful_ratio * 0.3           # 의미있는 개선 30%
        )
        
        return {
            "experience_score": round(experience_score, 1),
            "actual_improvement_rate": actual_improvement,
            "meaningful_improvement_ratio": round(meaningful_ratio, 1),
            "stability_score": round(100 - fallback_rate, 1),
            "readability_assessment": self._assess_readability(experience_score),
            "recommendation": self._get_user_recommendation(experience_score, fallback_rate)
        }
    
    def _assess_readability(self, score: float) -> str:
        """가독성 평가"""
        if score >= 80:
            return "우수 - 명확한 품질 개선 체감"
        elif score >= 60:
            return "양호 - 일부 개선 체감 가능"
        elif score >= 40:
            return "보통 - 미미한 개선 체감"
        elif score >= 20:
            return "부족 - 개선 체감 어려움"
        else:
            return "매우부족 - 개선 효과 없음"
    
    def _get_user_recommendation(self, score: float, fallback_rate: float) -> str:
        """사용자 권장사항"""
        if score >= 70 and fallback_rate <= 10:
            return "출시 가능 - 사용자 품질 보장"
        elif score >= 50 and fallback_rate <= 20:
            return "제한적 출시 - 특정 도메인 먼저 적용"
        elif score >= 30:
            return "내부 테스트 계속 - 규칙 개선 필요"
        else:
            return "규칙 재학습 필요 - 현재 효과 미미"
    
    def _make_quality_verdict(self, metrics: Dict) -> Dict:
        """종합 품질 판정"""
        rule_rate = metrics["rule_application_rate"]
        actual_rate = metrics["actual_improvement_rate"]
        fallback_rate = metrics["fallback_rate"]
        
        # 핵심 지표들
        issues = []
        if actual_rate < 30:
            issues.append("실제 개선률 부족")
        if fallback_rate > 15:
            issues.append("폴백률 과다")
        if rule_rate < 50:
            issues.append("규칙 적용률 부족")
        
        # 최종 판정
        if not issues:
            verdict = "우수"
        elif len(issues) == 1:
            verdict = "보통"
        elif len(issues) == 2:
            verdict = "부족"
        else:
            verdict = "매우부족"
        
        return {
            "overall_grade": verdict,
            "critical_issues": issues,
            "pass_criteria": {
                "actual_improvement_rate": f"{actual_rate}% (30%+ 요구)",
                "fallback_rate": f"{fallback_rate}% (15% 이하 요구)",
                "rule_application_rate": f"{rule_rate}% (50%+ 요구)"
            }
        }
    
    def _print_user_report(self, report: Dict, output_file: Path):
        """사용자 친화적 리포트 출력"""
        print("\n" + "="*70)
        print("📚 **1권 책 실제 품질 평가 리포트**")
        print("="*70)
        
        book_info = report["book_info"]
        metrics = report["quality_metrics"]
        user_exp = report["user_experience"]
        verdict = report["verdict"]
        
        print(f"📄 분석 대상: {book_info['total_pages']}페이지")
        print(f"⏱️ 분석 기간: {book_info['analysis_period']}")
        print()
        
        print("🎯 **핵심 지표**")
        print(f"   📈 실제 개선률: {metrics['actual_improvement_rate']}%")
        print(f"   ⚠️ 폴백률: {metrics['fallback_rate']}%")  
        print(f"   📊 규칙 적용률: {metrics['rule_application_rate']}%")
        print()
        
        print("👤 **사용자 체감 분석**")
        print(f"   🌟 체감 점수: {user_exp['experience_score']}/100")
        print(f"   📖 가독성: {user_exp['readability_assessment']}")
        print(f"   💡 권장사항: {user_exp['recommendation']}")
        print()
        
        print("🏆 **최종 판정**")
        print(f"   📋 종합 등급: {verdict['overall_grade']}")
        if verdict['critical_issues']:
            print("   🚨 주요 문제:")
            for issue in verdict['critical_issues']:
                print(f"      - {issue}")
        print()
        
        # Before/After 샘플 미리보기
        samples = report["improvement_samples"]
        if samples:
            print(f"📝 **개선 샘플 미리보기** (총 {len(samples)}개)")
            for i, sample in enumerate(samples[:3]):  # 상위 3개만 출력
                print(f"   {i+1}. 페이지 {sample['page_number']} ({sample['improvement_type']} 개선)")
                print(f"      Before: {sample['before'][:100]}...")
                print(f"      After:  {sample['after'][:100]}...")
                print(f"      규칙: {', '.join(sample['applied_rules'])}")
                print()
        
        print(f"📄 상세 리포트 저장: {output_file}")
        print("="*70)

def main():
    """메인 실행 함수"""  
    assessor = BookQualityAssessment()
    result = assessor.analyze_book_quality(min_pages=8)
    
    if not result:
        print("⚠️ 분석할 데이터가 부족합니다.")
        print("1. pc_app.py로 최소 5페이지 처리 후 다시 실행하세요.")
        return
    
    print("\n✅ 분석 완료!")
    print("📊 이 리포트를 통해 실제 사용자 체감 품질을 확인하세요.")

if __name__ == "__main__":
    main()