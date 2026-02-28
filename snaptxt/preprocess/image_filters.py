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


def _stage_basic_filters(image: np.ndarray, log: logging.Logger) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    h, w = gray.shape
    if h < 600 or w < 600:
        scale_factor = max(600 / h, 600 / w)
        new_h, new_w = int(h * scale_factor), int(w * scale_factor)
        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        log.info("   이미지 확대: %sx%s → %sx%s", w, h, new_w, new_h)

    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    denoised = cv2.medianBlur(enhanced, 3)
    blurred = cv2.GaussianBlur(denoised, (5, 5), 1.5)
    sharpened = cv2.addWeighted(denoised, 1.5, blurred, -0.5, 0)

    log.info("   전처리 완료: 효과적인 3단계 (CLAHE → Median Blur → Gentle Sharpening)")
    return sharpened


def _stage_background_filters(image: np.ndarray, log: logging.Logger) -> np.ndarray:
    _, thresh_otsu = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh_adaptive_gaussian = cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
    )
    thresh_adaptive_mean = cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 21, 10
    )

    combined = cv2.bitwise_or(
        cv2.bitwise_or(thresh_otsu, thresh_adaptive_gaussian), thresh_adaptive_mean
    )
    blurred = cv2.GaussianBlur(combined, (5, 5), 0)
    sharpened = cv2.addWeighted(combined, 3.0, blurred, -2.0, 0)

    log.info("   전처리 완료: 고급 책 페이지 최적화 적용")
    return sharpened


def _stage_korean_enhancements(image: np.ndarray, log: logging.Logger) -> np.ndarray:
    kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
    kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3))
    h_connected = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel_horizontal)
    v_connected = cv2.morphologyEx(h_connected, cv2.MORPH_CLOSE, kernel_vertical)
    kernel_clean = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(v_connected, cv2.MORPH_OPEN, kernel_clean)
    final_enhanced = cv2.equalizeHist(cleaned)

    log.info("   전처리 완료: 최고급 한국어 텍스트 최적화 적용")
    return final_enhanced
