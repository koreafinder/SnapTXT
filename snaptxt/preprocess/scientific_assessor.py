"""Scientific Image Quality Assessment for OCR Preprocessing

이 모듈은 이미지 품질을 과학적으로 평가하여 
OCR에 최적화된 전처리를 자동으로 결정하는 시스템입니다.

Based on research from:
- PaddleOCR PP-DocLayoutV3
- Tesseract Quality Guidelines  
- Computer Vision Best Practices
"""

import cv2
import numpy as np
from typing import Dict, Tuple, Optional, List
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PreprocessingAction(Enum):
    """전처리 액션 유형"""
    DENOISE = "denoise"
    ENHANCE_CONTRAST = "enhance_contrast"
    DESKEW = "deskew"  
    RESIZE = "resize"
    SHARPEN = "sharpen"
    NORMALIZE = "normalize"
    BINARIZE = "binarize"


@dataclass
class QualityMetrics:
    """이미지 품질 평가 메트릭"""
    resolution: Tuple[int, int]  # (width, height)
    dpi_estimate: float  # 추정 DPI
    sharpness: float  # 선명도 (0-1)
    contrast: float  # 대비 (0-1) 
    noise_level: float  # 노이즈 수준 (0-1)
    skew_angle: float  # 기울기 (도)
    brightness: float  # 밝기 (0-1)
    text_ratio: float  # 텍스트 영역 비율 (0-1)
    overall_quality: float  # 종합 품질 점수 (0-1)


@dataclass
class PreprocessingPlan:
    """전처리 계획"""
    actions: List[PreprocessingAction]
    parameters: Dict[str, any]
    confidence: float  # 계획에 대한 신뢰도 (0-1)
    rationale: str  # 결정 근거


class ScientificImageAssessor:
    """과학적 이미지 품질 평가기"""
    
    # OCR에 최적화된 임계값들 (연구 기반)
    OPTIMAL_DPI_MIN = 300
    OPTIMAL_DPI_MAX = 600
    MIN_SHARPNESS = 0.3
    MIN_CONTRAST = 0.2
    MAX_NOISE_LEVEL = 0.3
    MAX_SKEW_ANGLE = 2.0  # 도
    OPTIMAL_BRIGHTNESS_RANGE = (0.3, 0.7)
    MIN_TEXT_RATIO = 0.05
    
    def __init__(self):
        """이미지 평가기 초기화"""
        self.logger = logger
        
    def assess_image(self, image: np.ndarray) -> QualityMetrics:
        """
        과학적 방법으로 이미지 품질을 종합 평가
        
        Args:
            image: 입력 이미지 (BGR 또는 Grayscale)
            
        Returns:
            QualityMetrics: 품질 평가 결과
        """
        # 그레이스케일로 변환
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
            
        h, w = gray.shape
        
        # 각 메트릭 계산
        metrics = QualityMetrics(
            resolution=(w, h),
            dpi_estimate=self._estimate_dpi(gray),
            sharpness=self._calculate_sharpness(gray),
            contrast=self._calculate_contrast(gray),
            noise_level=self._estimate_noise_level(gray),
            skew_angle=self._detect_skew_angle(gray),
            brightness=self._calculate_brightness(gray),
            text_ratio=self._estimate_text_ratio(gray),
            overall_quality=0.0  # 나중에 계산
        )
        
        # 종합 품질 점수 계산
        metrics.overall_quality = self._calculate_overall_quality(metrics)
        
        self.logger.info(f"🔍 이미지 품질 평가 완료: {metrics.overall_quality:.3f}")
        self.logger.info(f"   해상도: {w}x{h}, DPI: {metrics.dpi_estimate:.1f}")
        self.logger.info(f"   선명도: {metrics.sharpness:.3f}, 대비: {metrics.contrast:.3f}")
        self.logger.info(f"   노이즈: {metrics.noise_level:.3f}, 기울기: {metrics.skew_angle:.1f}°")
        
        return metrics
    
    def _estimate_dpi(self, gray: np.ndarray) -> float:
        """DPI 추정 (텍스트 크기 기반)"""
        h, w = gray.shape
        
        # 기본 가정: A4 문서 크기
        # A4 = 210mm x 297mm
        a4_width_mm = 210
        a4_height_mm = 297
        
        # 픽셀 밀도 계산 (가정)
        dpi_x = (w / a4_width_mm) * 25.4
        dpi_y = (h / a4_height_mm) * 25.4
        
        return (dpi_x + dpi_y) / 2
    
    def _calculate_sharpness(self, gray: np.ndarray) -> float:
        """선명도 계산 (Laplacian variance 기반)"""
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        
        # 정규화 (경험적 최대값 기준)
        max_variance = 10000  # 일반적인 선명한 이미지의 variance
        return min(variance / max_variance, 1.0)
    
    def _calculate_contrast(self, gray: np.ndarray) -> float:
        """대비 계산 (Michelson contrast)"""
        # 히스토그램 기반 대비 계산
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        
        # 95th percentile과 5th percentile 사용
        cumsum = np.cumsum(hist.flatten())
        total = cumsum[-1]
        
        p5_idx = np.argmax(cumsum >= total * 0.05)
        p95_idx = np.argmax(cumsum >= total * 0.95)
        
        if p95_idx + p5_idx == 0:
            return 0.0
            
        michelson = (p95_idx - p5_idx) / (p95_idx + p5_idx)
        return min(michelson, 1.0)
    
    def _estimate_noise_level(self, gray: np.ndarray) -> float:
        """노이즈 수준 추정 (표준편차 기반)"""
        # 가우시안 블러를 적용한 후 원본과의 차이로 노이즈 추정
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = cv2.subtract(gray, blurred)
        noise_std = np.std(noise)
        
        # 정규화 (경험적 최대값)
        max_noise = 50  # 일반적인 노이지한 이미지의 표준편차
        return min(noise_std / max_noise, 1.0)
    
    def _detect_skew_angle(self, gray: np.ndarray) -> float:
        """기울기 각도 검출 (Hough 변환 기반)"""
        # 엣지 검출
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Hough 직선 검출
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
        
        if lines is None or len(lines) == 0:
            return 0.0
        
        # 각도 수집
        angles = []
        for rho, theta in lines[:, 0]:
            angle = np.degrees(theta) - 90
            # -45도 ~ +45도 범위로 정규화
            if angle > 45:
                angle -= 90
            elif angle < -45:
                angle += 90
            angles.append(angle)
        
        # 중앙값 반환 (이상치 제거)
        if angles:
            return np.median(angles)
        return 0.0
    
    def _calculate_brightness(self, gray: np.ndarray) -> float:
        """밝기 계산 (평균 픽셀값)"""
        return np.mean(gray) / 255.0
    
    def _estimate_text_ratio(self, gray: np.ndarray) -> float:
        """텍스트 영역 비율 추정"""
        # 이진화 후 텍스트 픽셀 비율 계산
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text_pixels = np.sum(binary == 0)  # 검은 픽셀 = 텍스트
        total_pixels = gray.size
        
        return text_pixels / total_pixels
    
    def _calculate_overall_quality(self, metrics: QualityMetrics) -> float:
        """종합 품질 점수 계산 (가중 평균)"""
        scores = []
        weights = []
        
        # DPI 점수
        if metrics.dpi_estimate < self.OPTIMAL_DPI_MIN:
            dpi_score = metrics.dpi_estimate / self.OPTIMAL_DPI_MIN
        elif metrics.dpi_estimate > self.OPTIMAL_DPI_MAX:
            dpi_score = self.OPTIMAL_DPI_MAX / metrics.dpi_estimate
        else:
            dpi_score = 1.0
        scores.append(dpi_score)
        weights.append(0.2)
        
        # 선명도 점수
        sharpness_score = min(metrics.sharpness / self.MIN_SHARPNESS, 1.0)
        scores.append(sharpness_score)
        weights.append(0.25)
        
        # 대비 점수
        contrast_score = min(metrics.contrast / self.MIN_CONTRAST, 1.0)
        scores.append(contrast_score)
        weights.append(0.2)
        
        # 노이즈 점수 (낮을수록 좋음)
        noise_score = 1.0 - min(metrics.noise_level / self.MAX_NOISE_LEVEL, 1.0)
        scores.append(noise_score)
        weights.append(0.15)
        
        # 기울기 점수 (낮을수록 좋음)
        skew_score = 1.0 - min(abs(metrics.skew_angle) / self.MAX_SKEW_ANGLE, 1.0)
        scores.append(skew_score)
        weights.append(0.1)
        
        # 밝기 점수
        brightness_min, brightness_max = self.OPTIMAL_BRIGHTNESS_RANGE
        if brightness_min <= metrics.brightness <= brightness_max:
            brightness_score = 1.0
        else:
            brightness_score = 1.0 - min(
                abs(metrics.brightness - (brightness_min + brightness_max) / 2) / 0.5, 1.0
            )
        scores.append(brightness_score)
        weights.append(0.1)
        
        # 가중평균 계산
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        total_weight = sum(weights)
        
        return weighted_sum / total_weight


class AdaptivePreprocessor:
    """적응형 전처리기"""
    
    def __init__(self):
        self.assessor = ScientificImageAssessor()
        self.logger = logger
    
    def create_preprocessing_plan(self, metrics: QualityMetrics) -> PreprocessingPlan:
        """
        품질 평가 결과를 바탕으로 전처리 계획 수립
        
        Args:
            metrics: 이미지 품질 평가 결과
            
        Returns:
            PreprocessingPlan: 전처리 계획
        """
        actions = []
        parameters = {}
        rationale_parts = []
        
        # DPI 기반 리사이징 결정
        if metrics.dpi_estimate < ScientificImageAssessor.OPTIMAL_DPI_MIN:
            scale_factor = ScientificImageAssessor.OPTIMAL_DPI_MIN / metrics.dpi_estimate
            actions.append(PreprocessingAction.RESIZE)
            parameters['resize_scale'] = scale_factor
            rationale_parts.append(f"낮은 DPI({metrics.dpi_estimate:.1f}) 보정")
        
        # 기울기 보정 결정
        if abs(metrics.skew_angle) > ScientificImageAssessor.MAX_SKEW_ANGLE:
            actions.append(PreprocessingAction.DESKEW)
            parameters['skew_angle'] = metrics.skew_angle
            rationale_parts.append(f"기울기({metrics.skew_angle:.1f}°) 보정")
        
        # 노이즈 제거 결정 
        if metrics.noise_level > ScientificImageAssessor.MAX_NOISE_LEVEL:
            actions.append(PreprocessingAction.DENOISE)
            parameters['denoise_strength'] = min(metrics.noise_level * 2, 1.0)
            rationale_parts.append(f"노이즈({metrics.noise_level:.3f}) 제거")
        
        # 대비 향상 결정
        if metrics.contrast < ScientificImageAssessor.MIN_CONTRAST:
            actions.append(PreprocessingAction.ENHANCE_CONTRAST)
            parameters['contrast_enhancement'] = ScientificImageAssessor.MIN_CONTRAST / metrics.contrast
            rationale_parts.append(f"낮은 대비({metrics.contrast:.3f}) 향상")
        
        # 선명도 향상 결정
        if metrics.sharpness < ScientificImageAssessor.MIN_SHARPNESS:
            actions.append(PreprocessingAction.SHARPEN)
            parameters['sharpen_strength'] = ScientificImageAssessor.MIN_SHARPNESS / metrics.sharpness
            rationale_parts.append(f"선명도({metrics.sharpness:.3f}) 향상")
        
        # 밝기 정규화 결정
        brightness_min, brightness_max = ScientificImageAssessor.OPTIMAL_BRIGHTNESS_RANGE
        if not (brightness_min <= metrics.brightness <= brightness_max):
            actions.append(PreprocessingAction.NORMALIZE)
            parameters['target_brightness'] = (brightness_min + brightness_max) / 2
            rationale_parts.append(f"밝기({metrics.brightness:.3f}) 정규화")
        
        # 최종 이진화 (고품질인 경우에만)
        if metrics.overall_quality > 0.7:
            actions.append(PreprocessingAction.BINARIZE)
            parameters['binarize_method'] = 'adaptive'
            rationale_parts.append("고품질 이미지 이진화")
        
        # 신뢰도 계산
        confidence = min(metrics.overall_quality + 0.1, 1.0)
        
        # 근거 문구 생성
        rationale = "필요 없음" if not rationale_parts else ", ".join(rationale_parts)
        
        plan = PreprocessingPlan(
            actions=actions,
            parameters=parameters,
            confidence=confidence,
            rationale=rationale
        )
        
        self.logger.info(f"📋 전처리 계획: {len(actions)}개 액션")
        self.logger.info(f"   근거: {rationale}")
        self.logger.info(f"   신뢰도: {confidence:.3f}")
        
        return plan
    
    def execute_preprocessing_plan(self, image: np.ndarray, plan: PreprocessingPlan) -> np.ndarray:
        """
        전처리 계획을 실행
        
        Args:
            image: 입력 이미지
            plan: 전처리 계획
            
        Returns:
            np.ndarray: 전처리된 이미지
        """
        result = image.copy()
        
        # 그레이스케일 변환
        if len(result.shape) == 3:
            result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        
        self.logger.info(f"🎯 전처리 실행 시작: {len(plan.actions)}개 액션")
        
        for i, action in enumerate(plan.actions):
            self.logger.info(f"   {i+1}/{len(plan.actions)}: {action.value}")
            
            if action == PreprocessingAction.RESIZE:
                scale = plan.parameters.get('resize_scale', 1.0)
                h, w = result.shape
                new_h, new_w = int(h * scale), int(w * scale)
                result = cv2.resize(result, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
                
            elif action == PreprocessingAction.DESKEW:
                angle = plan.parameters.get('skew_angle', 0)
                result = self._deskew_image(result, angle)
                
            elif action == PreprocessingAction.DENOISE:
                strength = plan.parameters.get('denoise_strength', 0.5)
                kernel_size = max(3, int(5 * strength))
                if kernel_size % 2 == 0:
                    kernel_size += 1
                result = cv2.medianBlur(result, kernel_size)
                
            elif action == PreprocessingAction.ENHANCE_CONTRAST:
                enhancement = plan.parameters.get('contrast_enhancement', 1.5)
                clahe = cv2.createCLAHE(clipLimit=enhancement * 2.0, tileGridSize=(8, 8))
                result = clahe.apply(result)
                
            elif action == PreprocessingAction.SHARPEN:
                strength = plan.parameters.get('sharpen_strength', 1.5)
                result = self._sharpen_image(result, strength)
                
            elif action == PreprocessingAction.NORMALIZE:
                target = plan.parameters.get('target_brightness', 0.5)
                result = self._normalize_brightness(result, target)
                
            elif action == PreprocessingAction.BINARIZE:
                method = plan.parameters.get('binarize_method', 'adaptive')
                if method == 'adaptive':
                    result = cv2.adaptiveThreshold(
                        result, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                        cv2.THRESH_BINARY, 21, 10
                    )
                else:
                    _, result = cv2.threshold(result, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        self.logger.info(f"✅ 전처리 실행 완료 (신뢰도: {plan.confidence:.3f})")
        return result
    
    def _deskew_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """이미지 기울기 보정"""
        h, w = image.shape
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, rotation_matrix, (w, h), 
                             flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    def _sharpen_image(self, image: np.ndarray, strength: float) -> np.ndarray:
        """이미지 선명화 (Unsharp masking)"""
        blurred = cv2.GaussianBlur(image, (5, 5), 1.5)
        return cv2.addWeighted(image, 1 + strength, blurred, -strength, 0)
    
    def _normalize_brightness(self, image: np.ndarray, target: float) -> np.ndarray:
        """밝기 정규화"""
        current_brightness = np.mean(image) / 255.0
        adjustment = target / current_brightness
        
        result = image.astype(np.float32) * adjustment
        return np.clip(result, 0, 255).astype(np.uint8)


def smart_preprocess_image(image: np.ndarray) -> Tuple[np.ndarray, QualityMetrics, PreprocessingPlan]:
    """
    과학적 방법으로 이미지를 분석하고 최적의 전처리를 적용
    
    Args:
        image: 입력 이미지 (BGR 또는 Grayscale)
        
    Returns:
        Tuple[np.ndarray, QualityMetrics, PreprocessingPlan]: 
        (전처리된 이미지, 품질 평가 결과, 전처리 계획)
    """
    # 1. 이미지 품질 평가
    assessor = ScientificImageAssessor()
    metrics = assessor.assess_image(image)
    
    # 2. 전처리 계획 수립
    preprocessor = AdaptivePreprocessor() 
    plan = preprocessor.create_preprocessing_plan(metrics)
    
    # 3. 전처리 실행
    processed_image = preprocessor.execute_preprocessing_plan(image, plan)
    
    return processed_image, metrics, plan