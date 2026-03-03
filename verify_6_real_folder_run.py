#!/usr/bin/env python3
"""
실전 품질 체크 자동화: verify_6_real_folder_run.py

pc_app.py로 폴더 처리 후 production_reports/를 자동 분석하여
운영 품질 지표를 한 화면에 출력
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import glob

class ProductionQualityAnalyzer:
    """Production 운영 품질 분석기"""
    
    def __init__(self, reports_dir: str = "production_reports"):
        self.reports_dir = Path(reports_dir)
        self.analysis_time = datetime.now()
        
        # 분석 결과 저장
        self.total_pages = 0 
        self.rules_applied_pages = 0
        self.rule_usage_count = {}
        self.total_char_changes = 0
        self.exception_count = 0
        self.fallback_count = 0
        
    def analyze_recent_reports(self, hours_back: int = 24) -> Dict:
        """최근 N시간 내 리포트 분석"""
        
        print("=" * 70)
        print("📊 **실전 Production 품질 분석 리포트**")
        print("=" * 70)
        print(f"🕐 분석 시간: {self.analysis_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 리포트 폴더: {self.reports_dir.absolute()}")
        
        # 리포트 디렉토리 존재 확인
        if not self.reports_dir.exists():
            print(f"❌ 리포트 폴더 없음: {self.reports_dir}")
            return self._generate_empty_report()
            
        # 최근 리포트 파일 수집
        cutoff_time = self.analysis_time - timedelta(hours=hours_back)
        recent_reports = self._collect_recent_reports(cutoff_time)
        
        print(f"📄 최근 {hours_back}시간 내 리포트: {len(recent_reports)}개")
        
        if not recent_reports:
            print("⚠️ 분석할 리포트 없음")
            return self._generate_empty_report()
            
        # 각 리포트 분석
        self._analyze_individual_reports(recent_reports)
        
        # 결과 출력
        return self._generate_quality_summary()
        
    def _collect_recent_reports(self, cutoff_time: datetime) -> List[Path]:
        """최근 리포트 파일 수집"""
        
        recent_reports = []
        
        # processing_report와 approval_request 모두 수집
        patterns = [
            "processing_report_*.json",
            "approval_request_*.json"
        ]
        
        for pattern in patterns:
            for report_file in self.reports_dir.glob(pattern):
                try:
                    # 파일 이름에서 타임스탬프 추출
                    file_time = datetime.fromtimestamp(report_file.stat().st_mtime)
                    if file_time >= cutoff_time:
                        recent_reports.append(report_file)
                except Exception as e:
                    print(f"⚠️ 리포트 파일 처리 실패: {report_file.name} - {e}")
                    
        # 시간순 정렬
        recent_reports.sort(key=lambda x: x.stat().st_mtime)
        return recent_reports
        
    def _analyze_individual_reports(self, report_files: List[Path]):
        """개별 리포트 분석"""
        
        print("\n" + "-" * 50)
        print("🔍 개별 리포트 분석 중...")
        print("-" * 50)
        
        for report_file in report_files:
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                    
                self._process_single_report(report_file.name, report_data)
                
            except Exception as e:
                print(f"⚠️ 리포트 파싱 실패: {report_file.name} - {e}")
                self.exception_count += 1
                
    def _process_single_report(self, filename: str, data: Dict):
        """단일 리포트 처리"""
        
        self.total_pages += 1
        
        # 리포트 타입 판별
        if "approval_request" in filename:
            # Conservative 모드로 사용자 승인 요청
            self.fallback_count += 1
            print(f"📋 {filename[:30]}... : Conservative 모드 - 사용자 승인 필요")
            return
            
        # Processing report 분석
        result = data.get("result", {})
        applied_rules = result.get("applied_rules", [])
        
        # 적용된 규칙 개수
        if len(applied_rules) > 0:
            self.rules_applied_pages += 1
            
            # 규칙별 사용 통계
            for rule_info in applied_rules:
                rule_id = rule_info.get("rule_id", "unknown")
                self.rule_usage_count[rule_id] = self.rule_usage_count.get(rule_id, 0) + 1
                
        # 텍스트 변화량
        text_metrics = data.get("text_metrics", {})
        original_len = text_metrics.get("original_length", 0)
        fixed_len = text_metrics.get("fixed_length", 0)
        char_change = abs(fixed_len - original_len)
        self.total_char_changes += char_change
        
        # Fallback 규칙 사용 체크
        source_info = data.get("source_of_truth", {})
        if source_info.get("fallback_used", False):
            self.fallback_count += 1
            
        print(f"📄 {filename[:30]}... : {len(applied_rules)}개 규칙, {char_change}자 변화")
        
    def _generate_quality_summary(self) -> Dict:
        """품질 요약 리포트 생성"""
        
        print("\n" + "=" * 70)
        print("🎯 **실전 Production 품질 요약**") 
        print("=" * 70)
        
        # 1. 총 페이지 수
        print(f"📊 총 pages: {self.total_pages}개")
        
        # 2. rules_applied>0 비율
        rules_applied_ratio = (self.rules_applied_pages / self.total_pages * 100) if self.total_pages > 0 else 0
        print(f"📈 rules_applied>0 비율: {self.rules_applied_pages}/{self.total_pages} ({rules_applied_ratio:.1f}%)")
        
        # 3. top applied rules
        if self.rule_usage_count:
            sorted_rules = sorted(self.rule_usage_count.items(), key=lambda x: x[1], reverse=True)
            top_rules = sorted_rules[:5]  # 상위 5개
            print(f"🏆 Top applied rules:")
            for i, (rule_id, count) in enumerate(top_rules, 1):
                print(f"   {i}. {rule_id}: {count}회")
        else:
            print(f"🏆 Top applied rules: 없음")
            
        # 4. 평균 Δlen(문자수 변화)  
        avg_char_change = (self.total_char_changes / self.total_pages) if self.total_pages > 0 else 0
        print(f"📏 평균 Δlen(문자수 변화): {avg_char_change:.1f}자/페이지")
        
        # 5. 예외/폴백 발생 횟수
        print(f"⚠️ 예외/폴백 발생 횟수: {self.exception_count + self.fallback_count}회")
        print(f"   - 예외: {self.exception_count}회")
        print(f"   - Fallback/Conservative: {self.fallback_count}회")
        
        # 품질 점수 계산
        quality_score = self._calculate_quality_score(rules_applied_ratio, self.exception_count)
        print(f"\n🌟 **종합 품질 점수**: {quality_score:.1f}/100")
        
        # 권장사항
        self._print_recommendations(rules_applied_ratio, quality_score)
        
        return {
            "total_pages": self.total_pages,
            "rules_applied_ratio": rules_applied_ratio,
            "top_rules": dict(sorted(self.rule_usage_count.items(), key=lambda x: x[1], reverse=True)[:5]),
            "avg_char_change": avg_char_change,
            "exception_count": self.exception_count,
            "fallback_count": self.fallback_count,
            "quality_score": quality_score
        }
        
    def _generate_empty_report(self) -> Dict:
        """빈 리포트 생성"""
        print("📊 총 pages: 0개")
        print("📈 rules_applied>0 비율: 0/0 (0.0%)")
        print("🏆 Top applied rules: 없음")
        print("📏 평균 Δlen(문자수 변화): 0.0자/페이지") 
        print("⚠️ 예외/폴백 발생 횟수: 0회")
        print("\n🌟 **종합 품질 점수**: 0.0/100")
        
        return {
            "total_pages": 0,
            "rules_applied_ratio": 0.0,
            "top_rules": {},
            "avg_char_change": 0.0,
            "exception_count": 0,
            "fallback_count": 0,
            "quality_score": 0.0
        }
        
    def _calculate_quality_score(self, applied_ratio: float, exception_count: int) -> float:
        """종합 품질 점수 계산 (0-100)"""
        
        # 기본 점수 (적용 비율 기반)
        base_score = min(applied_ratio, 80)  # 최대 80점
        
        # 예외 페널티 (예외 1개당 -5점)
        exception_penalty = exception_count * 5
        
        # 최종 점수
        final_score = max(0, base_score - exception_penalty)
        
        return final_score
        
    def _print_recommendations(self, applied_ratio: float, quality_score: float):
        """운영 권장사항 출력"""
        
        print("\n" + "=" * 70)
        print("💡 **운영 권장사항**")
        print("=" * 70)
        
        if quality_score >= 80:
            print("✅ 우수: Production 시스템이 안정적으로 작동 중")
        elif quality_score >= 60:
            print("⚠️ 양호: 일부 개선 필요")
            if applied_ratio < 50:
                print("   - Conservative 모드 → Standard 모드 전환 검토")
        elif quality_score >= 40:
            print("🔶 보통: 규칙 적용률 개선 필요")
            print("   - 활성 규칙 추가 또는 패턴 강화")
            print("   - Domain/Safety 모드 조정")
        else:
            print("🔺 미흡: 즉시 점검 필요")
            print("   - Source of Truth 경로 확인")
            print("   - 예외 로그 분석")
            print("   - Fallback 규칙 점검")
            
def run_quality_analysis(hours_back: int = 24):
    """품질 분석 실행"""
    
    analyzer = ProductionQualityAnalyzer()
    result = analyzer.analyze_recent_reports(hours_back)
    
    # JSON 리포트도 저장
    report_file = f"quality_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "analysis_time": analyzer.analysis_time.isoformat(),
                "hours_analyzed": hours_back,
                "results": result
            }, f, indent=2, ensure_ascii=False)
            
        print(f"\n📄 상세 분석 리포트 저장: {report_file}")
        
    except Exception as e:
        print(f"⚠️ 분석 리포트 저장 실패: {e}")
        
    return result

if __name__ == "__main__":
    print("🚀 실전 Production 품질 체크 시작...")
    print("pc_app.py 폴더 처리 후 이 스크립트를 실행하여 품질을 확인하세요")
    print()
    
    # 최근 24시간 분석
    run_quality_analysis(24)