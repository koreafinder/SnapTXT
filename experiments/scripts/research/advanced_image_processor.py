#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Image Preprocessor for Korean OCR
한국어 OCR을 위한 고급 이미지 전처리 모듈
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from typing import Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)

class AdvancedImageProcessor:
    """한국어 OCR을 위한 고급 이미지 전처리기"""
    
    def __init__(self):
        """초기화"""
        self.processing_history = []
    
    def preprocess_for_korean_ocr(self, image: np.ndarray, options: Dict = None) -> Dict:
        """
        한국어 OCR을 위한 종합 이미지 전처리
        
        Args:
            image: 입력 이미지 (numpy array)
            options: 전처리 옵션
            
        Returns:
            Dict: 전처리된 이미지들과 메타데이터
        """
        default_options = {
            'denoise': True,
            'enhance_contrast': True,
            'sharpen': True,
            'adaptive_threshold': True,
            'deskew': True,
            'upscale': False,
            'target_dpi': 300
        }
        
        if options:
            default_options.update(options)
        
        try:
            # 원본 이미지 정보
            original_shape = image.shape
            
            # 처리 단계별 이미지 저장
            processed_images = {
                'original': image.copy()
            }
            
            current_image = image.copy()
            
            # 1. 이미지 크기 조정 (필요시)
            if default_options['upscale']:
                current_image = self._upscale_image(current_image, target_dpi=default_options['target_dpi'])
                processed_images['upscaled'] = current_image.copy()
                logger.info("이미지 업스케일 완료")
            
            # 2. 노이즈 제거
            if default_options['denoise']:
                current_image = self._advanced_denoise(current_image)
                processed_images['denoised'] = current_image.copy()
                logger.info("노이즈 제거 완료")
            
            # 3. 기울기 보정 (deskewing)
            if default_options['deskew']:
                current_image = self._deskew_image(current_image)
                processed_images['deskewed'] = current_image.copy()
                logger.info("기울기 보정 완료")
            
            # 4. 대비 강화
            if default_options['enhance_contrast']:
                current_image = self._enhance_contrast_adaptive(current_image)
                processed_images['contrast_enhanced'] = current_image.copy()
                logger.info("대비 강화 완료")
            
            # 5. 선명도 강화
            if default_options['sharpen']:
                current_image = self._sharpen_text(current_image)
                processed_images['sharpened'] = current_image.copy()
                logger.info("선명도 강화 완료")
            
            # 6. 적응적 이진화
            if default_options['adaptive_threshold']:
                binary_image = self._adaptive_threshold(current_image)
                processed_images['binary'] = binary_image
                current_image = binary_image
                logger.info("적응적 이진화 완료")
            
            # 7. 최종 정리
            final_image = self._final_cleanup(current_image)
            processed_images['final'] = final_image
            
            # 품질 평가
            quality_score = self._evaluate_image_quality(final_image)
            
            result = {
                'success': True,
                'processed_image': final_image,
                'all_stages': processed_images,
                'quality_score': quality_score,
                'original_shape': original_shape,
                'final_shape': final_image.shape,
                'processing_options': default_options
            }
            
            # 처리 기록 저장
            self.processing_history.append({
                'original_shape': original_shape,
                'final_shape': final_image.shape,
                'quality_score': quality_score,
                'options': default_options.copy()
            })
            
            return result
            
        except Exception as e:
            logger.error(f"이미지 전처리 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_image': image,
                'quality_score': 0.0
            }
    
    def _upscale_image(self, image: np.ndarray, target_dpi: int = 300) -> np.ndarray:
        """이미지 해상도 향상"""
        height, width = image.shape[:2]
        
        # DPI 기반 스케일링 (가정: 원본 72 DPI)
        scale_factor = target_dpi / 72.0
        
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        
        # 고품질 보간법 사용
        upscaled = cv2.resize(image, (new_width, new_height), 
                             interpolation=cv2.INTER_CUBIC)
        
        return upscaled
    
    def _advanced_denoise(self, image: np.ndarray) -> np.ndarray:
        """고급 노이즈 제거"""
        if len(image.shape) == 3:
            # 컬러 이미지
            denoised = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
        else:
            # 그레이스케일 이미지
            denoised = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
        
        # 추가적인 가우시안 블러로 미세 노이즈 제거
        denoised = cv2.GaussianBlur(denoised, (3, 3), 0.5)
        
        return denoised
    
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """기울기 보정"""
        try:
            # 그레이스케일 변환
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # 이진화
            binary = cv2.adaptiveThreshold(gray, 255, 
                                         cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY, 11, 2)
            
            # 허프 변환으로 직선 검출
            edges = cv2.Canny(binary, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                # 각도 계산
                angles = []
                for rho, theta in lines[:, 0]:
                    angle = theta * 180 / np.pi
                    if angle < 45:
                        angles.append(angle)
                    elif angle > 135:
                        angles.append(angle - 180)
                
                if angles:
                    # 중앙값 각도로 회전
                    median_angle = np.median(angles)
                    if abs(median_angle) > 0.5:  # 0.5도 이상만 보정
                        return self._rotate_image(image, -median_angle)
            
            return image
            
        except Exception as e:
            logger.warning(f"기울기 보정 실패: {e}")
            return image
    
    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """이미지 회전"""
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        
        # 회전 변환 행렬
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # 새로운 경계 계산
        cos = abs(M[0, 0])
        sin = abs(M[0, 1])
        new_width = int((height * sin) + (width * cos))
        new_height = int((height * cos) + (width * sin))
        
        # 변환 행렬 조정
        M[0, 2] += (new_width / 2) - center[0]
        M[1, 2] += (new_height / 2) - center[1]
        
        # 회전 적용
        rotated = cv2.warpAffine(image, M, (new_width, new_height), 
                                flags=cv2.INTER_CUBIC, 
                                borderMode=cv2.BORDER_CONSTANT, 
                                borderValue=(255, 255, 255))
        
        return rotated
    
    def _enhance_contrast_adaptive(self, image: np.ndarray) -> np.ndarray:
        """적응적 대비 강화"""
        if len(image.shape) == 3:
            # 컬러 이미지: LAB 색공간에서 L 채널만 처리
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel = lab[:, :, 0]
            
            # CLAHE 적용 (제한된 적응 히스토그램 평활화)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced_l = clahe.apply(l_channel)
            
            # LAB 재조합
            lab[:, :, 0] = enhanced_l
            enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            # 그레이스케일: 직접 CLAHE 적용
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(image)
        
        return enhanced
    
    def _sharpen_text(self, image: np.ndarray) -> np.ndarray:
        """텍스트 특화 선명도 강화"""
        # 언샵 마스킹 커널
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        
        sharpened = cv2.filter2D(image, -1, kernel)
        
        # 원본과 블렌딩으로 과도한 선명화 방지
        blended = cv2.addWeighted(image, 0.7, sharpened, 0.3, 0)
        
        return blended
    
    def _adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """적응적 임계값 이진화"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Otsu + 가우시안 적응 임계값 조합
        # 1. Otsu 임계값 계산
        _, otsu_binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 2. 가우시안 적응 임계값
        adaptive_binary = cv2.adaptiveThreshold(gray, 255,
                                              cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                              cv2.THRESH_BINARY, 11, 2)
        
        # 3. 두 결과의 교집합 (더 보수적인 이진화)
        combined_binary = cv2.bitwise_and(otsu_binary, adaptive_binary)
        
        return combined_binary
    
    def _final_cleanup(self, image: np.ndarray) -> np.ndarray:
        """최종 정리"""
        # 작은 노이즈 제거 (모폴로지 연산)
        if len(image.shape) == 2:  # 이진 이미지
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            # Opening: 작은 노이즈 제거
            cleaned = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
            # Closing: 작은 구멍 메우기
            cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
        else:
            cleaned = image
        
        return cleaned
    
    def _evaluate_image_quality(self, image: np.ndarray) -> float:
        """이미지 품질 평가 (0.0 ~ 1.0)"""
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # 1. 선명도 평가 (라플라시안 분산)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness_score = min(1.0, laplacian_var / 1000.0)  # 정규화
            
            # 2. 대비 평가
            contrast = gray.std() / 255.0
            
            # 3. 밝기 평가 (너무 어둡거나 밝지 않은지)
            brightness = gray.mean() / 255.0
            brightness_score = 1.0 - abs(brightness - 0.5) * 2
            
            # 종합 점수 계산
            quality_score = (sharpness_score * 0.4 + 
                           contrast * 0.4 + 
                           brightness_score * 0.2)
            
            return min(1.0, max(0.0, quality_score))
            
        except Exception:
            return 0.5  # 기본값
    
    def get_processing_stats(self) -> Dict:
        """처리 통계 반환"""
        if not self.processing_history:
            return {'total_processed': 0}
        
        total = len(self.processing_history)
        avg_quality = sum(h['quality_score'] for h in self.processing_history) / total
        high_quality_count = sum(1 for h in self.processing_history if h['quality_score'] >= 0.7)
        
        return {
            'total_processed': total,
            'average_quality_score': round(avg_quality, 3),
            'high_quality_percentage': round((high_quality_count / total) * 100, 1),
            'recent_quality': [h['quality_score'] for h in self.processing_history[-10:]]
        }
    
    def save_processing_stages(self, result: Dict, output_dir: str):
        """처리 단계별 이미지 저장 (디버깅용)"""
        if not result['success']:
            return
        
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        for stage_name, stage_image in result['all_stages'].items():
            output_path = os.path.join(output_dir, f"{stage_name}.png")
            cv2.imwrite(output_path, stage_image)
        
        logger.info(f"처리 단계 이미지들이 {output_dir}에 저장되었습니다.")

# 테스트 실행
if __name__ == "__main__":
    # 간단한 테스트
    processor = AdvancedImageProcessor()
    
    # 더미 이미지 생성
    test_image = np.ones((200, 400, 3), dtype=np.uint8) * 128
    cv2.putText(test_image, "Test Korean OCR", (50, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    result = processor.preprocess_for_korean_ocr(test_image)
    
    print(f"처리 성공: {result['success']}")
    print(f"품질 점수: {result['quality_score']:.3f}")
    print(f"원본 크기: {result['original_shape']}")
    print(f"최종 크기: {result['final_shape']}")
    
    stats = processor.get_processing_stats()
    print(f"처리 통계: {stats}")