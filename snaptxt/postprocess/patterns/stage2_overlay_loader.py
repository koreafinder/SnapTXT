"""Stage2 Overlay Loader - GT Learner와 경로 완전 통일"""

import os
import yaml
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# GT Learner와 동일한 위치 탐색  
def _find_learning_data_paths() -> List[Path]:
    """GT learner와 동일한 CWD 독립적 경로 탐색"""
    # GT Learner와 동일한 방식: __file__ 기준 프로젝트 루트 계산
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent.parent  # snaptxt/postprocess/patterns -> 프로젝트루트
    
    # GT Learner와 정확히 동일한 경로
    primary_path = project_root / "learning_data"
    
    candidates = [
        primary_path,  # GT learner와 동일한 위치
        
        # 기존 호환성 유지
        Path.cwd() / "learning_data",
    ]
    
    existing_paths = [p for p in candidates if p.exists()]
    
    if not existing_paths:
        # GT learner와 동일하게 생성
        primary_path.mkdir(parents=True, exist_ok=True)
        existing_paths = [primary_path]
    
    return existing_paths

def load_stage2_overlay() -> Tuple[Dict[str, str], str]:
    """Stage2 overlay 전용 파일 안전 로드 (SMOKE 파일 격리)"""
    learning_paths = _find_learning_data_paths()
    
    for learning_dir in learning_paths:
        # stage2_overlay_*.yaml 파일 탐지
        overlay_files = list(learning_dir.glob("stage2_overlay_*.yaml"))
        
        # 🔒 SMOKE 파일 격리: *_SMOKE.yaml 파일 무시
        production_files = []
        ignored_files = []
        
        for file_path in overlay_files:
            if file_path.name.endswith("_SMOKE.yaml"):
                ignored_files.append(file_path.name)
            else:
                production_files.append(file_path)
        
        # 격리 로그
        if ignored_files:
            print(f"🔒 SMOKE 파일 격리: {ignored_files}")
        
        if not production_files:
            if ignored_files:
                return {}, f"❌ SMOKE 파일만 존재: {ignored_files} (Production overlay 없음)"
            continue
        
        # 최신 Production 파일 선택
        latest_overlay = max(production_files, key=lambda f: f.stat().st_mtime)
        print(f"📊 Production overlay 선택: {latest_overlay.name}")
        
        try:
            with open(latest_overlay, 'r', encoding='utf-8') as f:
                overlay_data = yaml.safe_load(f)
            
            overlay_rules = overlay_data.get("replacements", {})
            return overlay_rules, f"✅ {latest_overlay.name}"
            
        except Exception as e:
            continue
    
    return {}, "❌ stage2_overlay 파일 없음"

def get_overlay_file_info() -> Dict[str, Optional[str]]:
    """관측용: overlay 파일 정보만 (파싱 없음) - SMOKE 파일 제외"""
    learning_paths = _find_learning_data_paths()
    
    for learning_dir in learning_paths:
        overlay_files = list(learning_dir.glob("stage2_overlay_*.yaml"))
        
        # 🔒 SMOKE 파일 격리: Production 파일만 선택
        production_files = [f for f in overlay_files if not f.name.endswith("_SMOKE.yaml")]
        
        if production_files:
            latest = max(production_files, key=lambda f: f.stat().st_mtime)
            return {
                "overlay_file": latest.name,
                "overlay_mtime": latest.stat().st_mtime,
                "overlay_path": str(latest)
            }
    
    return {"overlay_file": None, "overlay_mtime": None, "overlay_path": None}

def apply_overlay_safe_limits(overlay_rules: Dict[str, str]) -> Tuple[Dict[str, str], str]:
    """긴 패턴 우선 + 쌍 기반 화이트리스트"""
    
    # 절대 상한
    ABSOLUTE_MAX = 30
    
    # (pattern, replacement) 쌍 기반 화이트리스트
    CONFUSION_PAIRS = {
        ("o", "0"), ("0", "o"), ("l", "1"), ("1", "l"), 
        ("기", "가"), ("가", "기"), ("는", "능"), ("능", "는"),
        ("어", "여"), ("여", "어"), ("마", "머"), ("머", "마")
    }
    
    # 분류
    safe_patterns = {}
    word_patterns = {}
    whitelist_patterns = {}
    
    for pattern, replacement in overlay_rules.items():
        # 화이트리스트 쌍 검사
        if (pattern, replacement) in CONFUSION_PAIRS:
            whitelist_patterns[pattern] = replacement
        elif len(pattern) >= 3:
            word_patterns[pattern] = replacement
        else:
            safe_patterns[pattern] = replacement  
    
    # 적용: 긴 패턴 우선 → 안전 → 화이트리스트
    limited_rules = {}
    applied_count = 0
    
    # 1. 긴 패턴부터 (내림차순)
    sorted_words = sorted(word_patterns.items(), key=lambda x: len(x[0]), reverse=True)
    for pattern, replacement in sorted_words[:min(20, ABSOLUTE_MAX-applied_count)]:
        limited_rules[pattern] = replacement
        applied_count += 1
    
    # 2. 2글자 안전 패턴
    remaining = ABSOLUTE_MAX - applied_count
    for pattern, replacement in list(safe_patterns.items())[:remaining]:
        limited_rules[pattern] = replacement
        applied_count += 1
    
    # 3. 화이트리스트만 (엄격)
    remaining = ABSOLUTE_MAX - applied_count
    for pattern, replacement in list(whitelist_patterns.items())[:min(3, remaining)]:
        limited_rules[pattern] = replacement
        applied_count += 1
    
    dropped = len(overlay_rules) - applied_count
    policy_info = f"total={len(overlay_rules)}, applied={applied_count}, dropped={dropped}, policy=long_first+pairs"
    
    return limited_rules, policy_info