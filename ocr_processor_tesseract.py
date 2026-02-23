"""
OCR (Optical Character Recognition) 기능을 제공하는 모듈
pytesseract를 사용하여 이미지에서 텍스트를 추출합니다.
"""

import pytesseract
from PIL import Image
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self):
        """OCR 프로세서 초기화"""
        # Windows에서 Tesseract 경로 설정
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        logger.info("Tesseract OCR 경로 설정 완료")
    
    def extract_text_from_image(self, image_path):
        """
        이미지 파일에서 텍스트를 추출합니다.
        
        Args:
            image_path (str): 이미지 파일 경로
            
        Returns:
            str: 추출된 텍스트
        """
        try:
            logger.info(f"이미지에서 텍스트 추출 시작: {image_path}")
            
            # PIL로 이미지 열기
            image = Image.open(image_path)
            
            # OCR 실행 (한국어와 영어)
            custom_config = r'--oem 3 --psm 6 -l kor+eng'
            text = pytesseract.image_to_string(image, config=custom_config)
            
            logger.info(f"OCR 완료: {len(text)} 글자 추출")
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR 처리 중 오류: {str(e)}")
            raise
    
    def extract_text_from_pil_image(self, pil_image):
        """
        PIL Image 객체에서 텍스트를 추출합니다.
        
        Args:
            pil_image: PIL Image 객체
            
        Returns:
            str: 추출된 텍스트
        """
        try:
            logger.info("PIL 이미지에서 텍스트 추출 시작")
            
            # OpenCV 형식으로 변환하여 전처리
            image_array = np.array(pil_image)
            if len(image_array.shape) == 3:
                # RGB를 BGR로 변환 (OpenCV 형식)
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            
            # 이미지 전처리
            processed_image = self._preprocess_image(image_array)
            
            # 전처리된 이미지를 PIL로 다시 변환
            if len(processed_image.shape) == 2:  # 그레이스케일
                processed_pil = Image.fromarray(processed_image, mode='L')
            else:
                processed_pil = Image.fromarray(cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB))
            
            # OCR 실행
            custom_config = r'--oem 3 --psm 6 -l kor+eng'
            text = pytesseract.image_to_string(processed_pil, config=custom_config)
            
            logger.info(f"OCR 완료: {len(text)} 글자 추출")
            return text.strip()
            
        except Exception as e:
            logger.error(f"PIL 이미지 OCR 처리 중 오류: {str(e)}")
            return f"OCR 처리 중 오류가 발생했습니다: {str(e)}"
    
    def _preprocess_image(self, image):
        """
        OCR 정확도 향상을 위한 이미지 전처리
        
        Args:
            image: OpenCV 이미지 (BGR 형식)
            
        Returns:
            numpy.ndarray: 전처리된 이미지
        """
        # 그레이스케일 변환
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 이미지 크기 조정 (너무 작으면 확대)
        height, width = gray.shape
        if height < 300 or width < 300:
            scale_factor = max(300/height, 300/width)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # 가우시안 블러로 노이즈 제거
        blurred = cv2.GaussianBlur(gray, (1, 1), 0)
        
        # 대비 개선 (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(blurred)
        
        # Otsu 이진화
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 모폴로지 연산으로 문자 개선
        kernel = np.ones((2, 2), np.uint8)
        
        # Opening 연산 (erosion 후 dilation)
        try:
            opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
        except AttributeError:
            # OpenCV 버전이 낮은 경우 수동으로 opening 연산 수행
            eroded = cv2.erode(binary, kernel, iterations=1)
            opening = cv2.dilate(eroded, kernel, iterations=1)
        
        # 배경이 어둡고 텍스트가 밝은 경우 반전
        if np.mean(opening) < 127:
            opening = cv2.bitwise_not(opening)
        
        return opening