"""Shared image preprocessing utilities used by every OCR entrypoint."""

from __future__ import annotations

import logging
from typing import Any, Optional, Union

import cv2
import numpy as np
from PIL import Image


logger = logging.getLogger(__name__)

ArrayLike = Union[np.ndarray, Image.Image]


def apply_default_filters(
    image: ArrayLike,
    level: int = 1,
    *,
    logger_override: Optional[logging.Logger] = None,
) -> np.ndarray:
    """Apply the legacy CLAHE/Adaptive pipeline with configurable depth."""

    log = logger_override or logger
    cv_image = _ensure_bgr_image(image)
    original = cv_image.copy()

    try:
        log.info("   입력 이미지 크기: %s", cv_image.shape)

        if level <= 0:
            log.info("   전처리 완료: 원본 이미지 사용")
            return cv_image

        processed = cv_image

        if level >= 1:
            processed = _stage_basic_filters(processed, log)

        if level >= 2:
            processed = _stage_background_filters(processed, log)

        if level >= 3:
            processed = _stage_korean_enhancements(processed, log)

        return processed
    except Exception as exc:
        log.warning("⚠️ 이미지 전처리 실패, 원본 사용: %s", exc)
        return cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)


def _ensure_bgr_image(image: ArrayLike) -> np.ndarray:
    if isinstance(image, Image.Image):
        arr = np.array(image)
        if arr.ndim == 2:
            return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    if isinstance(image, np.ndarray):
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        return image.copy()

    raise TypeError("Unsupported image type for preprocessing: %r" % type(image))


def _stage_basic_filters(image: np.ndarray, log: logging.Logger, debug_save: bool = False) -> np.ndarray:
    """Stage 1: 기본 전처리 (CLAHE + 노이즈 제거 + 선명화)"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    log.info("🌌 그레이스케일 변환 완료: %s", gray.shape)

    h, w = gray.shape
    original_size = (w, h)
    
    # 크기 조정 로직
    if h < 600 or w < 600:
        scale_factor = max(600 / h, 600 / w)
        new_h, new_w = int(h * scale_factor), int(w * scale_factor)
        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        log.info("📈 이미지 확대: %dx%d → %dx%d (배율: %.2f)", w, h, new_w, new_h, scale_factor)
    else:
        log.info("💯 이미지 크기 충분: %dx%d (확대 불필요)", w, h)

    # CLAHE 적용
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    log.info("✨ CLAHE 대비 향상 완료 (clipLimit=4.0, grid=8x8)")
    
    if debug_save:
        cv2.imwrite('debug_clahe.png', enhanced)
        log.info("💾 CLAHE 결과 저장: debug_clahe.png")

    # 노이즈 제거
    denoised = cv2.medianBlur(enhanced, 3)
    log.info("🎨 노이즈 제거 완료 (median blur, kernel=3)")
    
    # 부드러운 선명화
    blurred = cv2.GaussianBlur(denoised, (5, 5), 1.5)
    sharpened = cv2.addWeighted(denoised, 1.5, blurred, -0.5, 0)
    log.info("⚔️ 선명화 완료 (unsharp masking, weight=1.5/-0.5)")
    
    if debug_save:
        cv2.imwrite('debug_sharpened.png', sharpened)
        log.info("💾 선명화 결과 저장: debug_sharpened.png")

    # 통계 정보
    min_val, max_val = np.min(sharpened), np.max(sharpened)
    mean_val = np.mean(sharpened)
    log.info("📊 픽셀 범위: %d~%d, 평균: %.1f", min_val, max_val, mean_val)

    log.info("✅ Stage 1 완료: 기본 필터 체인 (CLAHE → Median Blur → Gentle Sharpening)")
    return sharpened


def _stage_background_filters(image: np.ndarray, log: logging.Logger, debug_save: bool = False) -> np.ndarray:
    """Stage 2: 배경 최적화 (다중 임계값 + 적응적 이진화)"""
    log.info("🎨 배경 최적화 시작, 입력 픽셀 범위: %d~%d", np.min(image), np.max(image))
    
    # Otsu 임계값
    thresh_val, thresh_otsu = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    log.info("🎯 Otsu 임계값: %.1f, 이진화 완료", thresh_val)
    
    if debug_save:
        cv2.imwrite('debug_otsu.png', thresh_otsu)
        log.info("💾 Otsu 결과 저장: debug_otsu.png")
    
    # 적응적 임계값 (Gaussian)
    thresh_adaptive_gaussian = cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
    )
    gauss_pixels = np.sum(thresh_adaptive_gaussian == 255)
    log.info("🌌 적응적 Gaussian: 흰색 픽셀 %d개", gauss_pixels)
    
    # 적응적 임계값 (Mean)  
    thresh_adaptive_mean = cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 21, 10
    )
    mean_pixels = np.sum(thresh_adaptive_mean == 255)
    log.info("📊 적응적 Mean: 흰색 픽셀 %d개", mean_pixels)

    # 다중 임계값 결합
    combined = cv2.bitwise_or(
        cv2.bitwise_or(thresh_otsu, thresh_adaptive_gaussian), thresh_adaptive_mean
    )
    combined_pixels = np.sum(combined == 255)
    log.info("♾️ 다중 임계값 결합: 흰색 픽셀 %d개", combined_pixels)
    
    if debug_save:
        cv2.imwrite('debug_combined.png', combined)
        log.info("💾 결합 결과 저장: debug_combined.png")
    
    # 추가 후처리
    blurred = cv2.GaussianBlur(combined, (5, 5), 0)
    sharpened = cv2.addWeighted(combined, 3.0, blurred, -2.0, 0)
    
    # 결과 범위 제한
    sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
    final_pixels = np.sum(sharpened == 255)
    log.info("✨ 최종 선명화: 흰색 픽셀 %d개", final_pixels)
    
    if debug_save:
        cv2.imwrite('debug_stage2_final.png', sharpened)
        log.info("💾 Stage2 최종 결과 저장: debug_stage2_final.png")

    log.info("✅ Stage 2 완료: 고급 책 페이지 최적화 적용")
    return sharpened


def _stage_korean_enhancements(image: np.ndarray, log: logging.Logger, debug_save: bool = False) -> np.ndarray:
    """Stage 3: 한국어 특화 처리 (모폴로지 + 히스토그램 균등화)"""
    log.info("🇰🇷 한국어 특화 처리 시작, 입력 픽셀 범위: %d~%d", np.min(image), np.max(image))
    
    # 범위 검증
    if np.sum(image == 255) < (image.shape[0] * image.shape[1] * 0.1):
        log.warning("⚠️ 경고: 흰색 픽셀 너무 적음! (전체의 %.1f%%) - Stage 3 위험할 수 있음", 
                   np.sum(image == 255) / (image.shape[0] * image.shape[1]) * 100)
    
    # 수평 연결
    kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
    h_connected = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel_horizontal)
    h_pixels = np.sum(h_connected == 255)
    log.info("↔️ 수평 연결: 흰색 픽셀 %d개 (변화: %+d)", 
             h_pixels, h_pixels - np.sum(image == 255))
    
    if debug_save:
        cv2.imwrite('debug_horizontal.png', h_connected)
        log.info("💾 수평 연결 결과 저장: debug_horizontal.png")
    
    # 수직 연결
    kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3))
    v_connected = cv2.morphologyEx(h_connected, cv2.MORPH_CLOSE, kernel_vertical)
    v_pixels = np.sum(v_connected == 255)
    log.info("↕️ 수직 연결: 흰색 픽셀 %d개 (변화: %+d)", 
             v_pixels, v_pixels - h_pixels)
    
    # 노이즈 제거
    kernel_clean = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(v_connected, cv2.MORPH_OPEN, kernel_clean)
    clean_pixels = np.sum(cleaned == 255)
    log.info("🧹 노이즈 제거: 흰색 픽셀 %d개 (변화: %+d)", 
             clean_pixels, clean_pixels - v_pixels)
    
    if debug_save:
        cv2.imwrite('debug_cleaned.png', cleaned)
        log.info("💾 노이즈 제거 결과 저장: debug_cleaned.png")
    
    # 히스토그램 균등화
    final_enhanced = cv2.equalizeHist(cleaned)
    final_pixels = np.sum(final_enhanced >= 128)  # 밝은 픽셀 카운트
    log.info("📊 히스토그램 균등화: 밝은 픽셀 %d개", final_pixels)
    
    # 최종 통계
    unique_values = len(np.unique(final_enhanced))
    log.info("🏆 Stage 3 최종 결과: 고유값 %d개, 픽셀 범위 %d~%d", 
             unique_values, np.min(final_enhanced), np.max(final_enhanced))
    
    if debug_save:
        cv2.imwrite('debug_stage3_final.png', final_enhanced)
        log.info("💾 Stage3 최종 결과 저장: debug_stage3_final.png")
    
    # 결과 검증
    if np.sum(final_enhanced >= 128) < (final_enhanced.shape[0] * final_enhanced.shape[1] * 0.05):
        log.error("❌ 심각한 오류: Stage 3 결과에 가독한 픽셀이 너무 적음! OCR 실패 예상")
    
    log.info("✅ Stage 3 완료: 최고급 한국어 텍스트 최적화 적용")
    return final_enhanced
