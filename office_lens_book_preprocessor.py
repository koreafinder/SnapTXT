# Office Lens 책 촬영 이미지 전용 전처리 시스템
# Parameter-Based Presets for Scanned Book Images

import cv2
import numpy as np
import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class PreprocessParams:
    """전처리 파라미터 설정"""
    name: str
    scale: float = 1.0                    # 업스케일 배율
    median_blur: int = 0                  # 3, 5, 또는 0(비활성)
    threshold_method: str = "adaptive"    # "otsu" 또는 "adaptive" 
    adaptive_block_size: int = 25         # 홀수만 (25~71)
    adaptive_C: int = 8                   # C값 (3~20)
    morph_operation: str = "none"         # "open", "close", "none"
    morph_kernel_size: int = 0            # 2, 3, 또는 0(비활성)
    sharpening: float = 0.0               # 0.0~1.0 (0=비활성)
    
class OfficeLensBookPreprocessor:
    """
    Office Lens + 책 촬영에 특화된 전처리 시스템
    - 3가지 프리셋 (Clean/Shadow/Thin)
    - 파라미터 기반 튜닝
    - 자동 품질 평가 및 선택
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.presets = self._initialize_presets()
        
    def _initialize_presets(self) -> Dict[str, PreprocessParams]:
        """실전 검증된 3가지 프리셋"""
        return {
            # 깔끔한 조명, 선명한 텍스트용
            "clean": PreprocessParams(
                name="Clean Text",
                scale=1.5,
                median_blur=3,
                threshold_method="otsu",
                morph_operation="none",
                sharpening=0.2
            ),
            
            # 그림자, 불균등 조명용  
            "shadow": PreprocessParams(
                name="Shadow Correction",
                scale=1.8,
                median_blur=3,
                threshold_method="adaptive",
                adaptive_block_size=45,
                adaptive_C=12,
                morph_operation="close",
                morph_kernel_size=2,
                sharpening=0.1
            ),
            
            # 작은 글씨, 얇은 글꼴용
            "thin": PreprocessParams(
                name="Thin Text",
                scale=2.2,
                median_blur=0,  # 노이즈 제거 안 함 (글자 보존)
                threshold_method="adaptive", 
                adaptive_block_size=25,
                adaptive_C=6,
                morph_operation="close",
                morph_kernel_size=2,
                sharpening=0.3
            )
        }
    
    def _optimize_image_size(self, image: np.ndarray, max_dimension: int = 800) -> Tuple[np.ndarray, float]:
        """이미지 크기 최적화 - EasyOCR 안정성을 위한 자동 리사이징"""
        h, w = image.shape[:2]
        max_current = max(h, w)
        
        if max_current <= max_dimension:
            return image, 1.0
        
        # EasyOCR 최적 크기로 다운스케일
        ratio = max_dimension / max_current
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        
        if len(image.shape) == 3:
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
        self.logger.info(f"📐 Auto-resized: {w}x{h} → {new_w}x{new_h} (ratio: {ratio:.2f})")
        return resized, ratio
    
    def process_with_params(self, image: np.ndarray, params: PreprocessParams) -> np.ndarray:
        """파라미터 기반 이미지 전처리 (자동 크기 최적화 포함)"""
        try:
            # 0단계: 자동 크기 최적화 (EasyOCR 안정성 보장)
            optimized_image, size_ratio = self._optimize_image_size(image)
            
            # 그레이스케일 변환
            if len(optimized_image.shape) == 3:
                gray = cv2.cvtColor(optimized_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = optimized_image.copy()
            
            self.logger.info(f"🔧 Processing with {params.name} preset...")
            
            # 1단계: 리사이즈 (업스케일 - 크기 최적화 후에 적용)
            if params.scale != 1.0:
                new_width = int(gray.shape[1] * params.scale)
                new_height = int(gray.shape[0] * params.scale)
                gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                self.logger.info(f"   📏 Upscaled: x{params.scale}")
            
            # 2단계: 노이즈 제거
            if params.median_blur > 0:
                gray = cv2.medianBlur(gray, params.median_blur)
                self.logger.info(f"   🧹 Denoised: kernel={params.median_blur}")
            
            # 3단계: 이진화
            if params.threshold_method == "otsu":
                _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                self.logger.info("   ⚫ Threshold: OTSU")
            else:
                binary = cv2.adaptiveThreshold(
                    gray, 255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY,
                    params.adaptive_block_size,
                    params.adaptive_C
                )
                self.logger.info(f"   ⚫ Adaptive: block={params.adaptive_block_size}, C={params.adaptive_C}")
            
            # 4단계: 모폴로지 연산
            if params.morph_operation != "none" and params.morph_kernel_size > 0:
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, 
                                                 (params.morph_kernel_size, params.morph_kernel_size))
                if params.morph_operation == "open":
                    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
                    self.logger.info(f"   🔓 Opening: kernel={params.morph_kernel_size}")
                elif params.morph_operation == "close":
                    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
                    self.logger.info(f"   🔒 Closing: kernel={params.morph_kernel_size}")
            
            # 5단계: 샤프닝 (선택적)
            if params.sharpening > 0:
                # Unsharp Mask 효과
                blur = cv2.GaussianBlur(binary, (5, 5), 1.0)
                binary = cv2.addWeighted(binary, 1.0 + params.sharpening, blur, -params.sharpening, 0)
                binary = np.clip(binary, 0, 255).astype(np.uint8)
                self.logger.info(f"   ✨ Sharpened: strength={params.sharpening}")
            
            # BGR로 변환 (OCR 호환성)
            result = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Processing error with {params.name}: {e}")
            return image
    
    def calculate_quality_score(self, processed_image: np.ndarray) -> float:
        """이미지 품질 점수 계산 (0~100)"""
        try:
            # 그레이스케일 변환
            if len(processed_image.shape) == 3:
                gray = cv2.cvtColor(processed_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = processed_image
            
            # 여러 품질 지표들
            scores = []
            
            # 1. 엣지 밀도 (텍스트 선명도)
            edges = cv2.Canny(gray, 100, 200)
            edge_density = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])
            edge_score = min(edge_density * 500, 30)  # 최대 30점
            scores.append(edge_score)
            
            # 2. 대비 (히스토그램 분산)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            contrast_score = min(np.var(hist) / 10000, 25)  # 최대 25점
            scores.append(contrast_score)
            
            # 3. 이진화 품질 (0/255 비율)
            binary_pixels = np.sum((gray == 0) | (gray == 255))
            total_pixels = gray.shape[0] * gray.shape[1]
            binary_ratio = binary_pixels / total_pixels
            binary_score = binary_ratio * 25  # 최대 25점
            scores.append(binary_score)
            
            # 4. 노이즈 페널티 (작은 영역들)
            contours, _ = cv2.findContours(255 - gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            small_contours = [c for c in contours if cv2.contourArea(c) < 10]
            noise_penalty = min(len(small_contours) / 100, 10)  # 최대 10점 감점
            
            total_score = sum(scores) - noise_penalty
            return max(0, min(100, total_score))
            
        except Exception as e:
            self.logger.error(f"Quality score calculation error: {e}")
            return 50.0  # 기본 점수
    
    def auto_select_best_preset(self, image: np.ndarray) -> Tuple[str, np.ndarray, float]:
        """자동으로 최적 프리셋 선택"""
        self.logger.info("🎯 Auto-selecting best preset...")
        
        best_preset = "clean"
        best_result = image
        best_score = 0.0
        
        for preset_name, params in self.presets.items():
            # 각 프리셋으로 처리
            processed = self.process_with_params(image, params)
            score = self.calculate_quality_score(processed)
            
            self.logger.info(f"   {preset_name}: {score:.1f} points")
            
            if score > best_score:
                best_score = score
                best_result = processed
                best_preset = preset_name
        
        self.logger.info(f"🏆 Selected: {best_preset} ({best_score:.1f} points)")
        return best_preset, best_result, best_score
    
    def process_image(self, image: np.ndarray, preset: str = "auto") -> np.ndarray:
        """메인 처리 함수"""
        if preset == "auto":
            _, result, _ = self.auto_select_best_preset(image)
            return result
        elif preset in self.presets:
            return self.process_with_params(image, self.presets[preset])
        else:
            self.logger.warning(f"Unknown preset: {preset}, using 'clean'")
            return self.process_with_params(image, self.presets["clean"])
    
    def get_available_presets(self) -> List[str]:
        """사용 가능한 프리셋 목록"""
        return list(self.presets.keys())
    
    def tune_parameters(self, images: List[np.ndarray], iterations: int = 50) -> PreprocessParams:
        """랜덤 탐색으로 파라미터 튜닝"""
        self.logger.info(f"🔬 Starting parameter tuning ({iterations} iterations)...")
        
        best_params = self.presets["clean"]  # 기본값
        best_score = 0.0
        
        for i in range(iterations):
            # 랜덤 파라미터 생성
            random_params = PreprocessParams(
                name=f"Tuned_{i}",
                scale=np.random.uniform(1.2, 2.5),
                median_blur=np.random.choice([0, 3, 5]),
                threshold_method=np.random.choice(["otsu", "adaptive"]),
                adaptive_block_size=np.random.choice(range(25, 72, 2)),  # 홀수만
                adaptive_C=np.random.randint(3, 21),
                morph_operation=np.random.choice(["none", "open", "close"]),
                morph_kernel_size=np.random.choice([0, 2, 3]),
                sharpening=np.random.uniform(0, 0.5)
            )
            
            # 모든 이미지에 대해 평균 점수 계산
            total_score = 0
            for img in images:
                processed = self.process_with_params(img, random_params)
                score = self.calculate_quality_score(processed)
                total_score += score
            
            avg_score = total_score / len(images)
            
            if avg_score > best_score:
                best_score = avg_score
                best_params = random_params
                self.logger.info(f"   New best: {avg_score:.1f} (iteration {i})")
        
        self.logger.info(f"🏆 Tuning completed. Best score: {best_score:.1f}")
        return best_params


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    print("📚 Office Lens Book Preprocessor")
    print("=" * 50)
    print("✅ 3가지 프리셋: Clean / Shadow / Thin")
    print("✅ 파라미터 기반 튜닝")
    print("✅ 자동 품질 평가 및 선택")
    print("✅ Office Lens 스캔 이미지 최적화")
    print("=" * 50)