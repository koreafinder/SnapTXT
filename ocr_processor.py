"""
간단한 EasyOCR 프로세서
"""

import easyocr
import numpy as np
import cv2
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    간단한 EasyOCR 클래스
    """
    
    def __init__(self):
        """OCR 리더 초기화"""
        try:
            logger.info("EasyOCR 초기화 중...")
            self.reader = easyocr.Reader(['ko', 'en'], gpu=False)
            logger.info("EasyOCR 초기화 완료")
        except Exception as e:
            logger.error(f"EasyOCR 초기화 실패: {e}")
            self.reader = None

    def extract_text_from_pil_image(self, pil_image):
        """PIL Image에서 텍스트 추출"""
        if not self.reader:
            return "OCR 초기화 실패"
        
        try:
            # PIL을 numpy 배열로 변환
            image_array = np.array(pil_image)
            
            # BGR 변환
            if len(image_array.shape) == 3:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            
            # OCR 실행
            results = self.reader.readtext(image_array)
            
            # 텍스트만 추출
            texts = []
            for (bbox, text, confidence) in results:
                if confidence > 0.3:
                    texts.append(text)
            
            return '\n'.join(texts) if texts else "텍스트를 찾을 수 없습니다."
            
        except Exception as e:
            logger.error(f"OCR 처리 오류: {e}")
            return f"OCR 오류: {str(e)}"
    
    def extract_text_from_path(self, image_path):
        """파일 경로에서 텍스트 추출"""
        try:
            pil_image = Image.open(image_path)
            return self.extract_text_from_pil_image(pil_image)
        except Exception as e:
            return f"파일 읽기 오류: {str(e)}"