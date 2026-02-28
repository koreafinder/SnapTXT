#!/usr/bin/env python3
"""SnapTXT 문서 상태 점검 스크립트."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

DOCS_ROOT = Path(__file__).resolve().parents[1] / "docs"

REQUIRED_FILES: List[Tuple[str, str]] = [
    ("foundation", "foundation/Project_Memory.md"),
    ("foundation", "foundation/Architecture.md"),
    ("status", "status/Current_Work.md"),
    ("status", "status/progress_flow.md"),
    ("reference", "README.md"),
]

OPTIONAL_FILES: List[Tuple[str, str]] = [
    ("plans", "plans/restructure_plan.md"),
    ("plans", "plans/future_improvement_plan.md"),
    ("reference", "PRACTICAL_GUIDE.md"),
]

CONTEXT_FLOW: List[Tuple[str, str]] = [
    ("철학", "foundation/Project_Memory.md"),
    ("아키텍처", "foundation/Architecture.md"),
    ("진행 현황", "status/Current_Work.md"),
    ("세부 계획", "plans/restructure_plan.md"),
]


def human_time(ts: float | None) -> str:
    if ts is None:
        return "-"
    dt_obj = dt.datetime.fromtimestamp(ts)
    delta = dt.datetime.now() - dt_obj
    days = delta.days
    if days == 0:
        return "오늘"
    if days == 1:
        return "어제"
    return f"{days}일 전"


def format_row(tag: str, rel_path: str, exists: bool, mtime: float | None) -> str:
    status = "OK" if exists else "MISS"
    age = human_time(mtime) if exists else "-"
    return f"{status:>4} | {tag:<10} | {rel_path:<30} | {age:<8}"


def check_files(entries: Iterable[Tuple[str, str]], kind: str) -> None:
    print(f"\n[{kind}]")
    print("stat | category  | file                          | updated")
    print("-----+-----------+------------------------------+---------")
    for tag, rel_path in entries:
        rel = Path("docs") / rel_path
        full = DOCS_ROOT / rel_path
        exists = full.exists()
        mtime = full.stat().st_mtime if exists else None
        print(format_row(tag, str(rel), exists, mtime))


def print_context_flow() -> None:
    print("\n[문서 워크플로]")
    for idx, (label, rel_path) in enumerate(CONTEXT_FLOW, start=1):
        print(f"{idx}. {label}: docs/{rel_path}")


def open_plan_file(rel_path: str) -> None:
    target = DOCS_ROOT / rel_path
    if not target.exists():
        return
    try:
        if os.name == "nt":
            os.startfile(target)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(target)], check=False)
        else:
            subprocess.run(["xdg-open", str(target)], check=False)
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="SnapTXT 문서 상태를 보여줍니다.")
    parser.add_argument("--show-optional", action="store_true", help="선택 문서도 함께 표시")
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="세부 기획 문서를 자동으로 열지 않습니다.",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI 모드: 누락된 파일이 있으면 exit code 1로 종료",
    )
    args = parser.parse_args()

    if not DOCS_ROOT.exists():
        raise SystemExit("docs 디렉터리를 찾을 수 없습니다. 루트에서 실행하세요.")

    missing_required = []
    missing_optional = []
    
    # Check required files and collect missing ones
    if args.ci:
        for tag, rel_path in REQUIRED_FILES:
            full = DOCS_ROOT / rel_path
            if not full.exists():
                missing_required.append((tag, rel_path))
        if args.show_optional:
            for tag, rel_path in OPTIONAL_FILES:
                full = DOCS_ROOT / rel_path
                if not full.exists():
                    missing_optional.append((tag, rel_path))
    
    check_files(REQUIRED_FILES, "필수")
    if args.show_optional:
        check_files(OPTIONAL_FILES, "선택")

    if not args.ci:
        print_context_flow()
        if not args.no_open:
            open_plan_file("plans/restructure_plan.md")

    print("\n가이드: docs/README.md 를 먼저 열어 문서 작성 규칙을 확인하세요.")
    
    # CI mode: exit with error if any required files are missing
    if args.ci and missing_required:
        print(f"\n❌ CI 검증 실패: {len(missing_required)}개 필수 문서 누락")
        for tag, rel_path in missing_required:
            print(f"  - {rel_path}")
        sys.exit(1)
    elif args.ci:
        print("\n✅ CI 검증 통과: 모든 필수 문서 존재")


if __name__ == "__main__":
    main()
