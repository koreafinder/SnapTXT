#!/usr/bin/env python3
"""
IMG_4790 이미지를 사용한 과학적 전처리 성능 테스트

기존 레거시 시스템과 새로운 과학적 전처리 시스템을 직접 비교합니다.
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


def find_img_4790():
    """IMG_4790 이미지 파일 찾기"""
    test_dir = Path("uploads")
    if not test_dir.exists():
        print("❌ uploads 폴더가 없습니다.")
        return None
    
    # 가능한 파일명들
    candidates = [
        "IMG_4790.JPG",
        "IMG_4790.jpg", 
        "img_4790.jpg",
        "IMG_4790.png",
        "IMG_4790.jpeg"
    ]
    
    for filename in candidates:
        filepath = test_dir / filename
        if filepath.exists():
            print(f"✅ 테스트 이미지 발견: {filepath}")
            return filepath
    
    # 모든 이미지 파일 나열
    print("📁 uploads 폴더의 이미지 파일들:")
    image_files = []
    for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
        image_files.extend(test_dir.glob(f"*{ext}"))
    
    for img_file in image_files:
        print(f"   - {img_file.name}")
        
    if image_files:
        # 첫 번째 이미지를 사용
        selected = image_files[0]
        print(f"🎯 첫 번째 이미지를 테스트용으로 선택: {selected.name}")
        return selected
    
    return None


def analyze_image_details(image_path):
    """이미지 세부 정보 분석"""
    print(f"\n📊 이미지 세부 분석: {image_path.name}")
    print("="*50)
    
    # 이미지 로드
    image = cv2.imread(str(image_path))
    if image is None:
        print("❌ 이미지 로드 실패")
        return None
    
    h, w = image.shape[:2]
    file_size = image_path.stat().st_size
    
    print(f"📐 크기: {w} x {h} pixels")
    print(f"📁 파일 크기: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    print(f"🎨 색상 채널: {image.shape[2] if len(image.shape) == 3 else 1}")
    
    # 그레이스케일로 변환하여 기본 통계
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    
    print(f"💡 밝기 범위: {np.min(gray)} ~ {np.max(gray)}")
    print(f"💡 평균 밝기: {np.mean(gray):.1f}")
    print(f"📊 표준편차: {np.std(gray):.1f}")
    
    return image


def test_preprocessing_comparison(image, image_name):
    """전처리 시스템 성능 비교"""
    print(f"\n🔬 전처리 성능 비교 테스트: {image_name}")
    print("="*60)
    
    results = []
    
    # 1. 전처리 없음 (원본)
    print("\n1️⃣ 전처리 없음 (원본)")
    start_time = time.time()
    original = image.copy()
    time_original = time.time() - start_time
    
    print(f"   ⏱️ 시간: {time_original:.6f}초")
    print(f"   📊 상태: 원본 그대로")
    
    results.append(("원본", time_original, original))
    
    # 2-4. 레거시 전처리 (Level 1, 2, 3)
    for level in [1, 2, 3]:
        print(f"\n{level+1}️⃣ 레거시 전처리 Level {level}")
        
        try:
            start_time = time.time()
            processed_legacy = apply_default_filters(image, level=level)
            time_legacy = time.time() - start_time
            
            print(f"   ⏱️ 시간: {time_legacy:.6f}초")
            print(f"   📊 결과: {processed_legacy.shape}")
            
            results.append((f"레거시 L{level}", time_legacy, processed_legacy))
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            results.append((f"레거시 L{level}", 0, None))
    
    # 5. 과학적 전처리
    print(f"\n5️⃣ 과학적 전처리 시스템")
    
    try:
        start_time = time.time()
        processed_scientific, metrics, plan = smart_preprocess_image(image)
        time_scientific = time.time() - start_time
        
        print(f"   ⏱️ 시간: {time_scientific:.6f}초")
        print(f"   📊 품질 점수: {metrics.overall_quality:.3f}")
        print(f"   🎯 적용 액션: {len(plan.actions)}개")
        print(f"   💭 근거: {plan.rationale}")
        print(f"   🔍 신뢰도: {plan.confidence:.3f}")
        
        # 세부 메트릭
        print(f"   📏 DPI 추정: {metrics.dpi_estimate:.1f}")
        print(f"   ✨ 선명도: {metrics.sharpness:.3f}")
        print(f"   🌓 대비: {metrics.contrast:.3f}")
        print(f"   🔊 노이즈: {metrics.noise_level:.3f}")
        print(f"   📐 기울기: {metrics.skew_angle:.1f}°")
        print(f"   💡 밝기: {metrics.brightness:.3f}")
        
        results.append(("과학적", time_scientific, processed_scientific))
        
    except Exception as e:
        print(f"   ❌ 실패: {e}")
        results.append(("과학적", 0, None))
    
    return results


def save_comparison_images(results, image_name):
    """비교 결과 이미지들 저장"""
    print(f"\n💾 결과 이미지 저장")
    print("-"*30)
    
    saved_files = []
    
    for method, time_taken, processed_img in results:
        if processed_img is not None:
            # 파일명 생성
            safe_method = method.replace(" ", "_").replace("/", "_")
            filename = f"test_{image_name}_{safe_method}.png"
            
            try:
                cv2.imwrite(filename, processed_img)
                saved_files.append(filename)
                print(f"   ✅ {filename}")
                
            except Exception as e:
                print(f"   ❌ {filename} 저장 실패: {e}")
    
    print(f"\n📁 총 {len(saved_files)}개 파일 저장됨")
    return saved_files


def analyze_performance_metrics(results):
    """성능 메트릭 분석"""
    print(f"\n📈 성능 분석 결과")
    print("="*50)
    
    # 처리 시간 분석
    valid_results = [(method, time_taken) for method, time_taken, img in results if time_taken > 0]
    
    print("\n⏱️ 처리 시간 비교:")
    for method, time_taken in sorted(valid_results, key=lambda x: x[1]):
        print(f"   {method:12s}: {time_taken:.6f}초")
    
    if len(valid_results) >= 2:
        fastest = min(valid_results, key=lambda x: x[1])
        slowest = max(valid_results, key=lambda x: x[1])
        
        print(f"\n🏃 가장 빠름: {fastest[0]} ({fastest[1]:.6f}초)")
        print(f"🐌 가장 느림: {slowest[0]} ({slowest[1]:.6f}초)")
        print(f"⚡ 속도 차이: {slowest[1]/fastest[1]:.1f}배")
    
    # 이미지 품질 분석
    print(f"\n🎨 결과 이미지 품질 분석:")
    
    for method, time_taken, processed_img in results:
        if processed_img is not None:
            # 기본 통계
            if len(processed_img.shape) == 3:
                gray = cv2.cvtColor(processed_img, cv2.COLOR_BGR2GRAY)
            else:
                gray = processed_img
            
            unique_values = len(np.unique(gray))
            mean_brightness = np.mean(gray)
            contrast = np.std(gray)
            
            print(f"   {method:12s}: 고유값 {unique_values:3d}, 밝기 {mean_brightness:5.1f}, 대비 {contrast:5.1f}")


def recommend_optimal_setting(results):
    """최적 설정 추천"""
    print(f"\n🎯 추천 설정")
    print("="*40)
    
    # 과학적 전처리 결과 찾기
    scientific_result = None
    for method, time_taken, processed_img in results:
        if "과학적" in method and processed_img is not None:
            scientific_result = (method, time_taken, processed_img)
            break
    
    if scientific_result:
        print(f"✅ 과학적 전처리 시스템 사용 권장")
        print(f"   - 이미지별 최적화된 전처리")
        print(f"   - 과처리로 인한 품질 저하 방지")
        print(f"   - 투명한 처리 근거 제공")
        print(f"   - 처리 시간: {scientific_result[1]:.3f}초")
        
        print(f"\n💻 사용 코드:")
        print(f"   processor.preprocess_image(image, use_scientific=True)")
    else:
        print(f"⚠️ 과학적 전처리 시스템 실행 실패")
        print(f"   레거시 시스템 Level 2 권장")
        print(f"   processor.preprocess_image(image, preprocessing_level=2)")


def main():
    """메인 테스트 함수"""
    print("🔬 IMG_4790 과학적 전처리 성능 테스트")
    print("="*60)
    
    # 1. 이미지 파일 찾기
    image_path = find_img_4790()
    if image_path is None:
        print("❌ 테스트할 이미지가 없습니다.")
        return
    
    # 2. 이미지 세부 분석
    image = analyze_image_details(image_path)
    if image is None:
        return
    
    # 3. 전처리 성능 비교
    results = test_preprocessing_comparison(image, image_path.stem)
    
    # 4. 결과 이미지 저장
    saved_files = save_comparison_images(results, image_path.stem)
    
    # 5. 성능 분석
    analyze_performance_metrics(results)
    
    # 6. 최적 설정 추천
    recommend_optimal_setting(results)
    
    print(f"\n🏁 테스트 완료!")
    print("="*60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()