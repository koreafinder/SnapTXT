#!/usr/bin/env python3
"""
Phase 1 MVP 직접 테스트 & 디버깅

DiffCollector와 패턴 수집이 제대로 동작하는지 직접 테스트
"""

import sys
import logging
from pathlib import Path

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

try:
    from snaptxt.postprocess import run_pipeline
    from snaptxt.postprocess.pattern_engine import DiffCollector, StageResult, PatternAnalyzer
    print("✅ 패턴 엔진 import 성공")
except ImportError as e:
    print(f"❌ import 실패: {e}")
    sys.exit(1)

def direct_diff_test():
    """DiffCollector 직접 테스트"""
    print("\n🔧 DiffCollector 직접 테스트")
    print("-" * 40)
    
    collector = DiffCollector()
    print(f"로그 경로: {collector.log_path}")
    
    # 간단한 StageResult 직접 생성
    stage_result = StageResult(
        original_text="안녕하세요. 이것은  테스트  입니다.",
        stage2_result="안녕하세요. 이것은 테스트 입니다.",  # 공백 정리
        stage3_result="안녕하세요. 이것은 테스트입니다.",   # 띄어쓰기 교정
        stage2_time=0.01,
        stage3_time=0.02,
        total_changes=5
    )
    
    print(f"원본: '{stage_result.original_text}'")
    print(f"Stage2: '{stage_result.stage2_result}'")
    print(f"Stage3: '{stage_result.stage3_result}'")
    
    # diff 수집
    try:
        diffs = collector.collect_stage_diffs(stage_result)
        print(f"\n수집된 diff: {len(diffs)}개")
        
        for i, diff in enumerate(diffs):
            print(f"  {i+1}. '{diff.before}' → '{diff.after}' (신뢰도: {diff.confidence:.2f}, {diff.stage})")
            
        # 로그 파일 확인
        if collector.log_path.exists():
            print(f"\n✅ 로그 파일 생성됨: {collector.log_path}")
            with open(collector.log_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"   파일 크기: {len(content)} 바이트")
                if content:
                    lines = content.strip().split('\n')
                    print(f"   로그 엔트리: {len(lines)}개")
        else:
            print(f"❌ 로그 파일 생성 안됨: {collector.log_path}")
            
    except Exception as e:
        print(f"❌ diff 수집 실패: {e}")
        import traceback
        traceback.print_exc()

def simple_pipeline_test():
    """단순한 파이프라인 테스트"""
    print("\n🔄 단순한 파이프라인 테스트")
    print("-" * 40)
    
    test_text = "안녕하세요.    이것은    테스트입니다."
    print(f"원본: '{test_text}'")
    
    # 패턴 수집 활성화하여 실행
    try:
        result = run_pipeline(test_text, collect_patterns=True)
        print(f"결과: '{result}'")
        
        # 로그 파일 확인
        log_path = Path("logs/pattern_collection.jsonl") 
        if log_path.exists():
            print(f"✅ 로그 파일 확인됨")
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"   내용: {content[-200:]}")  # 마지막 200자만 표시
        else:
            print(f"❌ 로그 파일 없음: {log_path}")
            
    except Exception as e:
        print(f"❌ 파이프라인 실행 실패: {e}")
        import traceback
        traceback.print_exc()

def test_pattern_analyzer():
    """PatternAnalyzer 테스트"""
    print("\n🔍 PatternAnalyzer 테스트")
    print("-" * 40)
    
    analyzer = PatternAnalyzer()
    
    # 강제로 로그 데이터 생성 후 분석
    log_path = Path("logs/pattern_collection.jsonl")
    
    if not log_path.exists():
        print("⚠️ 로그 파일이 없어서 분석할 수 없습니다.")
        print("먼저 diff 수집이 이루어져야 합니다.")
    else:
        print(f"📂 로그 파일 크기: {log_path.stat().st_size} 바이트")
        
        # 최근 패턴 분석
        try:
            candidates = analyzer.analyze_recent_patterns(days=1)
            print(f"✅ 패턴 분석 완료: {len(candidates)}개 후보")
            
            for candidate in candidates:
                print(f"   '{candidate.pattern}' → '{candidate.replacement}' " 
                      f"(빈도: {candidate.frequency}, 신뢰도: {candidate.confidence:.2f})")
                      
        except Exception as e:
            print(f"❌ 패턴 분석 실패: {e}")
            import traceback
            traceback.print_exc()

def test_with_meaningful_changes():
    """의미있는 변화로 테스트"""
    print("\n🎯 의미있는 변화로 테스트")
    print("-" * 40)
    
    # 확실한 변화가 있는 텍스트들
    test_cases = [
        ("한국어가어렵습니다", "한국어가 어렵습니다"),         # 띄어쓰기
        ("Hello  world  test", "Hello world test"),       # 공백 정리
        ("안녕하세요   반갑습니다", "안녕하세요 반갑습니다"),     # 공백 정리
        ("좋은    하루    되세요", "좋은 하루 되세요"),        # 공백 정리
        ("테스트문장입니다", "테스트 문장입니다")              # 띄어쓰기 추가
    ]
    
    collector = DiffCollector()
    
    for i, (original, expected) in enumerate(test_cases, 1):
        print(f"\n테스트 {i}: '{original}' → '{expected}'")
        
        # StageResult 직접 생성 (예상 결과로)
        stage_result = StageResult(
            original_text=original,
            stage2_result=expected,  # Stage2에서 교정된 것으로 가정
            stage3_result=expected,  # Stage3에서는 변화 없음
            stage2_time=0.01,
            stage3_time=0.01,
            total_changes=1
        )
        
        # diff 수집
        diffs = collector.collect_stage_diffs(stage_result)
        print(f"   수집 diff: {len(diffs)}개")
        
        for diff in diffs:
            print(f"      '{diff.before}' → '{diff.after}' (신뢰도: {diff.confidence:.2f})")
    
    # 최종 로그 파일 확인
    if collector.log_path.exists():
        print(f"\n✅ 최종 로그 파일: {collector.log_path}")
        print(f"   크기: {collector.log_path.stat().st_size} 바이트")
        
        # 패턴 분석 시도
        analyzer = PatternAnalyzer()
        candidates = analyzer.analyze_recent_patterns(days=1)
        print(f"   분석된 패턴: {len(candidates)}개")
        
        for candidate in candidates:
            print(f"      '{candidate.pattern}' → '{candidate.replacement}' " 
                  f"(빈도: {candidate.frequency})")

def main():
    print("🚀 Phase 1 MVP 직접 테스트 & 디버깅")
    print("=" * 50)
    
    try:
        # 1. DiffCollector 직접 테스트
        direct_diff_test()
        
        # 2. 단순한 파이프라인 테스트  
        simple_pipeline_test()
        
        # 3. PatternAnalyzer 테스트
        test_pattern_analyzer()
        
        # 4. 의미있는 변화로 테스트
        test_with_meaningful_changes()
        
        print("\n✅ 모든 테스트 완료")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())