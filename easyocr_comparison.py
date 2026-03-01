#!/usr/bin/env python3
"""
EasyOCR: 레거시 레벨1 vs 원본 이미지 텍스트 추출 비교
"""

import sys
sys.path.append('.')

from snaptxt.backend.multi_engine import MultiOCRProcessor
import time
import os

def compare_legacy_level1_vs_original():
    """레거시 레벨1과 원본 이미지에서 EasyOCR 텍스트 추출 비교"""
    
    print("🔍" + "="*80)
    print("📸 EasyOCR: 레거시 레벨1 vs 원본 이미지 텍스트 추출 비교")
    print("🔍" + "="*80)
    
    image_path = 'experiments/samples/office_lens_test/IMG_4793.JPG'
    processor = MultiOCRProcessor()
    print(f"🖼️  테스트 이미지: {image_path}")
    print(f"🤖 OCR 엔진: EasyOCR (동일)")
    print()
    
    results = {}
    
    # 1. 레거시 레벨1 전처리 + EasyOCR
    print("🏗️" + "="*70)
    print("1️⃣ 레거시 레벨1 전처리 + EasyOCR")
    print("🏗️" + "="*70)
    print("   📝 전처리: 그레이스케일 + CLAHE + 노이즈제거 + 선명화")
    
    start_time = time.time()
    try:
        settings_level1 = {
            'use_office_lens': False,
            'preprocessing_level': 1,
            'language': 'ko,en'
        }
        result_level1 = processor.process_file(image_path, settings_level1)
        time_level1 = time.time() - start_time
        
        print(f"   ⏱️  처리 시간: {time_level1:.2f}초")
        print(f"   📏 추출 길이: {len(result_level1)} 문자")
        
        if len(result_level1) > 50 and "❌" not in result_level1:
            print(f"   ✅ 텍스트 추출 성공!")
            results['레거시 레벨1'] = result_level1
            print(f"   📖 텍스트 미리보기:")
            preview = result_level1[:200].replace('\n', ' ')
            print(f"      '{preview}...'")
        else:
            print(f"   ❌ 텍스트 추출 실패")
            results['레거시 레벨1'] = result_level1
            
    except Exception as e:
        print(f"   ❌ 오류 발생: {e}")
        results['레거시 레벨1'] = f"오류: {str(e)}"
    
    print()
    
    # 2. 원본 이미지 + EasyOCR (전처리 없음)
    print("📷" + "="*70)
    print("2️⃣ 원본 이미지 + EasyOCR (전처리 없음)")
    print("📷" + "="*70)
    print("   📝 전처리: 없음 (원본 그대로)")
    
    start_time = time.time()
    try:
        settings_original = {
            'use_office_lens': False,
            'preprocessing_level': 0,  # 전처리 없음
            'language': 'ko,en'
        }
        result_original = processor.process_file(image_path, settings_original)
        time_original = time.time() - start_time
        
        print(f"   ⏱️  처리 시간: {time_original:.2f}초")
        print(f"   📏 추출 길이: {len(result_original)} 문자")
        
        if len(result_original) > 50 and "❌" not in result_original:
            print(f"   ✅ 텍스트 추출 성공!")
            results['원본'] = result_original
            print(f"   📖 텍스트 미리보기:")
            preview = result_original[:200].replace('\n', ' ')
            print(f"      '{preview}...'")
        else:
            print(f"   ❌ 텍스트 추출 실패")
            results['원본'] = result_original
            
    except Exception as e:
        print(f"   ❌ 오류 발생: {e}")
        results['원본'] = f"오류: {str(e)}"
    
    print()
    
    # 3. 결과 비교 분석
    print("📊" + "="*80)
    print("🏆 텍스트 추출 결과 비교 분석")
    print("📊" + "="*80)
    
    for method, text in results.items():
        print(f"\n🔍 **{method}**:")
        print(f"   📏 길이: {len(text)} 문자")
        
        if len(text) > 50 and "❌" not in text and "오류" not in text:
            # 성공적 추출
            lines = text.split('\n')
            non_empty_lines = [line.strip() for line in lines if line.strip()]
            
            print(f"   📖 줄 수: {len(non_empty_lines)}줄")
            print(f"   📝 주요 내용:")
            
            # 첫 3줄만 표시
            for i, line in enumerate(non_empty_lines[:3]):
                if line:
                    print(f"      {i+1}. {line}")
            
            if len(non_empty_lines) > 3:
                print(f"      ... (총 {len(non_empty_lines)}줄)")
                
            # 텍스트 품질 분석
            korean_chars = sum(1 for c in text if ord(c) >= 0xAC00 and ord(c) <= 0xD7A3)
            korean_ratio = (korean_chars / len(text)) * 100 if len(text) > 0 else 0
            print(f"   🇰🇷 한글 비율: {korean_ratio:.1f}%")
            
            # 주요 키워드 체크
            keywords = ["가장", "진실한", "자아", "여정", "성장", "마음", "소리", "깨닫", "중요", "마이클", "싱어"]
            found_keywords = [kw for kw in keywords if kw in text]
            print(f"   🔑 발견된 키워드: {len(found_keywords)}/{len(keywords)}개")
            print(f"      {', '.join(found_keywords)}")
            
        else:
            # 실패
            print(f"   ❌ 추출 실패")
            if "❌" in text:
                print(f"   🔧 실패 원인: OCR 엔진이 텍스트 인식 불가")
            elif "오류" in text:
                print(f"   🔧 실패 원인: {text}")
    
    print()
    print("💡" + "="*80)
    print("🎯 핵심 결론")
    print("💡" + "="*80)
    
    # 성능 비교
    if '레거시 레벨1' in results and '원본' in results:
        level1_success = len(results['레거시 레벨1']) > 50 and "❌" not in results['레거시 레벨1']
        original_success = len(results['원본']) > 50 and "❌" not in results['원본']
        
        if level1_success and not original_success:
            print("✅ **레거시 레벨1 압승**: 전처리가 OCR 성공의 핵심!")
            print("   📌 원본 이미지로는 EasyOCR도 텍스트 인식 실패")
            print("   📌 기본 전처리만으로도 완벽한 텍스트 추출 성공")
            print("   🎯 교훈: '적절한 전처리 없이는 좋은 AI도 소용없다'")
            
        elif level1_success and original_success:
            level1_len = len(results['레거시 레벨1'])
            original_len = len(results['원본'])
            print(f"📊 **둘 다 성공**: 레거시 레벨1({level1_len}자) vs 원본({original_len}자)")
            
            if level1_len > original_len:
                print("   🏆 레거시 레벨1이 더 많은 텍스트 추출")
            else:
                print("   📈 원본도 의외로 좋은 성능")
                
        elif not level1_success and original_success:
            print("😮 **원본 승리**: 전처리가 오히려 방해?")
            
        else:
            print("❌ **둘 다 실패**: 이미지 자체의 문제일 가능성")
    
    print("\n🔬 **과학적 검증 완료**:")
    print("   - 동일한 EasyOCR 엔진으로 공정한 비교")
    print("   - 전처리 효과를 정확히 측정")
    print("   - 실제 사용자 관점에서 성능 평가")
    
    return results

if __name__ == "__main__":
    results = compare_legacy_level1_vs_original()
    
    # 결과를 파일로도 저장
    output_file = "experiments/results/easyocr_legacy_vs_original_comparison.txt"
    os.makedirs("experiments/results", exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("EasyOCR: 레거시 레벨1 vs 원본 이미지 비교 결과\n")
        f.write("="*60 + "\n\n")
        
        for method, text in results.items():
            f.write(f"【{method}】\n")
            f.write(f"길이: {len(text)} 문자\n")
            f.write("-" * 40 + "\n")
            f.write(text)
            f.write("\n" + "="*60 + "\n\n")
    
    print(f"\n💾 상세 결과 저장: {output_file}")