#!/usr/bin/env python3
"""SnapTXT 프로젝트 안전 이동 스크립트"""

import shutil
import os
from pathlib import Path

def safe_project_migration():
    """OneDrive에서 로컬로 안전하게 프로젝트 이동"""
    
    # 현재 경로 (OneDrive)
    current_path = Path(__file__).parent
    print(f"현재 위치: {current_path}")
    
    # 새 경로 (로컬)
    new_path = Path("C:/dev/SnapTXT")
    
    print("=== SnapTXT 프로젝트 이동 계획 ===")
    print(f"source: {current_path}")
    print(f"target: {new_path}")
    
    # 필수 파일/폴더 체크
    essential_items = [
        'snaptxt/',
        'tools/', 
        'learning_data/',
        'main.py',
        'requirements.txt'
    ]
    
    print("\n필수 항목 체크:")
    for item in essential_items:
        item_path = current_path / item
        exists = item_path.exists()
        print(f"  {'✅' if exists else '❌'} {item}")
        
    # 예상 용량 계산
    total_size = sum(
        sum(f.stat().st_size for f in p.rglob('*') if f.is_file())
        for p in [current_path / 'snaptxt', current_path / 'tools']
        if p.exists()
    )
    print(f"\n예상 이동 용량: {total_size / 1024 / 1024:.1f} MB")
    
    # 새 위치 준비
    if not new_path.parent.exists():
        print(f"디렉토리 생성: {new_path.parent}")
        new_path.parent.mkdir(parents=True, exist_ok=True)
        
    print("\n이동 준비 완료!")
    print("수동 이동 권장:")
    print("1. Explorer로 전체 SnapTXT 폴더 복사")
    print("2. C:\\dev\\SnapTXT 에 붙여넣기") 
    print("3. 가상환경 재생성")
    
if __name__ == "__main__":
    safe_project_migration()