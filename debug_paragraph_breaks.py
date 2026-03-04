#!/usr/bin/env python3
"""
문단 나누기 함수 디버깅
====================

_add_paragraph_breaks 함수에서 빈 문자열이 반환되는 문제 조사
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import re
import logging

def debug_add_paragraph_breaks(text: str) -> str:
    """_add_paragraph_breaks 함수 디버깅 버전"""
    
    print(f"입력 텍스트: '{text}'")
    print(f"입력 길이: {len(text)}자")
    
    if not text.strip():
        print("❌ 텍스트가 비어있음!")
        return text
    
    # ': ' 이후 새로운 문장이 시작할 때 개행 추가
    text = re.sub(r':\s+([가-힣A-Z])', r':\n\n\1', text)
    print(f"콜론 후 개행 적용 후: '{text}'")
    
    # 문장이 끝나고(. ! ?) 160자 이상 연속될 때 개행 추가 
    sentences = re.split(r'([.!?])\s*', text)
    print(f"문장 분할 결과: {len(sentences)}개")
    for i, sent in enumerate(sentences):
        print(f"  [{i}]: '{sent}'")
    
    result_parts = []
    current_length = 0
    
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i]
        punctuation = sentences[i + 1] if i + 1 < len(sentences) else ''
        
        print(f"처리 중: sentence='{sentence}', punc='{punctuation}'")
        
        result_parts.append(sentence + punctuation)
        current_length += len(sentence) + len(punctuation)
        
        # 160자 이상이고 다음 문장이 있을 때 문단 나누기
        if current_length > 160 and i + 2 < len(sentences):
            next_sentence = sentences[i + 2].strip()
            if next_sentence and (next_sentence[0].isalpha() or '가' <= next_sentence[0] <= '힣'):
                result_parts.append('\n\n')
                current_length = 0
            else:
                result_parts.append(' ')
        elif i + 2 < len(sentences):
            result_parts.append(' ')
    
    # 마지막 문장 추가        
    if len(sentences) > 1:
        print(f"마지막 문장 추가: '{sentences[-1]}'")
        result_parts.append(sentences[-1])
        
    final_text = ''.join(result_parts)
    print(f"조합 후: '{final_text}'")
    
    # 연속된 개행 정리
    final_text = re.sub(r'\n{3,}', '\n\n', final_text)
    final_text = final_text.strip()
    
    print(f"최종 결과: '{final_text}'")
    print(f"최종 길이: {len(final_text)}자")
    
    return final_text

def test_paragraph_breaks():
    """문단 나누기 테스트"""
    
    print("🔍 문단 나누기 함수 디버깅")
    print("="*50)
    
    # 테스트 케이스들
    test_texts = [
        "안녕하세요 이것은 테스트입니다",
        "마이컨생어 Michael A Singer 숲속의 명상가로 불리는 마이클 싱어는 대중 앞에 나서기를 꺼려",
        "일러두기 : ( 명상 저널 ) 은 저자가 ( 상처받지 암논 영혼>에서 직접 발휘한 핵심 문장과"
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n🧪 테스트 {i}:")
        print("-" * 30)
        
        result = debug_add_paragraph_breaks(text)
        
        if len(result) == 0:
            print("❌ 빈 문자열 반환!")
        else:
            print(f"✅ 정상 처리: {len(result)}자")
        
        print()

if __name__ == "__main__":
    test_paragraph_breaks()