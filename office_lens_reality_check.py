#!/usr/bin/env python3
"""
Office Lens 샘플 10장 현실 검증 실험
- 레거시 레벨1 vs 실제 다양한 이미지 유형
- Adaptive Mode 필요성 입증
"""

import sys
sys.path.append('.')

from snaptxt.backend.multi_engine import MultiOCRProcessor
import cv2
import numpy as np
import os
from pathlib import Path
import time

def analyze_image_characteristics(image_path):
    """이미지 특성 분석 (GPT 5.2 기준과 비교)"""
    
    # 이미지 로드
    img = cv2.imread(image_path)
    if img is None:
        return None
        
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. 밝기 분산 (std) - 배경 복잡도
    brightness_std = np.std(gray)
    
    # 2. 엔트로피 - 텍스처 복잡도  
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist_norm = hist / hist.sum()
    entropy = -np.sum(hist_norm * np.log2(hist_norm + 1e-7))
    
    # 3. Edge density - 텍스트 가능성
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size
    
    # 4. 좌우 밝기 차이 - 비침 가능성
    h, w = gray.shape
    left_half = gray[:, :w//2]
    right_half = gray[:, w//2:]
    lr_diff = abs(np.mean(left_half) - np.mean(right_half))
    
    # 5. 컨투어 수 - 장식 요소
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour_count = len(contours)
    
    return {
        'brightness_std': brightness_std,
        'entropy': entropy,
        'edge_density': edge_density,
        'lr_brightness_diff': lr_diff,
        'contour_count': contour_count
    }

def classify_image_type(characteristics):
    """GPT 5.2 기준으로 이미지 유형 분류"""
    
    if characteristics is None:
        return "ERROR"
    
    std = characteristics['brightness_std']
    entropy = characteristics['entropy']
    edge_density = characteristics['edge_density']
    lr_diff = characteristics['lr_brightness_diff']
    contour_count = characteristics['contour_count']
    
    # GPT 5.2 분류 규칙 적용
    if edge_density < 0.05:  # Edge 낮음
        return "SKIP (텍스트 없음)"
    elif std < 30:  # std 낮음
        return "Type A (일반 텍스트)"
    elif entropy > 7.5:  # entropy 높음  
        return "Type B (배경 있는 텍스트)"
    elif lr_diff > 15:  # 좌우 밝기 차
        return "Type C (비침 페이지)"
    elif contour_count > 100:  # contour 많음
        return "Type D (장식 페이지)"
    else:
        return "Type A (일반 텍스트)"  # 기본값

def test_legacy_level1_on_diverse_images():
    """다양한 이미지에서 레거시 레벨1 성능 테스트"""
    
    print("🔍" + "="*80)
    print("📸 Office Lens 10장 샘플 - 레거시 레벨1 현실 검증")
    print("🔍" + "="*80)
    
    # 샘플 경로
    sample_dir = Path('experiments/samples/office_lens_test')
    if not sample_dir.exists():
        print(f"❌ 샘플 디렉터리가 없습니다: {sample_dir}")
        return
    
    # 이미지 파일 찾기
    image_files = list(sample_dir.glob("IMG_*.JPG"))
    if not image_files:
        print(f"❌ 이미지 파일이 없습니다: {sample_dir}")
        return
        
    print(f"📁 발견된 이미지: {len(image_files)}개")
    
    processor = MultiOCRProcessor()
    results = []
    
    for img_path in sorted(image_files):
        print(f"\n📷 {'='*60}")
        print(f"🖼️  {img_path.name}")
        print(f"📷 {'='*60}")
        
        # 1. 이미지 특성 분석
        characteristics = analyze_image_characteristics(str(img_path))
        img_type = classify_image_type(characteristics)
        
        print(f"🧠 GPT 5.2 분석 결과:")
        if characteristics:
            print(f"   📊 밝기 분산: {characteristics['brightness_std']:.1f}")
            print(f"   🌀 엔트로피: {characteristics['entropy']:.2f}")
            print(f"   ⚡ Edge 밀도: {characteristics['edge_density']:.3f}")
            print(f"   ↔️  좌우 밝기 차: {characteristics['lr_brightness_diff']:.1f}")
            print(f"   🔷 컨투어 수: {characteristics['contour_count']}")
        print(f"   🎯 분류: {img_type}")
        
        # 2. 레거시 레벨1으로 OCR 테스트
        print(f"\n🏗️ 레거시 레벨1 테스트:")
        
        start_time = time.time()
        try:
            settings = {
                'use_office_lens': False,
                'preprocessing_level': 1,
                'language': 'ko,en'
            }
            
            extracted_text = processor.process_file(str(img_path), settings)
            processing_time = time.time() - start_time
            
            text_length = len(extracted_text)
            success = text_length > 50 and "❌" not in extracted_text
            
            print(f"   ⏱️  처리 시간: {processing_time:.2f}초")
            print(f"   📏 추출 길이: {text_length}자")
            print(f"   ✅ 성공 여부: {'✅ 성공' if success else '❌ 실패'}")
            
            if success:
                # 텍스트 품질 간단 평가
                preview = extracted_text[:100].replace('\n', ' ')
                print(f"   📖 미리보기: '{preview}...'")
                
                # 한글 비율
                korean_chars = sum(1 for c in extracted_text if 0xAC00 <= ord(c) <= 0xD7A3)
                korean_ratio = korean_chars / text_length * 100 if text_length > 0 else 0
                print(f"   🇰🇷 한글 비율: {korean_ratio:.1f}%")
            
            results.append({
                'file': img_path.name,
                'type': img_type,
                'success': success,
                'length': text_length,
                'time': processing_time,
                'characteristics': characteristics
            })
            
        except Exception as e:
            print(f"   ❌ 오류: {e}")
            results.append({
                'file': img_path.name,
                'type': img_type,
                'success': False,
                'length': 0,
                'time': 0,
                'characteristics': characteristics
            })
    
    # 결과 종합 분석
    print(f"\n📊" + "="*80)
    print("🏆 종합 결과 분석")
    print(f"📊" + "="*80)
    
    print(f"\n📋 유형별 성능:")
    type_stats = {}
    for result in results:
        img_type = result['type']
        if img_type not in type_stats:
            type_stats[img_type] = {'total': 0, 'success': 0, 'avg_length': 0}
        
        type_stats[img_type]['total'] += 1
        if result['success']:
            type_stats[img_type]['success'] += 1
            type_stats[img_type]['avg_length'] += result['length']
    
    for img_type, stats in type_stats.items():
        success_rate = stats['success'] / stats['total'] * 100
        avg_length = stats['avg_length'] / max(stats['success'], 1)
        print(f"   {img_type}: {stats['success']}/{stats['total']} = {success_rate:.1f}% (평균 {avg_length:.0f}자)")
    
    print(f"\n💡 결론:")
    total_files = len(results)
    total_success = sum(1 for r in results if r['success'])
    overall_success_rate = total_success / total_files * 100
    
    print(f"   📈 전체 성공률: {total_success}/{total_files} = {overall_success_rate:.1f}%")
    
    if overall_success_rate < 80:
        print(f"   ❌ 레거시 레벨1 한계 입증: 다양한 이미지에서 성능 저하")
        print(f"   🎯 Adaptive Mode 필요성 확인")
    else:
        print(f"   ✅ 레거시 레벨1도 범용성 있음")
    
    # 상세 결과 저장
    output_file = "experiments/results/office_lens_reality_check.txt"
    os.makedirs("experiments/results", exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Office Lens 10장 샘플 현실 검증 결과\n")
        f.write("="*60 + "\n\n")
        
        for result in results:
            f.write(f"📁 {result['file']}\n")
            f.write(f"🎯 분류: {result['type']}\n")
            f.write(f"✅ 성공: {'✅' if result['success'] else '❌'} ({result['length']}자)\n")
            f.write(f"⏱️  시간: {result['time']:.2f}초\n")
            f.write("-" * 40 + "\n")
    
    print(f"\n💾 상세 결과 저장: {output_file}")
    
    return results

if __name__ == "__main__":
    results = test_legacy_level1_on_diverse_images()
    
    print("\n🎯 다음 단계 제안:")
    print("1. 각 유형별 최적 전처리 방법 개발")
    print("2. 자동 분류기 정확도 향상") 
    print("3. Adaptive Mode 구현")
    print("4. 속도 최적화")