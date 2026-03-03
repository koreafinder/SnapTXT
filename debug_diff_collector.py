#!/usr/bin/env python3
"""
DiffCollector 디버깅 - 왜 diff가 수집되지 않는지 단계별로 확인
"""

import sys
from pathlib import Path
from difflib import SequenceMatcher

try:
    from snaptxt.postprocess.pattern_engine import DiffCollector, StageResult, TextDiff
    print("✅ import 성공")
except ImportError as e:
    print(f"❌ import 실패: {e}")
    sys.exit(1)

def detailed_diff_debug():
    """diff 추출 과정을 단계별로 디버깅"""
    print("🔍 DiffCollector 단계별 디버깅")
    print("=" * 50)
    
    collector = DiffCollector()
    
    # 테스트 케이스
    before = "안녕하세요.    이것은    테스트입니다."
    after = "안녕하세요. 이것은 테스트입니다"
    
    print(f"Before: '{before}'")
    print(f"After:  '{after}'")
    print(f"길이 변화: {len(before)} → {len(after)} ({len(after)-len(before):+d})")
    
    # SequenceMatcher로 diff 분석
    matcher = SequenceMatcher(None, before, after)
    opcodes = list(matcher.get_opcodes())
    
    print(f"\n📊 SequenceMatcher 결과: {len(opcodes)}개 연산")
    for i, (tag, i1, i2, j1, j2) in enumerate(opcodes):
        if tag != 'equal':
            before_segment = before[i1:i2]
            after_segment = after[j1:j2]
            print(f"  {i+1}. {tag}: '{before_segment}' → '{after_segment}'")
            print(f"      위치: {i1}-{i2} → {j1}-{j2}")
            print(f"      길이: {len(before_segment)} → {len(after_segment)}")
            
            # 각 필터 단계별 확인
            print(f"      길이 필터: {collector.min_change_length} <= {max(len(before_segment), len(after_segment))} <= {collector.max_change_length} : ", end="")
            change_size = max(len(before_segment), len(after_segment))
            length_ok = collector.min_change_length <= change_size <= collector.max_change_length
            print("✅" if length_ok else "❌")
            
            if length_ok:
                # 의미있는 변화인지 확인  
                meaningful = collector._is_meaningful_change(before_segment, after_segment)
                print(f"      의미 필터: {meaningful} ({'✅' if meaningful else '❌'})")
                
                if meaningful:
                    # 신뢰도 계산
                    confidence = collector._calculate_confidence(before_segment, after_segment)
                    print(f"      신뢰도 계산: {confidence:.3f}")
                    print(f"      신뢰도 필터: {confidence} >= {collector.min_confidence} : {'✅' if confidence >= collector.min_confidence else '❌'}")

def test_individual_filters():
    """각 필터 함수를 개별적으로 테스트"""
    print("\n🧪 개별 필터 테스트")
    print("-" * 30)
    
    collector = DiffCollector()
    
    test_cases = [
        ("  ", " ", "공백 정리"),
        ("안녕    하세요", "안녕 하세요", "다중 공백 정리"),
        ("테스트", "테스트 ", "끝공백 추가"),
        ("hello", "Hello", "대소문자 변경"),
        ("안녕", "안녕", "동일 텍스트"),
        ("a", "b", "1글자 변경"),
        ("테스트문장", "테스트 문장", "띄어쓰기 추가"),
        ("한국어가어렵습니다", "한국어가 어렵습니다", "한국어 띄어쓰기"),
        ("  안녕하세요  ", "안녕하세요", "앞뒤 공백 제거"),
        ("test", "", "텍스트 삭제"),
        ("", "test", "텍스트 추가"),
    ]
    
    for before, after, desc in test_cases:
        print(f"\n📝 {desc}: '{before}' → '{after}'")
        
        # 길이 체크
        change_size = max(len(before), len(after))
        length_ok = collector.min_change_length <= change_size <= collector.max_change_length
        print(f"   길이: {length_ok} ({change_size}자)")
        
        if length_ok:
            # 의미있는 변화인지 확인
            meaningful = collector._is_meaningful_change(before, after)
            print(f"   의미: {meaningful}")
            
            if meaningful:
                # 신뢰도 계산
                confidence = collector._calculate_confidence(before, after)
                print(f"   신뢰도: {confidence:.3f} (임계값: {collector.min_confidence})")
                
                # 최종 판정
                final_ok = confidence >= collector.min_confidence
                print(f"   최종: {'✅ 수집됨' if final_ok else '❌ 필터링됨'}")

def test_lower_thresholds():
    """더 낮은 임계값으로 테스트"""
    print("\n⚙️ 낮은 임계값으로 테스트")
    print("-" * 30)
    
    # 더 관대한 설정으로 DiffCollector 생성
    collector = DiffCollector()
    collector.min_change_length = 1  # 1글자부터
    collector.min_confidence = 0.1   # 10%부터
    
    print(f"📊 새 설정: min_length={collector.min_change_length}, min_confidence={collector.min_confidence}")
    
    # 테스트 실행
    stage_result = StageResult(
        original_text="안녕하세요.    이것은    테스트입니다.",
        stage2_result="안녕하세요. 이것은 테스트 입니다.",
        stage3_result="안녕하세요. 이것은 테스트입니다.",
        stage2_time=0.01,
        stage3_time=0.01,
        total_changes=3
    )
    
    diffs = collector.collect_stage_diffs(stage_result)
    print(f"\n✨ 수집 결과: {len(diffs)}개 diff")
    
    for i, diff in enumerate(diffs):
        print(f"   {i+1}. '{diff.before}' → '{diff.after}' (신뢰도: {diff.confidence:.3f}, {diff.stage})")
    
    # 로그 파일 확인
    if collector.log_path.exists():
        print(f"\n✅ 로그 파일 생성됨: {collector.log_path.stat().st_size} bytes")
        return True
    else:
        print(f"\n❌ 로그 파일 생성 안됨")
        return False

def main():
    print("🔍 DiffCollector 상세 디버깅")
    print("=" * 60)
    
    try:
        # 1. 상세 diff 분석
        detailed_diff_debug()
        
        # 2. 개별 필터 테스트
        test_individual_filters()
        
        # 3. 낮은 임계값으로 테스트
        log_created = test_lower_thresholds()
        
        if log_created:
            print("\n🎯 패턴 분석 테스트")
            print("-" * 20)
            
            from snaptxt.postprocess.pattern_engine import PatternAnalyzer
            analyzer = PatternAnalyzer()
            candidates = analyzer.analyze_recent_patterns(days=1)
            
            print(f"✅ 패턴 후보: {len(candidates)}개")
            for candidate in candidates[:3]:  # 상위 3개만
                print(f"   '{candidate.pattern}' → '{candidate.replacement}' ({candidate.frequency}회)")
        
        print("\n✅ 디버깅 완료")
        
    except Exception as e:
        print(f"\n❌ 디버깅 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())