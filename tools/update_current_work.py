#!/usr/bin/env python3
"""SnapTXT current_work.md 자동 업데이트 도구"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# 프로젝트 루트 및 문서 경로
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURRENT_WORK_PATH = PROJECT_ROOT / "docs" / "status" / "current_work.md"
DOCS_ROOT = PROJECT_ROOT / "docs"


def read_current_work() -> str:
    """current_work.md 파일 내용 읽기"""
    if not CURRENT_WORK_PATH.exists():
        raise FileNotFoundError(f"current_work.md를 찾을 수 없습니다: {CURRENT_WORK_PATH}")
    
    return CURRENT_WORK_PATH.read_text(encoding='utf-8')


def write_current_work(content: str) -> None:
    """current_work.md 파일에 내용 쓰기"""
    # 백업 생성
    backup_path = CURRENT_WORK_PATH.with_suffix(f".backup_{int(dt.datetime.now().timestamp())}.md")
    CURRENT_WORK_PATH.rename(backup_path)
    
    # 새 내용 저장
    CURRENT_WORK_PATH.write_text(content, encoding='utf-8')
    
    print(f"✅ current_work.md가 업데이트되었습니다.")
    print(f"📁 백업 파일: {backup_path.name}")


def get_file_info(file_path: Path) -> Tuple[bool, Optional[str], Optional[int]]:
    """파일 정보 확인 (존재여부, 수정일, 크기)"""
    if not file_path.exists():
        return False, None, None
    
    stat = file_path.stat()
    last_modified = dt.datetime.fromtimestamp(stat.st_mtime)
    
    # 사용자 친화적인 시간 표시
    delta = dt.datetime.now() - last_modified
    days = delta.days
    
    if days == 0:
        time_str = "오늘"
    elif days == 1:
        time_str = "어제" 
    elif days < 7:
        time_str = f"{days}일 전"
    else:
        time_str = last_modified.strftime("%Y-%m-%d")
    
    return True, time_str, stat.st_size


def add_planning_doc(name: str, category: str = "plans", description: str = "", status: str = "진행중") -> None:
    """새 기획서를 활성 기획서 목록에 추가"""
    
    content = read_current_work()
    
    # 파일 경로 구성
    filename = name.lower().replace(" ", "_").replace("-", "_") + ".md"
    
    # 카테고리별 실제 저장 위치 매핑
    category_mappings = {
        "plans": "plans",
        "reference": "reference", 
        "status": "status",
        "analysis": "plans"  # analysis는 plans 디렉터리에 저장됨
    }
    
    actual_category = category_mappings.get(category, category)
    relative_path = f"../{actual_category}/{filename}"
    full_path = DOCS_ROOT / actual_category / filename
    
    # 파일 존재 확인 및 정보 수집
    exists, time_str, size = get_file_info(full_path)
    if not exists:
        print(f"⚠️ 경고: 기획서 파일이 존재하지 않습니다: {full_path}")
        print(f"   먼저 python tools/create_planning_doc.py --name \"{name}\" --type {category} 를 실행하세요.")
        return
    
    # 기본 설명 생성
    if not description:
        if category == "plans":
            description = f"{name} 실행 계획"
        elif category == "reference":
            description = f"{name} 참고자료"
        elif category == "analysis":
            description = f"{name} 분석 보고서"
        else:
            description = f"{name} 관련 문서"
    
    # 새 기획서 항목
    new_entry = f"- 📋 [{name}]({relative_path}) - {description} ({status})"
    
    # 활성 기획서 섹션 찾기
    active_plans_pattern = r'(## ⚙️ 활성 기획서들 \(AI 참고용\))\n(.*?)(?=\n##|\n$)'
    match = re.search(active_plans_pattern, content, re.DOTALL)
    
    if match:
        header = match.group(1)
        current_entries = match.group(2).strip()
        
        # 중복 확인
        if name in current_entries:
            print(f"⚠️ '{name}' 기획서가 이미 활성 목록에 있습니다.")
            return
        
        # 새 항목 추가
        if current_entries:
            updated_entries = current_entries + f"\n{new_entry}"
        else:
            updated_entries = new_entry
        
        # 내용 교체
        new_section = f"{header}\n{updated_entries}\n"
        content = re.sub(active_plans_pattern, new_section, content, flags=re.DOTALL)
        
    else:
        # 활성 기획서 섹션이 없다면 생성
        # 메인 목표 섹션 앞에 삽입
        main_goals_pattern = r'(## 🎯 이번 주 메인 목표)'
        
        new_section = f"""## ⚙️ 활성 기획서들 (AI 참고용)
{new_entry}

\\1"""
        
        content = re.sub(main_goals_pattern, new_section, content)
    
    # 최종 업데이트 날짜 갱신
    today = dt.datetime.now().strftime("%Y-%m-%d")
    content = re.sub(r'_최종 업데이트: [^_]+_', f'_최종 업데이트: {today}_', content)
    
    write_current_work(content)
    print(f"📋 '{name}' 기획서가 활성 목록에 추가되었습니다.")
    print(f"   📂 카테고리: {category}")
    print(f"   📄 파일: {relative_path}")
    print(f"   📝 설명: {description}")


def complete_planning_doc(name: str) -> None:
    """기획서를 완료 상태로 변경"""
    
    content = read_current_work()
    
    # 활성 기획서에서 해당 항목 찾기
    pattern = rf'- 📋 \[{re.escape(name)}\]\([^)]+\) - ([^(]+)\(([^)]+)\)'
    match = re.search(pattern, content)
    
    if not match:
        print(f"❌ '{name}' 기획서를 활성 목록에서 찾을 수 없습니다.")
        return
    
    description = match.group(1).strip()
    current_status = match.group(2)
    
    # 상태를 완료로 변경
    updated_line = re.sub(
        rf'(- 📋 \[{re.escape(name)}\]\([^)]+\) - {re.escape(description)}) \([^)]+\)',
        r'\1 (완료)',
        match.group(0)
    )
    
    # 원래 줄을 새 줄로 교체
    content = content.replace(match.group(0), updated_line)
    
    # 최종 업데이트 날짜 갱신
    today = dt.datetime.now().strftime("%Y-%m-%d")
    content = re.sub(r'_최종 업데이트: [^_]+_', f'_최종 업데이트: {today}_', content)
    
    write_current_work(content)
    print(f"✅ '{name}' 기획서가 완료 상태로 변경되었습니다.")


def remove_planning_doc(name: str) -> None:
    """기획서를 활성 목록에서 제거"""
    
    content = read_current_work()
    
    # 해당 기획서 줄 찾아서 제거
    pattern = rf'- 📋 \[{re.escape(name)}\]\([^)]+\)[^\n]*\n?'
    
    if not re.search(pattern, content):
        print(f"❌ '{name}' 기획서를 활성 목록에서 찾을 수 없습니다.")
        return
    
    # 줄 제거
    content = re.sub(pattern, '', content)
    
    # 최종 업데이트 날짜 갱신
    today = dt.datetime.now().strftime("%Y-%m-%d")
    content = re.sub(r'_최종 업데이트: [^_]+_', f'_최종 업데이트: {today}_', content)
    
    write_current_work(content)
    print(f"🗑️ '{name}' 기획서가 활성 목록에서 제거되었습니다.")


def add_main_goal(goal: str, priority: str = "", status: str = "미완료") -> None:
    """메인 목표 추가"""
    
    content = read_current_work()
    
    # 우선순위 처리
    if priority and not priority.startswith("**"):
        priority = f"**{priority}**"
    
    # 새 목표 항목
    if priority:
        new_goal = f"- [ ] {priority}: {goal}"
    else:
        new_goal = f"- [ ] {goal}"
    
    # 메인 목표 섹션 찾기
    main_goals_pattern = r'(## 🎯 이번 주 메인 목표[^#]*?)(\n##|\n$)'
    match = re.search(main_goals_pattern, content, re.DOTALL)
    
    if match:
        current_section = match.group(1)
        
        # 중복 확인 (간단한 키워드 매칭)
        goal_keywords = goal.lower().split()[:3]  # 처음 3단어로 중복 확인
        if any(keyword in current_section.lower() for keyword in goal_keywords):
            print(f"⚠️ 유사한 목표가 이미 존재할 수 있습니다: '{goal}'")
            confirm = input("계속 추가하시겠습니까? (y/N): ")
            if confirm.lower() not in ['y', 'yes']:
                print("작업이 취소되었습니다.")
                return
        
        # 새 목표 추가
        updated_section = current_section + f"{new_goal}\n"
        
        # 내용 교체
        rest_of_content = match.group(2)
        content = content.replace(match.group(0), updated_section + rest_of_content)
    else:
        print("❌ 메인 목표 섹션을 찾을 수 없습니다.")
        return
    
    # 최종 업데이트 날짜 갱신
    today = dt.datetime.now().strftime("%Y-%m-%d")
    content = re.sub(r'_최종 업데이트: [^_]+_', f'_최종 업데이트: {today}_', content)
    
    write_current_work(content)
    print(f"🎯 새 메인 목표가 추가되었습니다: '{goal}'")


def list_active_plans() -> None:
    """현재 활성 기획서 목록 출력"""
    
    content = read_current_work()
    
    # 활성 기획서 추출
    pattern = r'- 📋 \[([^\]]+)\]\(([^)]+)\) - ([^(]+)\(([^)]+)\)'
    matches = re.findall(pattern, content)
    
    if not matches:
        print("현재 활성 기획서가 없습니다.")
        return
    
    print("📋 현재 활성 기획서:")
    print("-" * 60)
    
    for name, path, description, status in matches:
        # 실제 파일 경로 구성
        if path.startswith('../'):
            file_path = DOCS_ROOT / path[3:]
        else:
            file_path = PROJECT_ROOT / path
        
        exists, time_str, size = get_file_info(file_path)
        
        status_icon = "✅" if exists else "❌"
        size_str = f"({size//1024}KB)" if size and size > 1024 else f"({size}B)" if size else "(없음)"
        
        print(f"  {status_icon} {name}")
        print(f"     📄 {path}")
        print(f"     📝 {description.strip()}")
        print(f"     ⏰ {status} - 수정: {time_str or '알 수 없음'} {size_str}")
        print()


def main():
    parser = argparse.ArgumentParser(description="current_work.md 자동 업데이트 도구")
    
    # 기획서 관리
    parser.add_argument("--add-planning-doc", type=str, metavar="NAME",
                       help="새 기획서를 활성 목록에 추가")
    parser.add_argument("--category", type=str, default="plans",
                       choices=["plans", "reference", "status", "analysis"],
                       help="기획서 카테고리 (기본: plans)")
    parser.add_argument("--description", type=str, default="",
                       help="기획서 설명")
    parser.add_argument("--status", type=str, default="진행중",
                       help="기획서 상태 (기본: 진행중)")
    
    parser.add_argument("--complete", type=str, metavar="NAME",
                       help="기획서를 완료 상태로 변경")
    parser.add_argument("--remove", type=str, metavar="NAME", 
                       help="기획서를 활성 목록에서 제거")
    
    # 메인 목표 관리
    parser.add_argument("--add-goal", type=str, metavar="GOAL",
                       help="새 메인 목표 추가")
    parser.add_argument("--priority", type=str, default="",
                       help="목표 우선순위 (P1, P2, P3 등)")
    
    # 조회
    parser.add_argument("--list-plans", action="store_true",
                       help="현재 활성 기획서 목록 출력")
    
    args = parser.parse_args()
    
    try:
        if args.add_planning_doc:
            add_planning_doc(args.add_planning_doc, args.category, args.description, args.status)
        elif args.complete:
            complete_planning_doc(args.complete)
        elif args.remove:
            remove_planning_doc(args.remove)
        elif args.add_goal:
            add_main_goal(args.add_goal, args.priority)
        elif args.list_plans:
            list_active_plans()
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"❌ 오류: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()