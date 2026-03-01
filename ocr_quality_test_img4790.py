#!/usr/bin/env python3
"""
IMG_4790 + OCR 통합 성능 테스트

전처리 방법별로 OCR 결과까지 비교하여 실제 텍스트 추출 품질을 평가합니다.
"""

import cv2
import numpy as np
import sys
import time
import os
from pathlib import Path

# SnapTXT 모듈 import
sys.path.insert(0, str(Path(__file__).parent))
from snaptxt.preprocess.scientific_assessor import smart_preprocess_image
from snaptxt.preprocess import apply_default_filters
from snaptxt.backend.multi_engine import MultiOCRProcessor


def ocr_quality_test():
    """OCR 품질 테스트"""
    print("🔗 IMG_4790 전처리-OCR 통합 품질 테스트")
    print("="*60)
    
    # 이미지 로드
    image_path = Path("uploads/IMG_4790.JPG")
    if not image_path.exists():
        print("❌ IMG_4790.JPG 파일이 없습니다.")
        return
    
    image = cv2.imread(str(image_path))
    if image is None:
        print("❌ 이미지 로드 실패")
        return
    
    print(f"📊 원본 이미지: {image.shape[1]}x{image.shape[0]} pixels")
    
    # OCR 프로세서 초기화
    print("🔧 OCR 프로세서 초기화 중...")
    processor = MultiOCRProcessor()
    
    test_results = []
    
    # 1. 전처리 없이 OCR
    print(f"\n1️⃣ 전처리 없이 OCR")
    try:
        start_time = time.time()
        result_no_prep = processor.extract_text_easyocr(image)
        time_no_prep = time.time() - start_time
        
        char_count = len(result_no_prep.strip())
        word_count = len(result_no_prep.strip().split())
        korean_chars = sum(1 for c in result_no_prep if '가' <= c <= '힣')
        
        print(f"   ⏱️ 시간: {time_no_prep:.3f}초")
        print(f"   📝 추출: {char_count}자, {word_count}단어, 한글 {korean_chars}자")
        print(f"   📄 미리보기: {result_no_prep[:80].replace(chr(10), ' ')}...")
        
        test_results.append({
            'method': '전처리 없음',
            'time': time_no_prep,
            'text': result_no_prep,
            'char_count': char_count,
            'word_count': word_count,
            'korean_chars': korean_chars
        })
        
    except Exception as e:
        print(f"   ❌ 실패: {e}")
        test_results.append({
            'method': '전처리 없음',
            'time': 0,
            'text': '',
            'char_count': 0,
            'word_count': 0,
            'korean_chars': 0
        })
    
    # 2. 레거시 전처리 Level 2 + OCR
    print(f"\n2️⃣ 레거시 전처리 Level 2 + OCR")
    try:
        start_time = time.time()
        preprocessed_legacy = processor.preprocess_image(image, preprocessing_level=2, use_scientific=False)
        result_legacy = processor.extract_text_easyocr(preprocessed_legacy)
        time_legacy = time.time() - start_time
        
        char_count = len(result_legacy.strip())
        word_count = len(result_legacy.strip().split())
        korean_chars = sum(1 for c in result_legacy if '가' <= c <= '힣')
        
        print(f"   ⏱️ 시간: {time_legacy:.3f}초")
        print(f"   📝 추출: {char_count}자, {word_count}단어, 한글 {korean_chars}자")
        print(f"   📄 미리보기: {result_legacy[:80].replace(chr(10), ' ')}...")
        
        test_results.append({
            'method': '레거시 L2',
            'time': time_legacy,
            'text': result_legacy,
            'char_count': char_count,
            'word_count': word_count,
            'korean_chars': korean_chars
        })
        
    except Exception as e:
        print(f"   ❌ 실패: {e}")
        test_results.append({
            'method': '레거시 L2',
            'time': 0,
            'text': '',
            'char_count': 0,
            'word_count': 0,
            'korean_chars': 0
        })
    
    # 3. 과학적 전처리 + OCR  
    print(f"\n3️⃣ 과학적 전처리 + OCR")
    try:
        start_time = time.time()
        preprocessed_scientific = processor.preprocess_image(image, use_scientific=True)
        result_scientific = processor.extract_text_easyocr(preprocessed_scientific)
        time_scientific = time.time() - start_time
        
        char_count = len(result_scientific.strip())
        word_count = len(result_scientific.strip().split())
        korean_chars = sum(1 for c in result_scientific if '가' <= c <= '힣')
        
        print(f"   ⏱️ 시간: {time_scientific:.3f}초")
        print(f"   📝 추출: {char_count}자, {word_count}단어, 한글 {korean_chars}자")
        print(f"   📄 미리보기: {result_scientific[:80].replace(chr(10), ' ')}...")
        
        test_results.append({
            'method': '과학적',
            'time': time_scientific,
            'text': result_scientific,
            'char_count': char_count,
            'word_count': word_count,
            'korean_chars': korean_chars
        })
        
    except Exception as e:
        print(f"   ❌ 실패: {e}")
        test_results.append({
            'method': '과학적',
            'time': 0,
            'text': '',
            'char_count': 0,
            'word_count': 0,
            'korean_chars': 0
        })
    
    # 결과 분석
    analyze_ocr_results(test_results)
    
    # 텍스트 품질 상세 분석
    detailed_text_analysis(test_results)
    
    return test_results


def analyze_ocr_results(test_results):
    """OCR 결과 종합 분석"""
    print(f"\n📈 OCR 성능 비교 분석")
    print("="*50)
    
    print("📊 기본 지표:")
    print("방법          | 시간(초) | 텍스트(자) | 단어수 | 한글자")
    print("-"*55)
    
    for result in test_results:
        method = result['method']
        time_taken = result['time']
        char_count = result['char_count'] 
        word_count = result['word_count']
        korean_chars = result['korean_chars']
        
        print(f"{method:12s} | {time_taken:7.2f} | {char_count:9d} | {word_count:5d} | {korean_chars:5d}")
    
    # 최고 성능 찾기
    valid_results = [r for r in test_results if r['time'] > 0]
    
    if len(valid_results) >= 2:
        best_char_count = max(valid_results, key=lambda x: x['char_count'])
        best_korean = max(valid_results, key=lambda x: x['korean_chars'])
        fastest = min(valid_results, key=lambda x: x['time'])
        
        print(f"\n🏆 성능 하이라이트:")
        print(f"   📝 최다 텍스트 추출: {best_char_count['method']} ({best_char_count['char_count']}자)")
        print(f"   🇰🇷 최다 한글 추출: {best_korean['method']} ({best_korean['korean_chars']}자)")
        print(f"   ⚡ 최고 속도: {fastest['method']} ({fastest['time']:.2f}초)")


def detailed_text_analysis(test_results):
    """텍스트 품질 상세 분석"""
    print(f"\n🔍 텍스트 품질 상세 분석")
    print("="*50)
    
    for i, result in enumerate(test_results):
        if result['text']:
            print(f"\n{i+1}️⃣ {result['method']} 결과 분석:")
            
            text = result['text']
            lines = text.strip().split('\n')
            
            # 텍스트 특성 분석
            total_chars = len(text)
            alpha_chars = sum(1 for c in text if c.isalpha())
            digit_chars = sum(1 for c in text if c.isdigit())
            punct_chars = sum(1 for c in text if c in '.,!?;:')
            space_chars = sum(1 for c in text if c.isspace())
            
            print(f"   📏 총 줄 수: {len(lines)}")
            print(f"   📊 문자 분포: 알파벳 {alpha_chars}, 숫자 {digit_chars}, 구두점 {punct_chars}, 공백 {space_chars}")
            
            # 첫 3줄 샘플
            print(f"   📄 첫 3줄 샘플:")
            for j, line in enumerate(lines[:3]):
                if line.strip():
                    print(f"      L{j+1}: {line.strip()[:60]}{'...' if len(line.strip()) > 60 else ''}")
            
            # 품질 점수 계산 (간단한 휴리스틱)
            quality_score = calculate_text_quality_score(text)
            print(f"   🎯 텍스트 품질 점수: {quality_score:.2f}/100")


def calculate_text_quality_score(text):
    """텍스트 품질 점수 계산 (0-100)"""
    score = 0
    
    # 기본 길이 점수 (0-30점)
    char_count = len(text.strip())
    score += min(char_count / 20, 30)  # 600자에서 만점
    
    # 한글 비율 점수 (0-25점)
    korean_chars = sum(1 for c in text if '가' <= c <= '힣')
    if char_count > 0:
        korean_ratio = korean_chars / char_count
        score += korean_ratio * 25
    
    # 단어 분포 점수 (0-20점)  
    words = text.strip().split()
    if len(words) > 0:
        avg_word_length = sum(len(w) for w in words) / len(words)
        if 2 <= avg_word_length <= 8:  # 적절한 평균 단어 길이
            score += 20
        else:
            score += max(0, 20 - abs(avg_word_length - 5) * 2)
    
    # 줄 분포 점수 (0-15점)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) >= 3:  # 최소 3줄 이상
        score += min(len(lines), 15)
    
    # 특수문자/공백 적절성 (0-10점)
    if char_count > 0:
        special_ratio = sum(1 for c in text if c in '.,!?;: \n') / char_count
        if 0.1 <= special_ratio <= 0.3:  # 적절한 특수문자 비율
            score += 10
        else:
            score += max(0, 10 - abs(special_ratio - 0.2) * 50)
    
    return min(score, 100)


def save_ocr_results(test_results):
    """OCR 결과를 파일로 저장"""
    print(f"\n💾 OCR 결과 저장")
    print("-"*30)
    
    for result in test_results:
        if result['text']:
            method_name = result['method'].replace(' ', '_')
            filename = f"ocr_result_{method_name}_IMG4790.txt"
            
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"=== {result['method']} OCR 결과 ===\n")
                    f.write(f"처리 시간: {result['time']:.3f}초\n")
                    f.write(f"추출 문자 수: {result['char_count']}\n")
                    f.write(f"단어 수: {result['word_count']}\n") 
                    f.write(f"한글 문자 수: {result['korean_chars']}\n")
                    f.write(f"\n텍스트 내용:\n")
                    f.write("-"*40 + "\n")
                    f.write(result['text'])
                
                print(f"   ✅ {filename}")
                
            except Exception as e:
                print(f"   ❌ {filename} 저장 실패: {e}")


def main():
    """메인 함수"""
    try:
        results = ocr_quality_test()
        save_ocr_results(results)
        
        print(f"\n🎯 최종 추천")
        print("="*40)
        
        # 결과 기반 추천
        valid_results = [r for r in results if r['time'] > 0]
        if valid_results:
            best_quality = max(valid_results, key=lambda x: x['char_count'])
            
            if '과학적' in best_quality['method']:
                print("✅ 과학적 전처리 시스템 추천")
                print("   - 최적화된 이미지 품질")
                print("   - 높은 OCR 정확도")
                print("   - 투명한 처리 과정")
            else:
                print(f"✅ {best_quality['method']} 방식 추천")
                print(f"   - 최다 텍스트 추출: {best_quality['char_count']}자")
        
        print(f"\n🏁 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()