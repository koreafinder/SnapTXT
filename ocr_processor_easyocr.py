"""
EasyOCR을 사용한 OCR 프로세서
한국어와 영어 텍스트 인식에 특화된 OCR 처리기
"""

import easyocr
import numpy as np
import cv2
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    EasyOCR을 사용한 텍스트 추출 클래스
    """
    
    def __init__(self):
        """OCR 리더 초기화"""
        try:
            # 한국어와 영어 지원 EasyOCR 리더 생성
            self.reader = easyocr.Reader(['ko', 'en'], gpu=False)
            logger.info("EasyOCR 리더 초기화 완료 (한국어, 영어 지원)")
        except Exception as e:
            logger.error(f"EasyOCR 초기화 실패: {e}")
            self.reader = None

    def extract_text_from_pil_image(self, pil_image):
        """
        PIL Image에서 텍스트 추출
        
        Args:
            pil_image: PIL Image 객체
            
        Returns:
            str: 추출된 텍스트
        """
        if not self.reader:
            return "OCR 리더가 초기화되지 않았습니다."
        
        try:
            # PIL Image를 numpy 배열로 변환
            image_array = np.array(pil_image)
            
            # RGB에서 BGR로 변환 (OpenCV 형식)
            if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            
            # EasyOCR로 텍스트 추출
            results = self.reader.readtext(image_array)
            
            # 결과에서 텍스트만 추출
            extracted_texts = []
            for (bbox, text, confidence) in results:
                # 신뢰도가 0.3 이상인 텍스트만 포함
                if confidence > 0.3:
                    extracted_texts.append(text)
                    logger.info(f"추출된 텍스트: {text} (신뢰도: {confidence:.2f})")
            
            # 텍스트들을 줄바꿈으로 구분하여 합치기
            final_text = '\n'.join(extracted_texts)
            
            return final_text if final_text else "텍스트를 찾을 수 없습니다."
            
        except Exception as e:
            logger.error(f"EasyOCR 텍스트 추출 중 오류: {e}")
            return f"OCR 처리 중 오류가 발생했습니다: {str(e)}"
    
    def extract_text_from_path(self, image_path):
        """
        이미지 파일 경로에서 텍스트 추출
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            str: 추출된 텍스트
        """
        try:
            # PIL로 이미지 열기
            pil_image = Image.open(image_path)
            return self.extract_text_from_pil_image(pil_image)
        except Exception as e:
            logger.error(f"이미지 파일 읽기 오류: {e}")
            return f"이미지 파일을 읽을 수 없습니다: {str(e)}"