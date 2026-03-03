#!/usr/bin/env python3
"""
PatternAnalyzer._normalize_pattern 메서드 디버깅
어떤 단계에서 패턴이 필터링되는지 상세 분석
"""

from snaptxt.postprocess.pattern_engine import PatternAnalyzer
import json
from datetime import datetime, timedelta

def debug_normalize_pattern():
    """_normalize_pattern 메서드의 각 단계별 디버깅"""
    print("🔍 PatternAnalyzer._normalize_pattern 디버깅")
    print("="*60)
    
    analyzer = PatternAnalyzer("logs")
    
    # 로그 파일에서 실제 diff 데이터 읽기
    test_patterns = []
    
    try:
        with open(analyzer.log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # 최근 10개 라인에서 diff 패턴 추출
        recent_lines = lines[-10:] if len(lines) >= 10 else lines
        
        for line in recent_lines:
            try:
                data = json.loads(line.strip())
                diffs = data.get('diffs', [])
                
                for diff in diffs:
                    before = diff.get('before', '')
                    after = diff.get('after', '')
                    test_patterns.append((before, after, diff.get('confidence', 0.5)))
                    
            except json.JSONDecodeError:
                continue
                
    except Exception as e:
        print(f"❌ 로그 파일 읽기 오류: {e}")
        return
    
    print(f"📊 추출된 테스트 패턴: {len(test_patterns)}개")
    print()
    
    # 각 패턴에 대해 _normalize_pattern 단계별 테스트
    for i, (before, after, confidence) in enumerate(test_patterns[:5], 1):  # 최대 5개만 테스트
        print(f"🧪 패턴 {i}: '{before}' → '{after}' (신뢰도: {confidence})")
        
        # 1. 길이 검증
        length_check = not (len(before) < 1 or len(after) < 1 or 
                           len(before) > analyzer.max_pattern_length or 
                           len(after) > analyzer.max_pattern_length)
        print(f"   1️⃣ 길이 검증: {length_check}")
        print(f"      before 길이: {len(before)}, after 길이: {len(after)}")
        
        if not length_check:
            print("   ❌ 길이 검증 실패 - 패턴 제외")
            print()
            continue
        
        # 2. 공백 정규화
        import re
        before_clean = re.sub(r'\s+', ' ', before.strip())
        after_clean = re.sub(r'\s+', ' ', after.strip()) 
        print(f"   2️⃣ 공백 정규화:")
        print(f"      before: '{before}' → '{before_clean}'")
        print(f"      after:  '{after}' → '{after_clean}'")
        
        # 3. 빈 문자열 검사
        empty_check = before_clean and after_clean
        print(f"   3️⃣ 빈 문자열 검사: {empty_check}")
        print(f"      before_clean: {repr(before_clean)}")
        print(f"      after_clean: {repr(after_clean)}")
        
        if not empty_check:
            print("   ❌ 빈 문자열 검사 실패 - 패턴 제외")
            print()
            continue
        
        # 4. 실제 _normalize_pattern 호출
        try:
            normalized = analyzer._normalize_pattern(before, after)
            print(f"   4️⃣ _normalize_pattern 결과: {normalized}")
            
            if normalized:
                print("   ✅ 정규화 성공 - 패턴 유효")
                
                # 빈도 필터링 시뮬레이션
                print(f"   5️⃣ 빈도 필터링 (최소 빈도: {analyzer.min_frequency})")
                print(f"      신뢰도 필터링 (최소 신뢰도: {analyzer.min_confidence})")
                print(f"      입력 신뢰도: {confidence}")
                
                freq_ok = True  # 빈도는 별도 계산 필요
                conf_ok = confidence >= analyzer.min_confidence
                
                print(f"      신뢰도 통과: {conf_ok}")
                
                if conf_ok:
                    print("   🎯 최종 통과 - 후보 패턴 가능")
                else:
                    print("   ⚠️ 신뢰도 부족 - 패턴 제외")
            else:
                print("   ❌ 정규화 실패 - 패턴 제외")
                
        except Exception as e:
            print(f"   ❌ _normalize_pattern 오류: {e}")
            
        print()
    
    # 전체 분석 다시 실행
    print("🔄 전체 분석 재실행")
    print("-"*40)
    
    try:
        # 기존 설정으로 분석
        print(f"⚙️ 현재 설정: 최소빈도={analyzer.min_frequency}, 최소신뢰도={analyzer.min_confidence}")
        candidates = analyzer.analyze_recent_patterns(days=1)
        print(f"📊 후보 패턴: {len(candidates)}개")
        
        # 더 관대한 설정으로 분석
        print(f"⚙️ 완화된 설정: 최소빈도=1, 최소신뢰도=0.1")
        analyzer.min_frequency = 1
        analyzer.min_confidence = 0.1
        
        relaxed_candidates = analyzer.analyze_recent_patterns(days=1)
        print(f"📊 완화된 후보 패턴: {len(relaxed_candidates)}개")
        
        if relaxed_candidates:
            print("🎯 완화된 설정에서 발견된 패턴:")
            for candidate in relaxed_candidates[:3]:  # 최대 3개
                print(f"   '{candidate.pattern}' → '{candidate.replacement}' (빈도: {candidate.frequency})")
        
    except Exception as e:
        print(f"❌ 분석 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_normalize_pattern()