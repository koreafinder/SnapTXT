#!/usr/bin/env python3
"""SnapTXT 현재 상황 요약 출력 스크립트 - AI 협업을 위한 컨텍스트 제공"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Optional

# 프로젝트 루트 디렉터리
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURRENT_WORK_PATH = PROJECT_ROOT / "docs" / "status" / "current_work.md"


def parse_current_work() -> Dict[str, any]:
    """current_work.md 파일을 파싱해서 구조화된 정보 반환"""
    if not CURRENT_WORK_PATH.exists():
        return {"active_plans": [], "main_goals": [], "error": f"current_work.md not found at {CURRENT_WORK_PATH}"}
    
    content = CURRENT_WORK_PATH.read_text(encoding='utf-8')
    
    # 활성 기획서들 파싱 (📋 [filename](path) - description 형태)
    active_plans = []
    plan_pattern = r'- 📋 \[([^\]]+)\]\(([^)]+)\) - ([^(]+)(?:\(([^)]+)\))?'
    
    for match in re.finditer(plan_pattern, content):
        plan_name = match.group(1)
        plan_path = match.group(2)
        description = match.group(3).strip()
        status = match.group(4) if match.group(4) else "상태 없음"
        
        # 상대 경로를 절대 경로로 변환
        if plan_path.startswith('../'):
            full_path = PROJECT_ROOT / "docs" / plan_path[3:]
        else:
            full_path = PROJECT_ROOT / plan_path
            
        active_plans.append({
            'name': plan_name,
            'path': plan_path,
            'full_path': full_path,
            'description': description,
            'status': status
        })
    
    # 이번 주 메인 목표 파싱 (- [ ] 형태)
    main_goals = []
    goal_section_start = content.find('## 🎯 이번 주 메인 목표')
    if goal_section_start != -1:
        goal_section = content[goal_section_start:content.find('\n##', goal_section_start)]
        goal_pattern = r'- \[ \] (.+)'
        
        for match in re.finditer(goal_pattern, goal_section):
            goal_text = match.group(1).strip()
            main_goals.append(goal_text)
    
    return {
        "active_plans": active_plans,
        "main_goals": main_goals,
        "last_update": extract_last_update(content)
    }


def extract_last_update(content: str) -> Optional[str]:
    """최종 업데이트 날짜 추출"""
    update_match = re.search(r'_최종 업데이트: ([^_]+)_', content)
    return update_match.group(1).strip() if update_match else None


def check_file_status(file_path: Path) -> Dict[str, any]:
    """파일 존재 여부와 수정일 체크"""
    if not file_path.exists():
        return {"exists": False, "last_modified": None, "size": 0}
    
    stat = file_path.stat()
    last_modified = dt.datetime.fromtimestamp(stat.st_mtime)
    
    return {
        "exists": True,
        "last_modified": last_modified,
        "size": stat.st_size,
        "human_time": human_time(stat.st_mtime)
    }


def human_time(timestamp: float) -> str:
    """사용자 친화적인 시간 표시"""
    dt_obj = dt.datetime.fromtimestamp(timestamp)
    delta = dt.datetime.now() - dt_obj
    days = delta.days
    hours = delta.seconds // 3600
    
    if days == 0:
        if hours == 0:
            return "방금 전"
        elif hours < 3:
            return f"{hours}시간 전"
        else:
            return "오늘"
    elif days == 1:
        return "어제"
    elif days < 7:
        return f"{days}일 전"
    else:
        return dt_obj.strftime("%Y-%m-%d")


def show_active_plans(parsed_data: Dict[str, any]) -> None:
    """활성 기획서 목록 표시"""
    print("## 📋 활성 기획서들 (AI 컨텍스트)")
    print()
    
    if not parsed_data["active_plans"]:
        print("현재 활성 기획서가 없습니다.")
        return
    
    max_name_len = max(len(plan['name']) for plan in parsed_data["active_plans"])
    
    print("파일명".ljust(max_name_len) + " | 상태     | 수정일   | 크기   | 설명")
    print("-" * max_name_len + "-+---------+----------+--------+-" + "-" * 30)
    
    for plan in parsed_data["active_plans"]:
        file_status = check_file_status(plan['full_path'])
        
        if file_status["exists"]:
            status_icon = "✅"
            time_str = file_status["human_time"]
            size_str = f"{file_status['size']//1024}KB" if file_status['size'] > 1024 else f"{file_status['size']}B"
        else:
            status_icon = "❌"
            time_str = "없음"
            size_str = "-"
        
        plan_status = plan['status'][:8] if len(plan['status']) <= 8 else plan['status'][:5] + "..."
        description = plan['description'][:30] if len(plan['description']) <= 30 else plan['description'][:27] + "..."
        
        print(f"{plan['name'].ljust(max_name_len)} | {status_icon} {plan_status:<6} | {time_str:<8} | {size_str:<6} | {description}")


def show_main_goals(parsed_data: Dict[str, any]) -> None:
    """이번 주 메인 목표 표시"""
    print("\n## 🎯 이번 주 메인 목표")
    print()
    
    if not parsed_data["main_goals"]:
        print("설정된 메인 목표가 없습니다.")
        return
    
    for i, goal in enumerate(parsed_data["main_goals"], 1):
        print(f"{i}. {goal}")


def show_quick_summary(parsed_data: Dict[str, any]) -> None:
    """빠른 요약 정보"""
    print("## 🚀 빠른 상황 요약")
    print()
    
    last_update = parsed_data.get("last_update", "알 수 없음")
    print(f"📅 **최종 업데이트**: {last_update}")
    
    active_count = len(parsed_data["active_plans"])
    existing_count = sum(1 for plan in parsed_data["active_plans"] 
                        if check_file_status(plan['full_path'])["exists"])
    
    print(f"📋 **활성 기획서**: {existing_count}/{active_count}개 파일 존재")
    print(f"🎯 **메인 목표**: {len(parsed_data['main_goals'])}개 설정")
    
    # 최근 수정된 기획서 찾기
    recent_plan = None
    recent_time = None
    
    for plan in parsed_data["active_plans"]:
        file_status = check_file_status(plan['full_path'])
        if file_status["exists"] and file_status["last_modified"]:
            if recent_time is None or file_status["last_modified"] > recent_time:
                recent_time = file_status["last_modified"]
                recent_plan = plan
    
    if recent_plan:
        print(f"🔥 **최근 활성**: {recent_plan['name']} ({human_time(recent_time.timestamp())})")


def main():
    parser = argparse.ArgumentParser(description="SnapTXT 현재 상황 요약")
    parser.add_argument("--show-active-plans", action="store_true", 
                       help="활성 기획서 목록 표시")
    parser.add_argument("--show-main-goals", action="store_true",
                       help="메인 목표 목록 표시")  
    parser.add_argument("--quick-summary", action="store_true",
                       help="빠른 요약 정보만 표시")
    parser.add_argument("--all", action="store_true",
                       help="모든 정보 표시")
    
    args = parser.parse_args()
    
    # current_work.md 파싱
    parsed_data = parse_current_work()
    
    if "error" in parsed_data:
        print(f"❌ 오류: {parsed_data['error']}", file=sys.stderr)
        sys.exit(1)
    
    # 인자에 따른 출력
    if args.all or (not any([args.show_active_plans, args.show_main_goals, args.quick_summary])):
        # 기본값: 모든 정보 표시
        show_quick_summary(parsed_data)
        print()
        show_active_plans(parsed_data) 
        print()
        show_main_goals(parsed_data)
    else:
        if args.quick_summary:
            show_quick_summary(parsed_data)
        if args.show_active_plans:
            if args.quick_summary:
                print()
            show_active_plans(parsed_data)
        if args.show_main_goals:
            if args.quick_summary or args.show_active_plans:
                print()
            show_main_goals(parsed_data)


if __name__ == "__main__":
    main()