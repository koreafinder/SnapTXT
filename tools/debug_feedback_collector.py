#!/usr/bin/env python3
"""
UserFeedbackCollector 디버깅 스크립트
"""

import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from snaptxt.learning.feedback_collector import UserFeedbackCollector

def debug_feedback_collector():
    """UserFeedbackCollector 디버깅"""
    print("🔍 UserFeedbackCollector 디버깅 시작")
    
    collector = UserFeedbackCollector()
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "띄어쓰기 오류 1",
            "original": "생각과자아를분리하는연습을해보세도",
            "corrected": "생각과 자아를 분리하는 연습을 해보세요"
        },
        {
            "name": "띄어쓰기 오류 2", 
            "original": "마이 클 싱 어는 세계적으로",
            "corrected": "마이클 싱어는 세계적으로"
        },
        {
            "name": "구두점 오류",
            "original": "생각이떠오를때마다인식하세요ㅏ",
            "corrected": "생각이 떠오를 때마다 인식하세요."
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n🧪 테스트 {i}: {test['name']}")
        print(f"   원본: {test['original']}")
        print(f"   수정: {test['corrected']}")
        
        try:
            result = collector.collect_user_correction(
                original_text=test['original'],
                corrected_text=test['corrected'],
                image_source=f"test_{i}.jpg",
                user_id="debug_user"
            )
            
            differences = result.get('differences', [])
            patterns = result.get('extracted_patterns', [])
            
            print(f"   🔎 차이점: {len(differences)}개")
            for j, diff in enumerate(differences, 1):
                print(f"      {j}. {diff.get('type', 'Unknown')}: '{diff.get('old_text', '')}' → '{diff.get('new_text', '')}' ({diff.get('correction_type', 'Unknown')})")
            
            print(f"   📝 패턴: {len(patterns)}개")
            for j, pattern in enumerate(patterns, 1):
                print(f"      {j}. '{pattern.get('pattern', 'N/A')}' → '{pattern.get('replacement', 'N/A')}' (카테고리: {pattern.get('category', 'N/A')})")
                
        except Exception as e:
            print(f"   ❌ 오류: {e}")
    
    print(f"\n✅ 디버깅 완료")

if __name__ == "__main__":
    debug_feedback_collector()