"""
🔍 Book Fingerprint System - Phase 2 Book Sense Engine

Purpose: 책의 고유 특성을 자동 감지하여 맞춤형 교정 기준 생성
Paradigm: 사후학습 → 사전기준생성 전환의 핵심 컴포넌트

Core Innovation:
- OCR 텍스트로부터 책의 Typography, Language Pattern, Domain 자동 분석
- 동일 책 재인식으로 기존 Book Profile 재활용 (비용 최적화)
- GPT 1회 호출을 위한 최적화된 책 정보 추출

Author: SnapTXT Team
Date: 2026-03-02
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
import hashlib
import re
import json
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BookDomain(Enum):
    """책의 도메인 분류"""
    NOVEL = "novel"              # 소설, 문학
    TEXTBOOK = "textbook"        # 학술서, 교과서
    MAGAZINE = "magazine"        # 잡지, 뉴스
    ACADEMIC = "academic"        # 논문, 학술지
    MANUAL = "manual"           # 매뉴얼, 기술서
    GENERAL = "general"         # 일반 도서
    UNKNOWN = "unknown"         # 분류 불가


class LanguageStyle(Enum):
    """언어 스타일 분류"""
    KOREAN_FORMAL = "korean_formal"      # 격식체 한국어
    KOREAN_INFORMAL = "korean_informal"  # 구어체 한국어
    ENGLISH_ACADEMIC = "english_academic" # 학술 영어
    ENGLISH_CASUAL = "english_casual"   # 일반 영어
    MIXED_BILINGUAL = "mixed_bilingual" # 한영 혼용
    TECHNICAL = "technical"             # 기술 문서
    UNKNOWN = "unknown"


@dataclass
class TypographyProfile:
    """책의 타이포그래피 특성"""
    avg_line_length: float          # 평균 줄 길이
    paragraph_break_pattern: str    # 문단 구분 패턴
    punctuation_density: Dict[str, float]  # 문장부호 밀도
    spacing_patterns: Dict[str, int]       # 공백 패턴 빈도
    font_characteristics: Dict[str, str]   # 폰트 특성 (추정)
    formatting_style: str          # 서식 스타일


@dataclass
class ContentProfile:
    """책의 내용 특성"""
    domain: BookDomain
    language_style: LanguageStyle
    technical_terms_count: int      # 전문 용어 빈도
    complexity_score: float         # 내용 복잡도
    vocabulary_diversity: float     # 어휘 다양성
    sentence_structure_patterns: List[str]  # 문장 구조 패턴


@dataclass
class QualityProfile:
    """OCR 품질 특성"""
    avg_confidence: float           # 평균 신뢰도
    consistent_errors: Dict[str, int]  # 반복 오류 패턴
    problematic_characters: Set[str]   # 문제 문자들
    recognition_difficulty: float   # 인식 난이도
    image_quality_indicators: Dict[str, float]  # 이미지 품질 지표


@dataclass
class BookFingerprint:
    """책의 종합적인 지문 정보"""
    book_id: str                    # 책 고유 ID (해시값)
    confidence: float               # 지문 신뢰도
    typography: TypographyProfile   # 타이포그래피 특성
    content: ContentProfile         # 내용 특성  
    quality: QualityProfile         # OCR 품질 특성
    sample_count: int              # 분석에 사용된 샘플 수
    created_at: str                # 생성 시점
    fingerprint_hash: str          # 지문 해시 (중복 검증용)
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환하여 저장 가능하게 함"""
        return {
            'book_id': self.book_id,
            'confidence': self.confidence,
            'typography': {
                'avg_line_length': self.typography.avg_line_length,
                'paragraph_break_pattern': self.typography.paragraph_break_pattern,
                'punctuation_density': self.typography.punctuation_density,
                'spacing_patterns': self.typography.spacing_patterns,
                'font_characteristics': self.typography.font_characteristics,
                'formatting_style': self.typography.formatting_style
            },
            'content': {
                'domain': self.content.domain.value,
                'language_style': self.content.language_style.value,
                'technical_terms_count': self.content.technical_terms_count,
                'complexity_score': self.content.complexity_score,
                'vocabulary_diversity': self.content.vocabulary_diversity,
                'sentence_structure_patterns': self.content.sentence_structure_patterns
            },
            'quality': {
                'avg_confidence': self.quality.avg_confidence,
                'consistent_errors': self.quality.consistent_errors,
                'problematic_characters': list(self.quality.problematic_characters),
                'recognition_difficulty': self.quality.recognition_difficulty,
                'image_quality_indicators': self.quality.image_quality_indicators
            },
            'sample_count': self.sample_count,
            'created_at': self.created_at,
            'fingerprint_hash': self.fingerprint_hash
        }


class BookFingerprintAnalyzer:
    """책의 고유 특성을 분석하여 지문 생성"""
    
    def __init__(self):
        """초기화 - 분석에 필요한 패턴과 규칙 설정"""
        self.domain_keywords = {
            BookDomain.NOVEL: ['소설', '주인공', '그녀는', '그는', '이야기', '장면'],
            BookDomain.TEXTBOOK: ['학습', '정의', '예시', '문제', '연습', '장', '절'],
            BookDomain.ACADEMIC: ['연구', '분석', '이론', '방법', '결과', '결론', '참고문헌'],
            BookDomain.MAGAZINE: ['기사', '인터뷰', '리뷰', '특집', '뉴스'],
            BookDomain.MANUAL: ['설정', '단계', '방법', '주의', '경고', '사용법', '시스템', '알고리즘', '구현', '성능', '최적화']
        }
        
        self.korean_formal_patterns = [
            r'니다\.$', r'습니다\.$', r'였습니다\.$', r'입니다\.$'
        ]
        
        self.korean_informal_patterns = [
            r'야\.$', r'지\.$', r'어\.$', r'아\.$', r'네\.$'
        ]
        
        self.english_academic_patterns = [
            r'\b(research|analysis|theory|method|conclusion)\b',
            r'\b(furthermore|moreover|however|therefore)\b'
        ]
        
    def analyze_typography(self, text_samples: List[str]) -> TypographyProfile:
        """타이포그래피 특성 분석"""
        
        # 평균 줄 길이 계산
        line_lengths = []
        all_text = "\n".join(text_samples)
        lines = all_text.split('\n')
        line_lengths = [len(line.strip()) for line in lines if line.strip()]
        avg_line_length = sum(line_lengths) / len(line_lengths) if line_lengths else 0
        
        # 문단 구분 패턴 분석
        paragraph_breaks = re.findall(r'\n\s*\n', all_text)
        paragraph_break_pattern = "double_newline" if paragraph_breaks else "single_newline"
        
        # 문장부호 밀도 분석
        punctuation_counts = {}
        punctuation_marks = ['.', ',', '!', '?', ';', ':', '"', "'", '(', ')', '-']
        total_chars = len(re.sub(r'\s', '', all_text))
        
        for mark in punctuation_marks:
            count = all_text.count(mark)
            punctuation_counts[mark] = count / total_chars if total_chars > 0 else 0
            
        # 공백 패턴 분석
        spacing_patterns = {
            'single_space': all_text.count(' '),
            'double_space': all_text.count('  '), 
            'tab': all_text.count('\t'),
            'multiple_spaces': len(re.findall(r' {3,}', all_text))
        }
        
        # 폰트 특성 추정 (OCR 오류 패턴으로부터)
        font_characteristics = self._analyze_font_characteristics(all_text)
        
        # 서식 스타일 판단
        formatting_style = self._detect_formatting_style(all_text)
        
        return TypographyProfile(
            avg_line_length=avg_line_length,
            paragraph_break_pattern=paragraph_break_pattern,
            punctuation_density=punctuation_counts,
            spacing_patterns=spacing_patterns,
            font_characteristics=font_characteristics,
            formatting_style=formatting_style
        )
        
    def analyze_content(self, text_samples: List[str]) -> ContentProfile:
        """내용 특성 분석"""
        all_text = " ".join(text_samples)
        
        # 도메인 분류
        domain = self._classify_domain(all_text)
        
        # 언어 스타일 분석
        language_style = self._analyze_language_style(all_text)
        
        # 전문 용어 카운트
        technical_terms_count = self._count_technical_terms(all_text)
        
        # 내용 복잡도 계산
        complexity_score = self._calculate_complexity(all_text)
        
        # 어휘 다양성 계산
        vocabulary_diversity = self._calculate_vocabulary_diversity(all_text)
        
        # 문장 구조 패턴 분석
        sentence_patterns = self._analyze_sentence_patterns(all_text)
        
        return ContentProfile(
            domain=domain,
            language_style=language_style,
            technical_terms_count=technical_terms_count,
            complexity_score=complexity_score,
            vocabulary_diversity=vocabulary_diversity,
            sentence_structure_patterns=sentence_patterns
        )
        
    def analyze_quality(self, ocr_results: List[Dict]) -> QualityProfile:
        """OCR 품질 특성 분석"""
        
        # 평균 신뢰도 계산
        confidences = []
        for result in ocr_results:
            if 'confidence' in result:
                confidences.append(result['confidence'])
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        # 일관된 오류 패턴 분석
        consistent_errors = self._find_consistent_errors(ocr_results)
        
        # 문제 문자들 식별
        problematic_chars = self._identify_problematic_characters(ocr_results)
        
        # 인식 난이도 계산
        recognition_difficulty = self._calculate_recognition_difficulty(ocr_results)
        
        # 이미지 품질 지표
        quality_indicators = self._analyze_image_quality(ocr_results)
        
        return QualityProfile(
            avg_confidence=avg_confidence,
            consistent_errors=consistent_errors,
            problematic_characters=problematic_chars,
            recognition_difficulty=recognition_difficulty,
            image_quality_indicators=quality_indicators
        )
        
    def generate_fingerprint(self, text_samples: List[str], ocr_results: List[Dict]) -> BookFingerprint:
        """종합적인 책 지문 생성"""
        
        # 각 프로파일 생성
        typography = self.analyze_typography(text_samples)
        content = self.analyze_content(text_samples)
        quality = self.analyze_quality(ocr_results)
        
        # 책 ID 생성 (내용 기반 해시)
        book_content = " ".join(text_samples[:5])  # 처음 5개 샘플로 생성
        book_id = hashlib.md5(book_content.encode()).hexdigest()[:16]
        
        # 지문 신뢰도 계산 (샘플 수와 일관성 기반)
        confidence = min(1.0, len(text_samples) / 10.0 * 0.7 + quality.avg_confidence * 0.3)
        
        # 지문 해시 생성 (중복 검증용)
        fingerprint_data = f"{typography.avg_line_length}_{content.domain.value}_{content.language_style.value}"
        fingerprint_hash = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]
        
        from datetime import datetime
        
        return BookFingerprint(
            book_id=book_id,
            confidence=confidence,
            typography=typography,
            content=content,
            quality=quality,
            sample_count=len(text_samples),
            created_at=datetime.now().isoformat(),
            fingerprint_hash=fingerprint_hash
        )
    
    # === Helper Methods ===
    
    def _analyze_font_characteristics(self, text: str) -> Dict[str, str]:
        """폰트 특성 추정 (OCR 오류 패턴 기반)"""
        characteristics = {}
        
        # 자주 혼동되는 문자 패턴으로 폰트 추정
        if 'rn' in text or 'cl' in text:
            characteristics['serif_likelihood'] = 'high'
        if text.count('ㅣ') > text.count('l') * 2:
            characteristics['korean_font_clarity'] = 'low'
            
        return characteristics
        
    def _detect_formatting_style(self, text: str) -> str:
        """서식 스타일 감지"""
        if re.search(r'^\d+\.\s', text, re.MULTILINE):
            return "numbered_list"
        if re.search(r'^[•▪▫]\s', text, re.MULTILINE): 
            return "bullet_list"
        if re.search(r'^제\d+장', text, re.MULTILINE):
            return "chapter_based"
        return "plain_text"
        
    def _classify_domain(self, text: str) -> BookDomain:
        """도메인 분류"""
        scores = {domain: 0 for domain in BookDomain}
        
        for domain, keywords in self.domain_keywords.items():
            for keyword in keywords:
                scores[domain] += text.count(keyword)
                
        if max(scores.values()) == 0:
            return BookDomain.UNKNOWN
            
        return max(scores, key=scores.get)
        
    def _analyze_language_style(self, text: str) -> LanguageStyle:
        """언어 스타일 분석"""
        
        # 한국어 격식체 패턴 검사
        formal_count = sum(1 for pattern in self.korean_formal_patterns 
                          if re.search(pattern, text))
                          
        # 한국어 구어체 패턴 검사  
        informal_count = sum(1 for pattern in self.korean_informal_patterns
                            if re.search(pattern, text))
                            
        # 영어 학술 패턴 검사
        academic_count = sum(1 for pattern in self.english_academic_patterns
                           if re.search(pattern, text, re.IGNORECASE))
                           
        if formal_count > informal_count and formal_count > 0:
            return LanguageStyle.KOREAN_FORMAL
        elif informal_count > 0:
            return LanguageStyle.KOREAN_INFORMAL
        elif academic_count > 0:
            return LanguageStyle.ENGLISH_ACADEMIC
        elif re.search(r'[a-zA-Z]', text):
            return LanguageStyle.ENGLISH_CASUAL if not academic_count else LanguageStyle.ENGLISH_ACADEMIC
        else:
            return LanguageStyle.UNKNOWN
            
    def _count_technical_terms(self, text: str) -> int:
        """전문 용어 개수 카운트"""
        # 간단한 휴리스틱: 영어 단어, 한자어, 전문 용어 패턴
        technical_patterns = [
            r'\b[A-Z]{2,}\b',  # 대문자 약어
            r'\b\w+(?:ology|graphy|ism)\b',  # 학문 접미사
            r'[一-龯]+',  # 한자
        ]
        
        count = 0
        for pattern in technical_patterns:
            count += len(re.findall(pattern, text))
        return count
        
    def _calculate_complexity(self, text: str) -> float:
        """내용 복잡도 계산"""
        sentences = re.split(r'[.!?]+', text)
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        
        if not sentence_lengths:
            return 0.0
            
        avg_length = sum(sentence_lengths) / len(sentence_lengths)
        complexity = min(1.0, avg_length / 20.0)  # 20단어를 기준으로 정규화
        
        return complexity
        
    def _calculate_vocabulary_diversity(self, text: str) -> float:
        """어휘 다양성 계산 (Type-Token Ratio)"""
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return 0.0
            
        unique_words = set(words)
        diversity = len(unique_words) / len(words)
        
        return diversity
        
    def _analyze_sentence_patterns(self, text: str) -> List[str]:
        """문장 구조 패턴 분석"""
        patterns = []
        
        # 시작 패턴
        if re.search(r'^그런데', text, re.MULTILINE):
            patterns.append("conjunctive_start")
        if re.search(r'^따라서', text, re.MULTILINE):
            patterns.append("conclusive_start")
            
        # 종결 패턴
        if re.search(r'다\.$', text, re.MULTILINE):
            patterns.append("declarative_ending")
        if re.search(r'까\?$', text, re.MULTILINE):
            patterns.append("interrogative_ending")
            
        return patterns
        
    def _find_consistent_errors(self, ocr_results: List[Dict]) -> Dict[str, int]:
        """일관된 OCR 오류 패턴 찾기"""
        error_patterns = {}
        
        # 실제 구현에서는 ground truth와 비교하여 오류 패턴 찾기
        # 현재는 시뮬레이션
        common_ocr_errors = {
            'rn': 'm',
            'cl': 'd', 
            'ㅣ': 'l',
            '되엇': '되었'
        }
        
        for result in ocr_results:
            text = result.get('text', '')
            for error, correct in common_ocr_errors.items():
                count = text.count(error)
                if count > 0:
                    error_patterns[f"{error}→{correct}"] = error_patterns.get(f"{error}→{correct}", 0) + count
                    
        return error_patterns
        
    def _identify_problematic_characters(self, ocr_results: List[Dict]) -> Set[str]:
        """문제 문자들 식별"""
        problematic = set()
        
        # 낮은 신뢰도 문자들 수집
        for result in ocr_results:
            if result.get('confidence', 1.0) < 0.7:
                text = result.get('text', '')
                problematic.update(list(text))
                
        return problematic
        
    def _calculate_recognition_difficulty(self, ocr_results: List[Dict]) -> float:
        """인식 난이도 계산"""
        confidences = [r.get('confidence', 0.5) for r in ocr_results]
        if not confidences:
            return 0.5
            
        avg_confidence = sum(confidences) / len(confidences)
        difficulty = 1.0 - avg_confidence
        
        return difficulty
        
    def _analyze_image_quality(self, ocr_results: List[Dict]) -> Dict[str, float]:
        """이미지 품질 지표 분석"""
        # 실제로는 이미지 메타데이터에서 추출
        # 현재는 OCR 결과로부터 추정
        indicators = {
            'blur_estimation': 0.0,
            'noise_level': 0.0,
            'contrast_score': 0.8,
            'resolution_adequacy': 0.9
        }
        
        # OCR 신뢰도로부터 대략적인 품질 추정
        avg_confidence = sum(r.get('confidence', 0.5) for r in ocr_results) / len(ocr_results) if ocr_results else 0.5
        
        if avg_confidence < 0.6:
            indicators['blur_estimation'] = 0.4
            indicators['noise_level'] = 0.6
            indicators['contrast_score'] = 0.5
            
        return indicators


# === 사용 예시와 테스트 코드 ===

if __name__ == "__main__":
    # 테스트를 위한 샘플 데이터
    sample_texts = [
        "이 책은 Python 프로그래밍의 기초를 다룹니다. 1장에서는 변수와 데이터 타입을 학습합니다.",
        "함수는 코드의 재사용성을 높이는 중요한 개념입니다. def 키워드로 정의할 수 있습니다.",
        "객체지향 프로그래밍은 현대 소프트웨어 개발의 핵심 패러다임입니다."
    ]
    
    sample_ocr_results = [
        {'text': "이 책은 Python 프로그래밍의 기초를 다룹니다.", 'confidence': 0.95},
        {'text': "함수는 코드의 재사용성을 높이는 중요한 개념입니다.", 'confidence': 0.88},
        {'text': "객체지향 프로그래밍은 현대 소프트웨어 개발의", 'confidence': 0.92}
    ]
    
    # 분석기 생성 및 테스트
    analyzer = BookFingerprintAnalyzer()
    fingerprint = analyzer.generate_fingerprint(sample_texts, sample_ocr_results)
    
    print("=" * 50)
    print("🔍 Book Fingerprint Analysis Result")
    print("=" * 50)
    print(f"Book ID: {fingerprint.book_id}")
    print(f"Confidence: {fingerprint.confidence:.2f}")
    print(f"Domain: {fingerprint.content.domain.value}")
    print(f"Language Style: {fingerprint.content.language_style.value}")
    print(f"Average Confidence: {fingerprint.quality.avg_confidence:.2f}")
    print(f"Sample Count: {fingerprint.sample_count}")
    print(f"Consistent Errors: {fingerprint.quality.consistent_errors}")
    print("=" * 50)
    
    # JSON 출력 테스트
    fingerprint_dict = fingerprint.to_dict()
    print("📝 JSON Export Test:")
    print(json.dumps(fingerprint_dict, indent=2, ensure_ascii=False)[:500] + "...")