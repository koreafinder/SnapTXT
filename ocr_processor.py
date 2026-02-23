"""
고성능 EasyOCR 프로세서 - GPU 가속, 이미지 전처리, 좌표 기반 정렬
"""

import easyocr
import numpy as np
import cv2
from PIL import Image, ImageEnhance
import logging
import torch
from typing import List, Tuple

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    고성능 EasyOCR 클래스 - GPU 가속, 전처리, 정렬 알고리즘 포함
    """
    
    def __init__(self):
        """OCR 리더 초기화 (GPU 자동 감지)"""
        try:
            logger.info("EasyOCR 초기화 중...")
            
            # GPU 사용 가능성 자동 감지
            self.use_gpu = torch.cuda.is_available()
            if self.use_gpu:
                logger.info("GPU 가속 활성화")
            else:
                logger.info("CPU 모드로 실행")
            
            self.reader = easyocr.Reader(['ko', 'en'], gpu=self.use_gpu)
            logger.info(f"EasyOCR 초기화 완료 (GPU: {self.use_gpu})")
        except Exception as e:
            logger.error(f"EasyOCR 초기화 실패: {e}")
            self.reader = None
            self.use_gpu = False

    def preprocess_image(self, pil_image: Image.Image) -> np.ndarray:
        """이미지 전처리 - 대비/밝기 조정, 노이즈 제거, 해상도 최적화"""
        try:
            # 원본 크기 저장
            original_width, original_height = pil_image.size
            
            # 1. 해상도 최적화 (너무 작으면 확대, 너무 크면 축소)
            if original_width < 800 or original_height < 600:
                # 작은 이미지는 2배 확대
                new_size = (original_width * 2, original_height * 2)
                pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"이미지 확대: {original_width}x{original_height} → {new_size[0]}x{new_size[1]}")
            elif original_width > 3000 or original_height > 3000:
                # 큰 이미지는 적절히 축소
                scale = min(3000/original_width, 3000/original_height)
                new_size = (int(original_width * scale), int(original_height * scale))
                pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"이미지 축소: {original_width}x{original_height} → {new_size[0]}x{new_size[1]}")
            
            # 2. 대비와 선명도 향상
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(1.2)  # 대비 20% 증가
            
            enhancer = ImageEnhance.Sharpness(pil_image)
            pil_image = enhancer.enhance(1.1)  # 선명도 10% 증가
            
            # 3. numpy 배열로 변환
            image_array = np.array(pil_image)
            
            # 4. BGR 변환 (OpenCV 형식)
            if len(image_array.shape) == 3:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            
            # 5. 노이즈 제거 (가우시안 블러 적용)
            image_array = cv2.GaussianBlur(image_array, (1, 1), 0)
            
            logger.info("이미지 전처리 완료")
            return image_array
            
        except Exception as e:
            logger.warning(f"이미지 전처리 실패, 원본 사용: {e}")
            # 전처리 실패 시 원본 사용
            image_array = np.array(pil_image)
            if len(image_array.shape) == 3:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            return image_array
    
    def sort_text_by_coordinates(self, results: List) -> List[Tuple[str, float]]:
        """좌표 기반 텍스트 정렬 - 위에서 아래로, 왼쪽에서 오른쪽으로 (안전한 언패킹)"""
        try:
            # 신뢰도가 높은 결과만 필터링 (안전한 언패킹)
            high_confidence_results = []
            for result in results:
                try:
                    # EasyOCR 결과 형식 확인 및 안전한 언패킹
                    if len(result) == 3:
                        bbox, text, confidence = result
                    elif len(result) == 2:
                        # 때로는 confidence가 없는 경우
                        bbox, text = result
                        confidence = 1.0  # 기본값 설정
                    else:
                        logger.warning(f"예상하지 못한 결과 형식: {result}")
                        continue
                    
                    if confidence >= 0.7:  # 신뢰도 임계값 상향 조정
                        high_confidence_results.append((bbox, text, confidence))
                except Exception as e:
                    logger.warning(f"결과 언패킹 오류 (건너뜀): {e}")
                    continue
            
            if not high_confidence_results:
                logger.warning("높은 신뢰도 텍스트 없음, 임계값을 0.5로 낮춤")
                # 임계값을 낮춰서 재시도
                for result in results:
                    try:
                        if len(result) == 3:
                            bbox, text, confidence = result
                        elif len(result) == 2:
                            bbox, text = result
                            confidence = 1.0
                        else:
                            continue
                        
                        if confidence >= 0.5:
                            high_confidence_results.append((bbox, text, confidence))
                    except Exception:
                        continue
            
            if not high_confidence_results:
                logger.warning("임계값 0.5에서도 텍스트 없음, 0.3으로 최종 시도")
                # 최종적으로 0.3으로 시도
                for result in results:
                    try:
                        if len(result) == 3:
                            bbox, text, confidence = result
                        elif len(result) == 2:
                            bbox, text = result
                            confidence = 1.0
                        else:
                            continue
                        
                        if confidence >= 0.3:
                            high_confidence_results.append((bbox, text, confidence))
                    except Exception:
                        continue
            
            # 좌표 기반 정렬 (Y축 우선, 그 다음 X축)
            def get_sort_key(item):
                try:
                    bbox, text, confidence = item
                    # bbox는 [[x1,y1], [x2,y1], [x2,y2], [x1,y2]] 형태
                    if isinstance(bbox, list) and len(bbox) > 0:
                        top_left = bbox[0]
                        if isinstance(top_left, list) and len(top_left) >= 2:
                            x, y = float(top_left[0]), float(top_left[1])
                        else:
                            x, y = 0, 0
                    else:
                        x, y = 0, 0
                    # Y축을 20픽셀 단위로 묶어서 같은 줄로 인식
                    line_group = int(y // 20) * 20
                    return (line_group, x)
                except Exception:
                    return (0, 0)
            
            sorted_results = sorted(high_confidence_results, key=get_sort_key)
            
            # 텍스트와 신뢰도만 반환
            text_confidence_pairs = []
            for bbox, text, confidence in sorted_results:
                if isinstance(text, str) and text.strip():
                    text_confidence_pairs.append((text.strip(), confidence))
            
            logger.info(f"정렬된 텍스트 {len(text_confidence_pairs)}개 (평균 신뢰도: {np.mean([conf for _, conf in text_confidence_pairs]):.3f if text_confidence_pairs else 0})")
            return text_confidence_pairs
            
        except Exception as e:
            logger.error(f"텍스트 정렬 오류: {e}")
            # 정렬 실패 시 기본 필터링만 적용
            simple_results = []
            for result in results:
                try:
                    if len(result) >= 2:
                        if len(result) == 3:
                            bbox, text, confidence = result
                        else:
                            bbox, text = result
                            confidence = 1.0
                        
                        if isinstance(text, str) and text.strip() and confidence >= 0.3:
                            simple_results.append((text.strip(), confidence))
                except Exception:
                    continue
            return simple_results
    
    def format_text_output(self, text_confidence_pairs: List[Tuple[str, float]]) -> str:
        """텍스트 출력 형식 최적화 - 단락 구분 및 줄바꿈 처리 (안전한 처리)"""
        if not text_confidence_pairs:
            return "텍스트를 찾을 수 없습니다."
        
        try:
            formatted_lines = []
            current_line = ""
            
            for item in text_confidence_pairs:
                try:
                    # 안전한 언패킹
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        text, confidence = item[0], item[1]
                    elif isinstance(item, (list, tuple)) and len(item) == 1:
                        text, confidence = item[0], 1.0
                    elif isinstance(item, str):
                        text, confidence = item, 1.0
                    else:
                        continue
                    
                    # 텍스트 검증
                    if not isinstance(text, str) or not text.strip():
                        continue
                    
                    text = text.strip()
                    
                    # 매우 짧은 텍스트는 이전 줄에 연결
                    if len(text) <= 2 and current_line:
                        current_line += text
                    # 새로운 줄 시작
                    elif current_line and not current_line.endswith((' ', '-')):
                        # 현재 줄이 완전하면 저장하고 새 줄 시작
                        formatted_lines.append(current_line.strip())
                        current_line = text
                    else:
                        # 기존 줄에 연결
                        current_line += (" " if current_line and not text.startswith((' ', '-')) else "") + text
                    
                    # 줄이 너무 길면 강제로 나누기
                    if len(current_line) > 100:
                        formatted_lines.append(current_line.strip())
                        current_line = ""
                        
                except Exception as e:
                    logger.warning(f"텍스트 항목 처리 오류 (건너뜀): {e}")
                    continue
            
            # 마지막 줄 추가
            if current_line.strip():
                formatted_lines.append(current_line.strip())
            
            # 빈 줄 제거 및 최종 포맷팅
            final_text = '\n'.join([line for line in formatted_lines if line.strip()])
            
            if not final_text.strip():
                return "텍스트 처리 중 오류가 발생했습니다."
            
            logger.info(f"최종 텍스트 형식화 완료: {len(formatted_lines)}줄")
            return final_text
            
        except Exception as e:
            logger.error(f"텍스트 형식화 오류: {e}")
            # 형식화 실패 시 단순 연결
            try:
                simple_texts = []
                for item in text_confidence_pairs:
                    if isinstance(item, (list, tuple)) and len(item) >= 1:
                        text = item[0] if isinstance(item[0], str) else str(item[0])
                        if text.strip():
                            simple_texts.append(text.strip())
                    elif isinstance(item, str) and item.strip():
                        simple_texts.append(item.strip())
                
                return '\n'.join(simple_texts) if simple_texts else "텍스트를 처리할 수 없습니다."
            except Exception:
                return "텍스트 처리 중 심각한 오류가 발생했습니다."
    
    def extract_text_from_pil_image(self, pil_image):
        """PIL Image에서 고성능 텍스트 추출 (전처리 + 정렬 + 형식화) - 안전한 처리"""
        if not self.reader:
            return "OCR 초기화 실패"
        
        try:
            logger.info("고성능 OCR 처리 시작")
            
            # 1. 이미지 전처리
            processed_image = self.preprocess_image(pil_image)
            
            # 2. EasyOCR 실행 (안전한 옵션 적용)
            try:
                results = self.reader.readtext(
                    processed_image,
                    width_ths=0.7,      # 텍스트 폭 임계값
                    height_ths=0.7,     # 텍스트 높이 임계값
                    mag_ratio=1.5,      # 확대 비율
                    slope_ths=0.1,      # 기울기 임계값
                    ycenter_ths=0.5,    # Y축 중심 임계값
                    x_ths=1.0,          # X축 임계값
                    y_ths=0.5,          # Y축 임계값
                    text_threshold=0.7, # 텍스트 신뢰도
                    low_text=0.4,       # 낮은 신뢰도 텍스트
                    link_threshold=0.4, # 링크 임계값
                    canvas_size=2560,   # 캔버스 크기
                    paragraph=True      # 단락 단위 인식
                )
            except Exception as advanced_error:
                logger.warning(f"고급 옵션 OCR 실패, 기본 옵션으로 재시도: {advanced_error}")
                # 고급 옵션 실패 시 기본 옵션으로 재시도
                try:
                    results = self.reader.readtext(processed_image)
                except Exception as basic_error:
                    logger.error(f"기본 OCR도 실패: {basic_error}")
                    return f"OCR 처리 실패: {basic_error}"
            
            logger.info(f"OCR 결과 수신: {len(results) if results else 0}개 항목")
            
            if not results:
                logger.warning("OCR 결과 없음")
                return "이미지에서 텍스트를 찾을 수 없습니다. 이미지가 선명하고 텍스트가 포함되어 있는지 확인해주세요."
            
            # 3. 결과 검증 및 로깅
            valid_results = []
            for i, result in enumerate(results):
                try:
                    if isinstance(result, (list, tuple)) and len(result) >= 2:
                        valid_results.append(result)
                    else:
                        logger.warning(f"유효하지 않은 결과 형식 (인덱스 {i}): {type(result)} - {result}")
                except Exception as e:
                    logger.warning(f"결과 검증 오류 (인덱스 {i}): {e}")
            
            if not valid_results:
                return "OCR 결과를 처리할 수 없습니다. 이미지 품질을 확인해주세요."
            
            logger.info(f"유효한 OCR 결과: {len(valid_results)}개")
            
            # 4. 좌표 기반 정렬
            text_confidence_pairs = self.sort_text_by_coordinates(valid_results)
            
            if not text_confidence_pairs:
                return "설정된 신뢰도 임계값을 만족하는 텍스트가 없습니다. 이미지 품질을 확인해주세요."
            
            # 5. 텍스트 형식화
            final_text = self.format_text_output(text_confidence_pairs)
            
            logger.info(f"OCR 처리 완료: {len(text_confidence_pairs)}개 텍스트 추출")
            return final_text
            
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