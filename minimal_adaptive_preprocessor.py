#!/usr/bin/env python3
"""
SnapTXT용 최소 연산 Adaptive 전처리 시스템
- 썸네일 기반 빠른 분석 (512px)
- 4타입 분류 (A: 본문, B: 배경, C: 그림자, D: 비침)  
- 최소 연산 전처리 (1-2개만)
- EasyOCR 최적화 + Fallback 전략
"""

import cv2
import numpy as np
from typing import Dict, Tuple, Optional, Any
import logging
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger(__name__)

class PageType(Enum):
    """페이지 유형 분류"""
    SKIP = "SKIP"           # 텍스트 없음 (빈 페이지)
    TYPE_A = "TYPE_A"       # 깨끗한 본문
    TYPE_B = "TYPE_B"       # 배경/텍스처 있음
    TYPE_C = "TYPE_C"       # 그림자/조명 불균일
    TYPE_D = "TYPE_D"       # 비침(bleed-through)

@dataclass
class ImageMetrics:
    """이미지 분석 지표"""
    brightness_mean: float     # 밝기 평균
    brightness_std: float      # 밝기 표준편차
    edge_density: float        # 에지 밀도 (0~1)
    lr_gradient: float         # 좌/우 밝기 차이
    tb_gradient: float         # 상/하 밝기 차이
    blur_variance: float       # 라플라시안 분산 (흐림 정도)
    
@dataclass
class PreprocessResult:
    """전처리 결과"""
    processed_image: np.ndarray
    page_type: PageType
    metrics: ImageMetrics
    processing_time: float
    retry_used: bool = False

class MinimalAdaptivePreprocessor:
    """최소 연산 Adaptive 전처리기"""
    
    # 분류 임계값 (실험으로 최적화 가능)
    THRESHOLDS = {
        'edge_density_min': 0.003,      # 0.3% 미만이면 텍스트 없음
        'std_min': 20,                  # 너무 낮으면 빈 페이지
        'std_high': 60,                 # 높으면 배경/텍스처
        'gradient_high': 25,            # 좌우 차이 크면 그림자
        'blur_threshold': 50,           # 라플라시안 분산 낮으면 흐림
    }
    
    def __init__(self, thumbnail_size: int = 512):
        """
        Args:
            thumbnail_size: 분석용 썸네일 크기 (기본 512px)
        """
        self.thumbnail_size = thumbnail_size
        
    def analyze_thumbnail(self, image: np.ndarray) -> ImageMetrics:
        """
        썸네일 기반 빠른 이미지 분석
        
        Args:
            image: 원본 이미지 (BGR 또는 그레이스케일)
            
        Returns:
            ImageMetrics: 분석 지표들
        """
        # 1. 썸네일 생성 (속도 최적화)
        h, w = image.shape[:2]
        if max(h, w) > self.thumbnail_size:
            scale = self.thumbnail_size / max(h, w)
            new_h, new_w = int(h * scale), int(w * scale)
            thumb = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            thumb = image
        
        # 2. 그레이스케일 변환
        if len(thumb.shape) == 3:
            gray = cv2.cvtColor(thumb, cv2.COLOR_BGR2GRAY)
        else:
            gray = thumb
        
        # 3. 빠른 지표 계산
        # 밝기 평균/표준편차
        brightness_mean = np.mean(gray)
        brightness_std = np.std(gray)
        
        # 에지 밀도
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # 좌/우 밝기 차이 (그림자 감지)
        th, tw = gray.shape
        left_half = gray[:, :tw//2]
        right_half = gray[:, tw//2:]
        lr_gradient = abs(np.mean(left_half) - np.mean(right_half))
        
        # 상/하 밝기 차이 (상하 그림자 감지)
        top_half = gray[:th//2, :]
        bottom_half = gray[th//2:, :]
        tb_gradient = abs(np.mean(top_half) - np.mean(bottom_half))
        
        # 라플라시안 분산 (흐림 감지)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        blur_variance = np.var(laplacian)
        
        return ImageMetrics(
            brightness_mean=brightness_mean,
            brightness_std=brightness_std,
            edge_density=edge_density,
            lr_gradient=lr_gradient,
            tb_gradient=tb_gradient,
            blur_variance=blur_variance
        )
    
    def classify_page_type(self, metrics: ImageMetrics) -> PageType:
        """
        지표 기반 페이지 유형 분류
        
        Args:
            metrics: 이미지 분석 지표
            
        Returns:
            PageType: 분류된 페이지 유형
        """
        T = self.THRESHOLDS
        
        # 1. 텍스트 없음 (빈 페이지) 먼저 체크
        if (metrics.edge_density < T['edge_density_min'] and 
            metrics.brightness_std < T['std_min']):
            return PageType.SKIP
        
        # 2. 그림자/조명 불균일 (좌우 또는 상하 차이 큼) - TYPE_B보다 먼저!
        max_gradient = max(metrics.lr_gradient, metrics.tb_gradient)
        if max_gradient > T['gradient_high']:
            return PageType.TYPE_C
        
        # 3. 배경/텍스처 (표준편차 높음)
        if metrics.brightness_std > T['std_high']:
            return PageType.TYPE_B
        
        # 4. 기본: 깨끗한 본문
        return PageType.TYPE_A
    
    def preprocess_type_a(self, image: np.ndarray) -> np.ndarray:
        """
        TYPE A: 깨끗한 본문 처리
        - 그레이스케일 + 약한 선명화
        """
        # 그레이스케일
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 약한 unsharp mask (선택적)
        blurred = cv2.GaussianBlur(gray, (5, 5), 1.0)
        sharpened = cv2.addWeighted(gray, 1.3, blurred, -0.3, 0)
        
        return sharpened
    
    def preprocess_type_b(self, image: np.ndarray) -> np.ndarray:
        """
        TYPE B: 배경/텍스처 있는 페이지
        - 그레이스케일 + 노이즈 제거 + 약한 대비 보정
        """
        # 그레이스케일
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 노이즈 제거 (median blur)
        denoised = cv2.medianBlur(gray, 3)
        
        # 약한 CLAHE (clipLimit 낮춤 - 한글에서 텍스처 부작용 방지)
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        return enhanced
    
    def preprocess_type_c(self, image: np.ndarray) -> np.ndarray:
        """
        TYPE C: 그림자/조명 불균일
        - 배경 평탄화 + 노이즈 제거
        """
        # 그레이스케일
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 배경 평탄화 (illumination correction)
        # 큰 커널로 배경 추정
        background = cv2.GaussianBlur(gray, (0, 0), sigmaX=30)
        
        # cv2.divide 방식으로 안정적 정규화
        normalized = cv2.divide(gray, background + 1, scale=255)
        normalized = normalized.astype(np.uint8)
        
        # 가벼운 노이즈 제거
        result = cv2.medianBlur(normalized, 3)
        
        return result
    
    def preprocess_type_d(self, image: np.ndarray) -> np.ndarray:
        """
        TYPE D: 비침(bleed-through)
        - TYPE C + 로컬 threshold + 모폴로지
        """
        # 먼저 TYPE C 처리 (배경 평탄화)
        normalized = self.preprocess_type_c(image)
        
        # 로컬 adaptive threshold (약하게)
        adaptive = cv2.adaptiveThreshold(
            normalized, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
            cv2.THRESH_BINARY, blockSize=21, C=10
        )
        
        # 작은 모폴로지 closing (글자 연결)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        result = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel)
        
        return result
    
    def safe_crop(self, image: np.ndarray, crop_ratio: float = 0.02) -> np.ndarray:
        """
        안전한 가장자리 크롭 (손가락/테두리 제거)
        
        Args:
            image: 입력 이미지
            crop_ratio: 크롭 비율 (기본 2%)
            
        Returns:
            크롭된 이미지
        """
        h, w = image.shape[:2]
        crop_h = int(h * crop_ratio)
        crop_w = int(w * crop_ratio)
        
        return image[crop_h:h-crop_h, crop_w:w-crop_w]
    
    def process(self, image: np.ndarray, apply_crop: bool = True) -> PreprocessResult:
        """
        메인 전처리 파이프라인
        
        Args:
            image: 입력 이미지 (BGR 또는 그레이스케일)
            apply_crop: 가장자리 크롭 적용 여부
            
        Returns:
            PreprocessResult: 전처리 결과
        """
        start_time = time.time()
        
        # 1. 안전한 크롭 (옵션)
        work_image = self.safe_crop(image) if apply_crop else image
        
        # 2. 썸네일 분석
        metrics = self.analyze_thumbnail(work_image)
        logger.info(f"📊 이미지 분석: std={metrics.brightness_std:.1f}, "
                   f"edge={metrics.edge_density:.3f}, grad={metrics.lr_gradient:.1f}")
        
        # 3. 페이지 타입 분류
        page_type = self.classify_page_type(metrics)
        logger.info(f"🎯 분류 결과: {page_type.value}")
        
        # 4. 타입별 전처리
        if page_type == PageType.SKIP:
            # 텍스트 없음 - 원본 그대로 (OCR 스킵할 예정)
            processed = work_image
        elif page_type == PageType.TYPE_A:
            processed = self.preprocess_type_a(work_image)
        elif page_type == PageType.TYPE_B:
            processed = self.preprocess_type_b(work_image)
        elif page_type == PageType.TYPE_C:
            processed = self.preprocess_type_c(work_image)
        else:  # TYPE_D는 fallback에서만 사용
            processed = self.preprocess_type_a(work_image)  # 기본 처리
        
        processing_time = time.time() - start_time
        
        return PreprocessResult(
            processed_image=processed,
            page_type=page_type,
            metrics=metrics,
            processing_time=processing_time
        )
    
    def fallback_process(self, image: np.ndarray, original_result: PreprocessResult, 
                        ocr_confidence: float) -> PreprocessResult:
        """
        Fallback 전처리 (1차 OCR 결과가 나쁠 때만)
        
        Args:
            image: 원본 이미지
            original_result: 1차 전처리 결과
            ocr_confidence: 1차 OCR 평균 신뢰도
            
        Returns:
            강화된 전처리 결과
        """
        start_time = time.time()
        
        logger.info(f"🔄 Fallback 처리 시작 (신뢰도: {ocr_confidence:.2f})")
        
        work_image = self.safe_crop(image)
        metrics = original_result.metrics
        
        # 세분화된 Fallback 전략
        if original_result.page_type == PageType.TYPE_B:
            # TYPE_B였다면: CLAHE 끄고 노이즈 억제 강화
            if len(image.shape) == 3:
                gray = cv2.cvtColor(work_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = work_image
            processed = cv2.medianBlur(gray, 5)  # 강화된 노이즈 제거
            fallback_type = PageType.TYPE_B
            
        elif original_result.page_type == PageType.TYPE_C:
            # TYPE_C였다면: 평탄화 파라미터 강화
            if len(image.shape) == 3:
                gray = cv2.cvtColor(work_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = work_image
            background = cv2.GaussianBlur(gray, (0, 0), sigmaX=35)  # 더 큰 커널
            processed = cv2.divide(gray, background + 1, scale=255).astype(np.uint8)
            processed = cv2.medianBlur(processed, 3)
            fallback_type = PageType.TYPE_C
            
        else:
            # 심각한 경우에만 TYPE_D (이진화) 사용
            if (ocr_confidence < 0.20 and 
                metrics.edge_density > 0.01 and 
                metrics.brightness_std < 40):
                processed = self.preprocess_type_d(work_image)
                fallback_type = PageType.TYPE_D
            else:
                # 기본 강화 처리
                processed = self.preprocess_type_c(work_image)
                fallback_type = PageType.TYPE_C
        
        processing_time = time.time() - start_time
        
        return PreprocessResult(
            processed_image=processed,
            page_type=fallback_type,
            metrics=original_result.metrics,  # 지표는 재사용
            processing_time=processing_time,
            retry_used=True
        )

# 사용 예시 (실행 방지용 - 실제 SnapTXT 통합시 필요)
def example_integration():
    """SnapTXT 통합 예시 (복사해도 자동 실행 안됨)"""
    
    # 초기화
    preprocessor = MinimalAdaptivePreprocessor(thumbnail_size=512)
    
    # 이미지 로드
    image = cv2.imread("test_image.jpg")
    
    # 1차 전처리
    result = preprocessor.process(image)
    
    if result.page_type == PageType.SKIP:
        print("텍스트 없는 페이지 - OCR 스킵")
        return
    
    # OCR 실행 (EasyOCR)
    # ocr_result, avg_confidence = your_easyocr_function(result.processed_image)
    
    # Fallback 조건 체크
    fallback_needed = False
    # if (avg_confidence < 0.35 or len(ocr_result) < 30):
    #     fallback_needed = True
    
    if fallback_needed:
        print("Fallback 처리 중...")
        result = preprocessor.fallback_process(image, result, 0.3)
        # ocr_result, avg_confidence = your_easyocr_function(result.processed_image)
    
    print(f"최종 결과: {result.page_type.value}, "
          f"처리시간: {result.processing_time:.2f}초")

if __name__ == "__main__":
    print("⚠️ 이 모듈은 import 전용입니다. SnapTXT에 통합해서 사용하세요.")
    print("📖 통합 예시는 example_integration() 함수를 참고하세요.")