"""
SnapTXT 고급 OCR 시스템
- 사용자 사전 기반 개인화
- 실시간 피드백 학습
- 지속적 최적화
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import cv2
import numpy as np
from collections import defaultdict, Counter

class PersonalDictionary:
    """개인화된 사용자 사전 시스템"""
    
    def __init__(self, db_path: str = "user_dictionary.db"):
        self.db_path = db_path
        self.init_database()
        self.word_frequency = Counter()
        self.correction_patterns = defaultdict(list)
    
    def init_database(self):
        """사용자 사전 데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 사용자 단어 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE,
            frequency INTEGER DEFAULT 1,
            context TEXT,
            domain TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 교정 이력 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original TEXT,
            corrected TEXT,
            confidence REAL,
            session_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 성능 추적 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            accuracy REAL,
            processing_time REAL,
            image_quality REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        conn.close()
    
    def add_word(self, word: str, context: str = "", domain: str = "general"):
        """새 단어를 사전에 추가"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            INSERT OR REPLACE INTO user_words (word, frequency, context, domain, last_used)
            VALUES (?, COALESCE((SELECT frequency FROM user_words WHERE word = ?) + 1, 1), ?, ?, ?)
            """, (word, word, context, domain, datetime.now()))
            conn.commit()
        except Exception as e:
            print(f"단어 추가 오류: {e}")
        finally:
            conn.close()
    
    def get_suggestions(self, partial_word: str, limit: int = 5) -> List[str]:
        """부분 단어에 대한 자동완성 제안"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT word FROM user_words 
        WHERE word LIKE ? 
        ORDER BY frequency DESC, last_used DESC 
        LIMIT ?
        """, (f"{partial_word}%", limit))
        
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results
    
    def record_correction(self, original: str, corrected: str, confidence: float, session_id: str):
        """사용자 교정 기록"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO corrections (original, corrected, confidence, session_id)
        VALUES (?, ?, ?, ?)
        """, (original, corrected, confidence, session_id))
        
        conn.commit()
        conn.close()
        
        # 교정된 단어를 사전에 추가
        self.add_word(corrected, context=f"교정됨: {original}")

class EnhancedImageProcessor:
    """향상된 이미지 전처리"""
    
    @staticmethod
    def adaptive_preprocessing(image: np.ndarray) -> np.ndarray:
        """적응형 이미지 전처리"""
        
        # 1. 그레이스케일 변환
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 2. 노이즈 제거
        denoised = cv2.medianBlur(gray, 3)
        
        # 3. 적응형 히스토그램 평활화 (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # 4. 적응형 이진화
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # 5. 모폴로지 연산으로 문자 정리
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
    
    @staticmethod
    def detect_text_rotation(image: np.ndarray) -> float:
        """텍스트 회전 각도 감지"""
        edges = cv2.Canny(image, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
        
        if lines is not None:
            angles = []
            for rho, theta in lines[:20]:  # 상위 20개 선분만 분석
                angle = np.degrees(theta) - 90
                angles.append(angle)
            
            # 가장 빈번한 각도 반환
            return np.median(angles) if angles else 0
        
        return 0
    
    @staticmethod
    def correct_rotation(image: np.ndarray, angle: float) -> np.ndarray:
        """이미지 회전 보정"""
        if abs(angle) < 0.5:  # 0.5도 미만은 무시
            return image
        
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # 회전된 이미지 크기 계산
        cos_angle = np.abs(matrix[0, 0])
        sin_angle = np.abs(matrix[0, 1])
        new_w = int((h * sin_angle) + (w * cos_angle))
        new_h = int((h * cos_angle) + (w * sin_angle))
        
        # 변환 매트릭스 조정
        matrix[0, 2] += (new_w / 2) - center[0]
        matrix[1, 2] += (new_h / 2) - center[1]
        
        return cv2.warpAffine(image, matrix, (new_w, new_h), 
                             flags=cv2.INTER_CUBIC, 
                             borderMode=cv2.BORDER_REPLICATE)

class ContextAwareOCR:
    """문맥 인식 OCR 시스템"""
    
    def __init__(self, dictionary: PersonalDictionary):
        self.dictionary = dictionary
        self.confidence_threshold = 0.7
    
    def process_with_context(self, text: str, confidence_scores: List[float]) -> str:
        """문맥을 고려한 텍스트 후처리"""
        words = text.split()
        processed_words = []
        
        for i, (word, conf) in enumerate(zip(words, confidence_scores)):
            if conf < self.confidence_threshold:
                # 신뢰도가 낮은 단어에 대해 사전 검색
                suggestions = self.dictionary.get_suggestions(word[:3])
                if suggestions:
                    # 편집 거리가 가장 작은 단어 선택
                    best_match = min(suggestions, 
                                   key=lambda x: self._edit_distance(word, x))
                    processed_words.append(f"[{best_match}]")  # 제안 표시
                else:
                    processed_words.append(f"({word})")  # 의심스러운 단어 표시
            else:
                processed_words.append(word)
                # 확실한 단어는 사전에 추가
                self.dictionary.add_word(word)
        
        return " ".join(processed_words)
    
    @staticmethod
    def _edit_distance(s1: str, s2: str) -> int:
        """편집 거리 계산 (Levenshtein)"""
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
        
        return dp[m][n]

class PerformanceTracker:
    """성능 추적 및 분석 시스템"""
    
    def __init__(self, db_path: str = "user_dictionary.db"):
        self.db_path = db_path
    
    def log_session(self, session_id: str, accuracy: float, 
                   processing_time: float, image_quality: float):
        """세션 성능 로깅"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO performance_log (session_id, accuracy, processing_time, image_quality)
        VALUES (?, ?, ?, ?)
        """, (session_id, accuracy, processing_time, image_quality))
        
        conn.commit()
        conn.close()
    
    def get_performance_trends(self, days: int = 30) -> Dict:
        """성능 트렌드 분석"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT 
            DATE(created_at) as date,
            AVG(accuracy) as avg_accuracy,
            AVG(processing_time) as avg_time,
            COUNT(*) as session_count
        FROM performance_log 
        WHERE created_at >= date('now', '-{} days')
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        """.format(days))
        
        results = cursor.fetchall()
        conn.close()
        
        return {
            'dates': [row[0] for row in results],
            'accuracy': [row[1] for row in results],
            'processing_time': [row[2] for row in results],
            'session_count': [row[3] for row in results]
        }
    
    def analyze_error_patterns(self) -> Dict:
        """오류 패턴 분석"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT 
            original, 
            corrected, 
            COUNT(*) as frequency,
            AVG(confidence) as avg_confidence
        FROM corrections 
        GROUP BY original, corrected
        ORDER BY frequency DESC
        LIMIT 20
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        return {
            'patterns': [
                {
                    'original': row[0],
                    'corrected': row[1], 
                    'frequency': row[2],
                    'avg_confidence': row[3]
                } for row in results
            ]
        }

# 시스템 통합 클래스
class AdvancedOCRSystem:
    """고급 OCR 시스템 통합 클래스"""
    
    def __init__(self):
        self.dictionary = PersonalDictionary()
        self.image_processor = EnhancedImageProcessor()
        self.context_ocr = ContextAwareOCR(self.dictionary)
        self.performance_tracker = PerformanceTracker()
    
    def process_image(self, image: np.ndarray, session_id: str) -> Tuple[str, Dict]:
        """이미지 전체 처리 파이프라인"""
        start_time = datetime.now()
        
        try:
            # 1. 이미지 전처리
            angle = self.image_processor.detect_text_rotation(image)
            if abs(angle) > 0.5:
                image = self.image_processor.correct_rotation(image, angle)
            
            processed_image = self.image_processor.adaptive_preprocessing(image)
            
            # 2. OCR 수행 (기존 EasyOCR/Tesseract 연동)
            # 여기서 기존 OCR 엔진들을 호출
            raw_text, confidence_scores = self._run_ocr_engines(processed_image)
            
            # 3. 문맥 기반 후처리
            enhanced_text = self.context_ocr.process_with_context(raw_text, confidence_scores)
            
            # 4. 성능 기록
            processing_time = (datetime.now() - start_time).total_seconds()
            avg_confidence = np.mean(confidence_scores) if confidence_scores else 0
            
            self.performance_tracker.log_session(
                session_id, avg_confidence, processing_time, 0.8  # image_quality placeholder
            )
            
            return enhanced_text, {
                'confidence': avg_confidence,
                'processing_time': processing_time,
                'rotation_corrected': abs(angle) > 0.5,
                'angle': angle
            }
            
        except Exception as e:
            print(f"OCR 처리 오류: {e}")
            return "", {'error': str(e)}
    
    def _run_ocr_engines(self, image: np.ndarray) -> Tuple[str, List[float]]:
        """OCR 엔진 실행 (기존 코드와 연동)"""
        # 여기서 기존의 EasyOCR/Tesseract를 호출
        # 임시 구현
        return "샘플 텍스트", [0.8, 0.9, 0.7]
    
    def user_correction(self, original: str, corrected: str, 
                       confidence: float, session_id: str):
        """사용자 교정 처리"""
        self.dictionary.record_correction(original, corrected, confidence, session_id)
    
    def get_analytics(self) -> Dict:
        """분석 데이터 반환"""
        return {
            'performance_trends': self.performance_tracker.get_performance_trends(),
            'error_patterns': self.performance_tracker.analyze_error_patterns()
        }

if __name__ == "__main__":
    # 시스템 테스트
    ocr_system = AdvancedOCRSystem()
    
    # 테스트 이미지 처리
    test_image = np.zeros((100, 400), dtype=np.uint8)  # 더미 이미지
    result, metadata = ocr_system.process_image(test_image, "test_session_001")
    
    print(f"OCR 결과: {result}")
    print(f"메타데이터: {metadata}")
    
    # 분석 데이터 확인
    analytics = ocr_system.get_analytics()
    print(f"성능 분석: {analytics}")