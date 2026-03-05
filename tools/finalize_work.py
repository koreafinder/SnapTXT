#!/usr/bin/env python3
"""SnapTXT 작업 완료 처리 도구 - 완료된 기획서 정리 및 Git 워크플로우"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# 프로젝트 루트 및 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURRENT_WORK_PATH = PROJECT_ROOT / "docs" / "status" / "current_work.md"
EXPERIMENTS_RESULTS = PROJECT_ROOT / "experiments" / "results"
DOCS_ROOT = PROJECT_ROOT / "docs"


def get_git_status() -> bool:
    """Git 저장소 상태 확인"""
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=PROJECT_ROOT)
        return result.returncode == 0 and bool(result.stdout.strip())
    except FileNotFoundError:
        return False


def get_staged_files() -> List[str]:
    """스테이징된 파일 목록 반환"""
    try:
        result = subprocess.run(['git', 'diff', '--staged', '--name-only'], 
                              capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=PROJECT_ROOT)
        if result.returncode == 0:
            return [f for f in result.stdout.strip().split('\n') if f]
        return []
    except FileNotFoundError:
        return []


def move_completed_docs(completed_docs: List[str], dry_run: bool = False) -> List[Tuple[Path, Path]]:
    """완료된 기획서들을 experiments/results/로 이동"""
    
    if not completed_docs:
        print("이동할 완료된 문서가 없습니다.")
        return []
    
    # experiments/results 디렉터리 생성
    EXPERIMENTS_RESULTS.mkdir(parents=True, exist_ok=True)
    
    moved_files = []
    
    for doc_name in completed_docs:
        # 가능한 위치에서 파일 찾기
        potential_paths = [
            DOCS_ROOT / "plans" / f"{doc_name}.md",
            DOCS_ROOT / "reference" / f"{doc_name}.md", 
            DOCS_ROOT / "status" / f"{doc_name}.md"
        ]
        
        source_path = None
        for path in potential_paths:
            if path.exists():
                source_path = path
                break
        
        if not source_path:
            print(f"⚠️ '{doc_name}' 파일을 찾을 수 없습니다.")
            continue
        
        # 목적지 경로
        timestamp = dt.datetime.now().strftime("%Y%m%d")
        dest_filename = f"{doc_name}_completed_{timestamp}.md"
        dest_path = EXPERIMENTS_RESULTS / dest_filename
        
        # 중복 확인
        counter = 1
        while dest_path.exists():
            dest_filename = f"{doc_name}_completed_{timestamp}_{counter:02d}.md"
            dest_path = EXPERIMENTS_RESULTS / dest_filename
            counter += 1
        
        if dry_run:
            print(f"[DRY RUN] {source_path.relative_to(PROJECT_ROOT)} → {dest_path.relative_to(PROJECT_ROOT)}")
            moved_files.append((source_path, dest_path))
        else:
            try:
                shutil.move(str(source_path), str(dest_path))
                print(f"📁 이동 완료: {source_path.name} → {dest_path.name}")
                moved_files.append((source_path, dest_path))
            except Exception as e:
                print(f"❌ 이동 실패 ({doc_name}): {e}")
    
    return moved_files


def update_current_work_for_completion(completed_docs: List[str]) -> None:
    """current_work.md에서 완료된 기획서 정리"""
    
    if not CURRENT_WORK_PATH.exists():
        print("❌ current_work.md를 찾을 수 없습니다.")
        return
    
    content = CURRENT_WORK_PATH.read_text(encoding='utf-8')
    original_content = content
    
    # 완료된 기획서들의 상태를 완료로 변경하고 제거
    for doc_name in completed_docs:
        # 해당 기획서 줄 찾기
        import re
        pattern = rf'- 📋 \[{re.escape(doc_name)}\]\([^)]+\)[^\n]*\n?'
        
        if re.search(pattern, content):
            print(f"🗑️ 활성 목록에서 '{doc_name}' 제거")
            content = re.sub(pattern, '', content)
    
    # 최종 업데이트 날짜 갱신
    today = dt.datetime.now().strftime("%Y-%m-%d")
    content = re.sub(r'_최종 업데이트: [^_]+_', f'_최종 업데이트: {today}_', content)
    
    if content != original_content:
        # 백업 생성
        backup_path = CURRENT_WORK_PATH.with_suffix(f".backup_{int(dt.datetime.now().timestamp())}.md")
        CURRENT_WORK_PATH.rename(backup_path)
        
        # 새 내용 저장
        CURRENT_WORK_PATH.write_text(content, encoding='utf-8')
        
        print(f"✅ current_work.md가 업데이트되었습니다.")
        print(f"📁 백업: {backup_path.name}")
    else:
        print("ℹ️ current_work.md에 변경사항이 없습니다.")


def generate_commit_message(moved_files: List[Tuple[Path, Path]], custom_message: str = "") -> str:
    """Git 커밋 메시지 자동 생성"""
    
    if custom_message:
        return custom_message
    
    if not moved_files:
        return "docs: update work completion status"
    
    moved_count = len(moved_files)
    
    if moved_count == 1:
        doc_name = moved_files[0][0].stem
        return f"docs: complete {doc_name} and move to results"
    else:
        return f"docs: complete {moved_count} documents and reorganize structure"


def git_add_and_commit(commit_message: str, dry_run: bool = False) -> bool:
    """Git add 및 commit 실행"""
    
    if not get_git_status():
        print("ℹ️ Git 변경사항이 없습니다.")
        return True
    
    try:
        if dry_run:
            print(f"[DRY RUN] git add -A")
            print(f"[DRY RUN] git commit -m \"{commit_message}\"")
            return True
        
        # git add -A
        result = subprocess.run(['git', 'add', '-A'], 
                              capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=PROJECT_ROOT)
        if result.returncode != 0:
            print(f"❌ git add 실패: {result.stderr}")
            return False
        
        # git commit
        result = subprocess.run(['git', 'commit', '-m', commit_message], 
                              capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=PROJECT_ROOT)
        if result.returncode != 0:
            print(f"❌ git commit 실패: {result.stderr}")
            if "nothing to commit" in result.stdout:
                print("ℹ️ 커밋할 변경사항이 없습니다.")
                return True
            return False
        
        print(f"✅ Git 커밋 완료: {commit_message}")
        return True
        
    except FileNotFoundError:
        print("❌ Git이 설치되지 않았거나 PATH에 없습니다.")
        return False


def git_push(dry_run: bool = False) -> bool:
    """Git push 실행"""
    
    try:
        if dry_run:
            print(f"[DRY RUN] git push")
            return True
        
        result = subprocess.run(['git', 'push'], 
                              capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=PROJECT_ROOT)
        if result.returncode != 0:
            print(f"❌ git push 실패: {result.stderr}")
            return False
        
        print(f"✅ Git push 완료")
        return True
        
    except FileNotFoundError:
        print("❌ Git이 설치되지 않았거나 PATH에 없습니다.")
        return False


def run_docs_verification() -> bool:
    """문서 시스템 무결성 검증"""
    
    try:
        # check_docs.bat ci 실행 - UTF-8 인코딩으로 디코딩 오류 방지
        result = subprocess.run(['cmd', '/c', 'check_docs.bat', 'ci'], 
                              capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=PROJECT_ROOT)
        
        if result.returncode == 0:
            print("✅ 문서 시스템 검증 통과")
            return True
        else:
            print("❌ 문서 시스템 검증 실패:")
            print(result.stdout)
            return False
            
    except Exception as e:
        print(f"❌ 문서 검증 중 치명적 오류: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="작업 완료 처리 및 정리 도구")
    
    parser.add_argument("--complete-docs", type=str, nargs="+", 
                       help="완료된 기획서 이름 목록")
    parser.add_argument("--commit-msg", type=str, default="",
                       help="Git 커밋 메시지 (기본: 자동 생성)")
    
    parser.add_argument("--no-move", action="store_true",
                       help="파일 이동 건너뛰기")
    parser.add_argument("--no-git", action="store_true",
                       help="Git 작업 건너뛰기")
    parser.add_argument("--no-push", action="store_true", 
                       help="Git push 건너뛰기")
    parser.add_argument("--no-verify", action="store_true",
                       help="문서 검증 건너뛰기")
    
    parser.add_argument("--dry-run", action="store_true",
                       help="실제 작업 없이 시뮬레이션만 실행")
    
    # 개별 작업
    parser.add_argument("--git-only", action="store_true",
                       help="Git 작업만 실행")
    parser.add_argument("--docs-only", action="store_true", 
                       help="문서 정리만 실행")
    
    args = parser.parse_args()
    
    print("🎉 작업 완료 처리 시작...")
    print("=" * 50)
    
    moved_files = []
    
    # 1. 문서 정리 작업
    if not args.git_only:
        if args.complete_docs and not args.no_move:
            print("\n📁 [1/4] 완료된 기획서 이동...")
            print("-" * 30)
            moved_files = move_completed_docs(args.complete_docs, args.dry_run)
            
            print(f"\n📝 [2/4] current_work.md 업데이트...")
            print("-" * 30)
            if not args.dry_run:
                update_current_work_for_completion(args.complete_docs)
            else:
                print("[DRY RUN] current_work.md 업데이트 시뮬레이션")
    
    # 2. Git 작업
    if not args.docs_only and not args.no_git:
        print(f"\n🔄 [3/4] Git 커밋 및 푸시...")
        print("-" * 30)
        
        commit_msg = generate_commit_message(moved_files, args.commit_msg)
        print(f"📝 커밋 메시지: {commit_msg}")
        
        if git_add_and_commit(commit_msg, args.dry_run):
            if not args.no_push:
                git_push(args.dry_run)
        else:
            print("❌ Git 커밋 실패. push를 건너뜁니다.")
    
    # 3. 문서 검증
    if not args.no_verify:
        print(f"\n🔍 [4/4] 문서 시스템 검증...")
        print("-" * 30)
        
        if not args.dry_run:
            if not run_docs_verification():
                print("❌ 문서 검증 실패로 인해 작업을 중단합니다.")
                sys.exit(1)
        else:
            print("[DRY RUN] 문서 검증 시뮬레이션")
    
    print("\n" + "=" * 50)
    if args.dry_run:
        print("🎭 시뮬레이션 완료! 실제 작업은 --dry-run 옵션을 제거하고 다시 실행하세요.")
    else:
        print("✅ 작업 완료 처리가 모두 끝났습니다!")
    
    if moved_files:
        print(f"\n📊 처리 결과:")
        print(f"   📁 이동된 파일: {len(moved_files)}개")
        for source, dest in moved_files:
            print(f"      • {source.name} → {dest.name}")


if __name__ == "__main__":
    main()