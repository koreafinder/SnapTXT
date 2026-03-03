#!/usr/bin/env python3
"""
PatternAnalyzer 직접 디버깅 테스트
수집된 로그 데이터로 패턴 분석이 정상 작동하는지 확인
"""

from snaptxt.postprocess.pattern_engine import PatternAnalyzer, RuleGenerator
import json
from pathlib import Path

def debug_pattern_analyzer():
    """PatternAnalyzer 디버깅"""
    print("🔍 PatternAnalyzer 직접 테스트")
    print("="*50)
    
    analyzer = PatternAnalyzer("logs")
    
    # 로그 파일 상태 확인
    log_file = analyzer.log_path
    if not log_file.exists():
        print(f"❌ 로그 파일 없음: {log_file}")
        return 0
        
    print(f"📂 로그 파일: {log_file}")
    print(f"📊 파일 크기: {log_file.stat().st_size} bytes")
    
    # 로그 데이터 직접 읽기
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f"📄 총 로그 라인: {len(lines)}개")
        
        # 최근 몇 개 라인 분석
        recent_lines = lines[-5:] if len(lines) >= 5 else lines
        print(f"🔍 최근 {len(recent_lines)}개 라인 분석:")
        
        patterns_found = {}
        for i, line in enumerate(recent_lines, 1):
            try:
                data = json.loads(line.strip())
                diffs = data.get('diffs', [])
                print(f"   라인 {i}: {len(diffs)}개 diff")
                
                for diff in diffs:
                    before = diff.get('before', '')
                    after = diff.get('after', '')
                    pattern_key = f"'{before}' → '{after}'"
                    
                    if pattern_key not in patterns_found:
                        patterns_found[pattern_key] = 0
                    patterns_found[pattern_key] += 1
            except json.JSONDecodeError as e:
                print(f"   라인 {i}: JSON 파싱 오류 - {e}")
                
        print("\n📈 발견된 패턴들:")
        for pattern, count in patterns_found.items():
            print(f"   {pattern} ({count}회)")
        
    except Exception as e:
        print(f"❌ 로그 읽기 오류: {e}")
        return 0
    
    # PatternAnalyzer 실행
    print("\n🧠 PatternAnalyzer.analyze_recent_patterns() 실행")
    print("-"*40)
    
    # 현재 설정 출력
    print(f"⚙️ 현재 설정:")
    print(f"   최소 빈도: {analyzer.min_frequency}")
    print(f"   최소 신뢰도: {analyzer.min_confidence}")
    print(f"   최대 패턴 길이: {analyzer.max_pattern_length}")
    
    try:
        candidates = analyzer.analyze_recent_patterns(days=1)
        print(f"\n🎯 분석 결과: {len(candidates)}개 후보 패턴")
        
        if candidates:
            print("\n📋 후보 패턴 목록:")
            for i, candidate in enumerate(candidates, 1):
                print(f"   {i}. '{candidate.pattern}' → '{candidate.replacement}'")
                print(f"      빈도: {candidate.frequency}회, 신뢰도: {candidate.confidence:.3f}")
                print(f"      카테고리: {candidate.predicted_category}")
                print(f"      첫 발견: {candidate.first_seen.strftime('%H:%M:%S')}")
                print()
                
            # 규칙 생성 테스트
            print("⚙️ RuleGenerator 테스트")
            print("-"*30)
            
            rule_generator = RuleGenerator()
            suggestions = rule_generator.generate_rule_suggestions(candidates)
            
            if suggestions:
                print(f"✅ {len(suggestions)}개 규칙 생성됨")
                print(f"📄 파일: {rule_generator.suggestions_path}")
                
                # 생성된 규칙 파일 내용 확인
                if Path(rule_generator.suggestions_path).exists():
                    with open(rule_generator.suggestions_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    print(f"📝 파일 내용 ({len(content)} 글자):")
                    print("   " + content[:200] + ("..." if len(content) > 200 else ""))
                else:
                    print("⚠️ 규칙 파일이 생성되지 않았습니다")
            else:
                print("❌ 규칙 생성 실패")
        else:
            print("⚠️ 후보 패턴이 없습니다")
            print("💡 디버깅 제안:")
            print("   - min_frequency를 더 낮춰보세요 (현재: {})".format(analyzer.min_frequency))
            print("   - min_confidence를 더 낮춰보세요 (현재: {})".format(analyzer.min_confidence))
            print("   - 더 많은 테스트 데이터를 생성해보세요")
            
        return len(candidates)
        
    except Exception as e:
        print(f"❌ 분석 오류: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    print("🚀 PatternAnalyzer 직접 디버깅 테스트")
    print("="*60)
    
    found = debug_pattern_analyzer()
    
    print("\n" + "="*60)
    print("🏁 테스트 완료")
    print("="*60)
    
    if found > 0:
        print(f"✅ {found}개 패턴 후보 발견!")
        print("🎉 Phase 1 MVP 패턴 학습 시스템이 정상 작동합니다!")
    else:
        print("⚠️ 패턴 후보를 발견하지 못했습니다")
        print("🔧 추가 조정이 필요할 수 있습니다")