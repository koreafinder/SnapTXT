#!/usr/bin/env python3
"""
Stage2 vs Stage3 중복 패턴 자동 추출 및 교집합 분석
증거 기반 분석을 위한 스크립트
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple

def extract_stage2_rules() -> Dict[str, str]:
    """Stage2 rules.yaml에서 모든 치환 규칙 추출"""
    stage2_path = Path("snaptxt/postprocess/patterns/stage2_rules.yaml")
    
    if not stage2_path.exists():
        print(f"❌ {stage2_path} 파일이 없습니다.")
        return {}
    
    with open(stage2_path, 'r', encoding='utf-8') as f:
        content = yaml.safe_load(f)
    
    rules = content.get('replacements', {})
    print(f"✅ Stage2 규칙 추출 완료: {len(rules)}개")
    return rules

def extract_stage3_patterns() -> List[Tuple[str, str, str]]:
    """Stage3에서 사용되는 모든 regex 치환 패턴 추출"""
    patterns = []
    
    # 1. Stage3 baseline 규칙 파일에서 추출
    stage3_baseline_path = Path("reports/stage3_rules_baseline_20260301.yaml")
    if stage3_baseline_path.exists():
        try:
            with open(stage3_baseline_path, 'r', encoding='utf-8') as f:
                stage3_content = yaml.safe_load(f)
                
            # spacing 섹션에서 패턴 추출
            spacing_rules = stage3_content.get('spacing', {})
            for category, rules in spacing_rules.items():
                if isinstance(rules, list):
                    for rule in rules:
                        if isinstance(rule, dict) and 'pattern' in rule and 'replacement' in rule:
                            patterns.append((rule['pattern'], rule['replacement'], f"stage3_baseline:{category}"))
                            
        except Exception as e:
            print(f"❌ Stage3 baseline 읽기 오류: {e}")
    
    # 2. 주요 Stage3 파일들에서 추가 스캔
    stage3_files = [
        "easyocr_worker.py",
        "snaptxt/postprocess/context_aware_processor.py",
    ]
    
    for filepath in stage3_files:
        file_path = Path(filepath)
        if not file_path.exists():
            print(f"⚠️ {filepath} 파일이 없습니다.")
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # re.sub 패턴 추출 
            regex_patterns = re.findall(
                r're\.sub\([\'"](.+?)[\'"],\s*[\'"](.+?)[\'"]', 
                content
            )
            
            for pattern, replacement in regex_patterns:
                patterns.append((pattern, replacement, str(file_path)))
                
            # text.replace 패턴 추출
            replace_patterns = re.findall(
                r'text\.replace\([\'"](.+?)[\'"],\s*[\'"](.+?)[\'"]', 
                content
            )
            
            for pattern, replacement in replace_patterns:
                patterns.append((pattern, replacement, str(file_path)))
                
        except Exception as e:
            print(f"❌ {filepath} 읽기 오류: {e}")
            continue
    
    print(f"✅ Stage3 패턴 추출 완료: {len(patterns)}개")
    return patterns

def find_overlaps(stage2_rules: Dict[str, str], stage3_patterns: List[Tuple[str, str, str]]) -> List[Dict]:
    """Stage2와 Stage3의 교집합 찾기"""
    overlaps = []
    
    # Stage2의 키(패턴)들 
    stage2_keys = set(stage2_rules.keys())
    
    # Stage3의 패턴들에서 완전 일치 또는 유사 패턴 찾기
    for stage3_pattern, stage3_replacement, source_file in stage3_patterns:
        for stage2_key in stage2_keys:
            # 완전 일치
            if stage2_key == stage3_pattern:
                overlaps.append({
                    'type': '완전일치',
                    'pattern': stage2_key,
                    'stage2_replacement': stage2_rules[stage2_key],
                    'stage3_replacement': stage3_replacement,
                    'stage3_source': source_file,
                    'conflict_level': 'HIGH' if stage2_rules[stage2_key] != stage3_replacement else 'LOW'
                })
            
            # 유사 패턴 (부분 문자열 포함)
            elif stage2_key in stage3_pattern or stage3_pattern in stage2_key:
                overlaps.append({
                    'type': '유사패턴',
                    'pattern': f"'{stage2_key}' vs '{stage3_pattern}'",
                    'stage2_replacement': stage2_rules[stage2_key],
                    'stage3_replacement': stage3_replacement,
                    'stage3_source': source_file,
                    'conflict_level': 'MEDIUM'
                })
            
            # 어미/어절 패턴 유사성 검사 (한국어 특화)
            elif any(keyword in stage2_key for keyword in ['습니다', '했습니다', '음 니다']) and \
                 any(keyword in stage3_replacement for keyword in ['습니다', '했습니다']):
                overlaps.append({
                    'type': '어미중복',
                    'pattern': f"Stage2 '{stage2_key}' vs Stage3 '{stage3_pattern}'",
                    'stage2_replacement': stage2_rules[stage2_key],
                    'stage3_replacement': stage3_replacement,
                    'stage3_source': source_file,
                    'conflict_level': 'HIGH'
                })
    
    return overlaps

def main():
    print("🔍 Stage2 vs Stage3 중복 패턴 자동 분석 시작")
    print("=" * 60)
    
    # 1. Stage2 규칙 추출
    stage2_rules = extract_stage2_rules()
    
    # 2. Stage3 패턴 추출  
    stage3_patterns = extract_stage3_patterns()
    
    # 3. 교집합 계산
    overlaps = find_overlaps(stage2_rules, stage3_patterns)
    
    print(f"\n📊 분석 결과:")
    print(f"   Stage2 총 규칙: {len(stage2_rules)}개")
    print(f"   Stage3 총 패턴: {len(stage3_patterns)}개") 
    print(f"   교집합: {len(overlaps)}개")
    
    # 4. 상위 30개 출력
    print(f"\n🏆 교집합 상위 30개:")
    for i, overlap in enumerate(overlaps[:30], 1):
        print(f"   {i:2d}. {overlap['type']} - {overlap['pattern']}")
        print(f"      Stage2: '{overlap['stage2_replacement']}'")
        print(f"      Stage3: '{overlap['stage3_replacement']}' ({overlap['stage3_source']})")
        print(f"      충돌수준: {overlap['conflict_level']}")
        print()
        
    return len(overlaps)

if __name__ == "__main__":
    main()