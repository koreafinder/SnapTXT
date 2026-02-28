"""
Level 1 전처리 시각화 도구
원본 vs 전처리 비교 이미지 생성
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from snaptxt.preprocess.image_filters import apply_default_filters
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import font_manager
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def create_comparison_images():
    """원본 vs Level 1 전처리 비교 이미지 생성"""
    
    # 테스트할 대표 이미지들
    test_images = [
        "uploads/IMG_4794.JPG",  # 문제가 된 이미지
        "uploads/IMG_4790.JPG",  # 성공한 이미지 
        "uploads/IMG_4791.JPG",  # 다른 샘플
    ]
    
    logger.info(f"🎨 Level 1 전처리 시각화 시작")
    logger.info(f"📄 대상 이미지: {len(test_images)}개")
    
    # 각 이미지별로 비교 생성
    for i, img_path in enumerate(test_images):
        if not os.path.exists(img_path):
            logger.warning(f"⚠️ 파일 없음: {img_path}")
            continue
            
        filename = os.path.basename(img_path).replace('.JPG', '')
        logger.info(f"\n📷 === {filename} 처리 중 ===")
        
        try:
            # 원본 이미지 로드
            original = cv2.imread(img_path)
            if original is None:
                logger.error(f"❌ 이미지 로드 실패: {filename}")
                continue
            
            original_rgb = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)
            h, w = original.shape[:2]
            logger.info(f"📊 원본 크기: {w}x{h}")
            
            # Level 1 전처리 적용
            logger.info(f"🔧 Level 1 전처리 적용 중...")
            processed = apply_default_filters(original, level=1)
            
            # 전처리 결과를 RGB로 변환 (그레이스케일이면)
            if len(processed.shape) == 2:
                processed_rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
            else:
                processed_rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
            
            # 이미지 크기 조정 (비교를 위해 같은 크기로)
            target_size = (800, 1200)  # 적절한 표시 크기
            
            original_resized = cv2.resize(original_rgb, target_size)
            processed_resized = cv2.resize(processed_rgb, target_size)
            
            # 비교 이미지 생성
            plt.figure(figsize=(16, 10))
            
            # 원본 이미지
            plt.subplot(1, 2, 1)
            plt.imshow(original_resized)
            plt.title(f'{filename} - 원본', fontsize=16, pad=20)
            plt.axis('off')
            
            # 처리된 이미지
            plt.subplot(1, 2, 2)
            plt.imshow(processed_resized)
            plt.title(f'{filename} - Level 1 전처리', fontsize=16, pad=20)
            plt.axis('off')
            
            # 전체 제목
            plt.suptitle(f'📷 {filename}: 원본 vs Level 1 전처리 비교', fontsize=20, y=0.95)
            
            # 저장
            output_file = f"visual_comparison_{filename}_level1.png"
            plt.tight_layout()
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"💾 비교 이미지 저장: {output_file}")
            
            # 추가: 각각 개별 저장 (더 자세한 확인용)
            individual_original = f"individual_original_{filename}.png"
            individual_processed = f"individual_processed_{filename}_level1.png"
            
            cv2.imwrite(individual_original, original)
            cv2.imwrite(individual_processed, processed)
            
            logger.info(f"💾 개별 저장:")
            logger.info(f"   - 원본: {individual_original}")
            logger.info(f"   - Level1: {individual_processed}")
            
        except Exception as e:
            logger.error(f"❌ {filename} 처리 실패: {e}")
    
    # 전체 요약 이미지 생성 (모든 결과를 한 번에)
    create_summary_comparison()
    
def create_summary_comparison():
    """모든 전처리 결과를 한 눈에 비교"""
    
    logger.info(f"\n🎨 전체 요약 비교 이미지 생성")
    
    # 대표 이미지들
    representatives = [
        ("uploads/IMG_4794.JPG", "문제 이미지"),
        ("uploads/IMG_4790.JPG", "성공 이미지"),
    ]
    
    fig, axes = plt.subplots(2, 4, figsize=(20, 12))
    fig.suptitle('📊 SnapTXT 전처리 효과 전체 비교', fontsize=24, y=0.95)
    
    for row, (img_path, description) in enumerate(representatives):
        if not os.path.exists(img_path):
            continue
            
        filename = os.path.basename(img_path).replace('.JPG', '')
        
        try:
            # 원본 로드
            original = cv2.imread(img_path)
            original_rgb = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)
            
            # 다양한 전처리 레벨
            level1 = apply_default_filters(original, level=1)
            level2 = apply_default_filters(original, level=2) 
            level3 = apply_default_filters(original, level=3)
            
            # 그레이스케일을 RGB로 변환
            if len(level1.shape) == 2:
                level1 = cv2.cvtColor(level1, cv2.COLOR_GRAY2RGB)
            if len(level2.shape) == 2:
                level2 = cv2.cvtColor(level2, cv2.COLOR_GRAY2RGB)
            if len(level3.shape) == 2:
                level3 = cv2.cvtColor(level3, cv2.COLOR_GRAY2RGB)
            
            # 크기 조정
            target_size = (400, 600)
            original_small = cv2.resize(original_rgb, target_size)
            level1_small = cv2.resize(level1, target_size)
            level2_small = cv2.resize(level2, target_size)
            level3_small = cv2.resize(level3, target_size)
            
            # 이미지 배치
            images = [original_small, level1_small, level2_small, level3_small]
            titles = ['원본', 'Level 1\n(권장)', 'Level 2', 'Level 3']
            colors = ['blue', 'green', 'orange', 'red']
            
            for col, (img, title, color) in enumerate(zip(images, titles, colors)):
                ax = axes[row, col]
                ax.imshow(img)
                ax.set_title(title, fontsize=14, color=color, weight='bold')
                ax.axis('off')
                
                # Level 1에 추천 표시
                if col == 1:  # Level 1
                    rect = patches.Rectangle((0, 0), img.shape[1]-1, img.shape[0]-1, 
                                           linewidth=5, edgecolor='green', facecolor='none')
                    ax.add_patch(rect)
                    ax.text(img.shape[1]//2, 30, '✅ 최적', ha='center', 
                           fontsize=16, color='green', weight='bold',
                           bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="green"))
            
            # 행 제목
            axes[row, 0].text(-50, img.shape[0]//2, f'{description}\n({filename})', 
                            rotation=90, ha='center', va='center', fontsize=14, weight='bold')
            
        except Exception as e:
            logger.error(f"❌ {filename} 요약 비교 실패: {e}")
    
    plt.tight_layout()
    plt.savefig("SUMMARY_preprocessing_comparison.png", dpi=200, bbox_inches='tight')
    plt.close()
    
    logger.info(f"💾 전체 요약: SUMMARY_preprocessing_comparison.png")

if __name__ == "__main__":
    print("\n👁️ Level 1 전처리 시각적 검증 시스템")
    print("=" * 60)
    print("🎯 목적: 전처리가 텍스트를 보존하는지 직접 확인")
    print("")
    
    create_comparison_images()
    
    print(f"\n✅ 시각화 완료!")
    print(f"📄 생성된 파일들을 확인하세요:")
    print(f"   1. visual_comparison_*.png - 개별 비교")
    print(f"   2. individual_*.png - 고해상도 개별 이미지")
    print(f"   3. SUMMARY_preprocessing_comparison.png - 전체 비교")
    print(f"")
    print(f"👀 직접 눈으로 확인 포인트:")
    print(f"   ✅ 텍스트가 선명해졌는가?")
    print(f"   ✅ 글자가 뭉개지지 않았는가?") 
    print(f"   ✅ 배경 노이즈가 줄어들었는가?")
    print(f"   ❌ 텍스트가 사라지지 않았는가?")