#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Korean OCR Processor
고도화된 한국어 OCR 후처리 모듈 - kiwipiepy, soynlp, KSS 통합
"""

import re
import time
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class EnhancedKoreanProcessor:
    """고도화된 한국어 텍스트 후처리기"""
    
    def __init__(self):
        """초기화 및 라이브러리 로드"""
        self.kiwi = None
        self.init_libraries()
        self.user_dict = {}  # 사용자 사전
        self.performance_stats = {
            'processing_times': [],
            'error_corrections': 0,
            'morpheme_corrections': 0
        }
        
    def init_libraries(self):
        """외부 라이브러리 초기화"""
        try:
            # kiwipiepy 초기화 (형태소 분석)
            from kiwipiepy import Kiwi
            self.kiwi = Kiwi()
            logger.info("✅ kiwipiepy 초기화 완료")
        except ImportError:
            logger.warning("⚠️ kiwipiepy 미설치 - 기본 처리 모드")
        except Exception as e:
            logger.error(f"❌ kiwipiepy 초기화 실패: {e}")
    
    def process_text(self, text: str, enable_morpheme_analysis: bool = True) -> Dict:
        """
        텍스트 종합 후처리
        
        Args:
            text: 원본 텍스트
            enable_morpheme_analysis: 형태소 분석 활성화
            
        Returns:
            Dict: 처리 결과 및 통계
        """
        start_time = time.time()
        
        try:
            # 1. 기본 정리
            processed_text = self._basic_cleanup(text)
            
            # 2. OCR 오류 패턴 수정 (확장판)
            processed_text = self._fix_ocr_errors_extended(processed_text)
            
            # 3. 형태소 분석 기반 교정 (선택적)
            if enable_morpheme_analysis and self.kiwi:
                processed_text = self._morpheme_based_correction(processed_text)
            
            # 4. 띄어쓰기 개선 (고급 버전)
            processed_text = self._advanced_spacing_correction(processed_text)
            
            # 5. 문장 구조 개선
            processed_text = self._improve_sentence_structure(processed_text)
            
            # 6. 사용자 사전 적용
            processed_text = self._apply_user_dictionary(processed_text)
            
            # 7. 최종 검증
            processed_text = self._final_validation(processed_text)
            
            # 성능 통계 업데이트
            processing_time = time.time() - start_time
            self.performance_stats['processing_times'].append(processing_time)
            
            return {
                'success': True,
                'original_text': text,
                'processed_text': processed_text,
                'processing_time': processing_time,
                'corrections_applied': self._count_corrections(text, processed_text),
                'quality_score': self._calculate_quality_score(processed_text)
            }
            
        except Exception as e:
            logger.error(f"텍스트 처리 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'original_text': text,
                'processed_text': text  # 실패시 원본 반환
            }
    
    def _basic_cleanup(self, text: str) -> str:
        """기본 텍스트 정리"""
        # 연속된 공백, 특수문자 정리
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r'\?{2,}', '?', text)
        text = re.sub(r'!{2,}', '!', text)
        
        return text.strip()
    
    def _fix_ocr_errors_extended(self, text: str) -> str:
        """확장된 OCR 오류 패턴 수정"""
        
        # 기존 easyocr_worker.py에서 가져온 패턴 + 추가 패턴
        extended_patterns = {
            # 1. 영문 이름 오류 (확장)
            '마이름상어': '마이클 싱어', '마이클상어': '마이클 싱어', '마이칼심어': '마이클 싱어',
            '원프리': '윈프리', '소율': '소울', '곧경': '곤경', '상어든': '싱어는',
            
            # 2. 한글 조사/어미 오류 (대폭 확장)
            '기틀': '기를', '부탁울': '부탁을', '이기지': '이기지', '자유로위지': '자유로워지',
            '을컷고': '올랐고', '소개되워': '소개되었', '두없던': '두었던', '우리튼': '우리를',
            '그이후': '그 이후', '돌두했': '돌입했', '깊은내면': '깊은 내면', '드러넷': '드러냈',
            '알려저': '알려져', '지처': '지쳐', '되워': '되어', '겨져': '겪어',
            
            # 3. 자주 틀리는 단어들
            '하나너': '하나님', '사악': '사람', '내숭': '내용', '세제': '세계',
            '인갑': '인간', '부족할': '부족한', '쳬험': '체험', '현젠': '현실',
            '사뭄들': '사람들', '이여기': '이야기', '설각': '생각', '가슴속': '가슴 속',
            
            # 4. 숫자 관련 오류
            '2o1g': '2019', '2o2o': '2020', '2o21': '2021', '2o22': '2022',
            '1o': '10', '1oo': '100', '1ooo': '1000',
            
            # 5. 특수 문자 오류
            '，': ',', '；': ';', '：': ':', '？': '?', '！': '!',
            '（': '(', '）': ')', '［': '[', '］': ']', '｛': '{', '｝': '}',
            
            # 6. 영문 단어 오류 (확장)
            'teh': 'the', 'adn': 'and', 'hte': 'the', 'youer': 'your',
            'Michacl': 'Michael', 'Sinyer': 'Singer', 'Uniyerse': 'Universe',
        }
        
        # 패턴 적용
        corrections = 0
        for wrong, correct in extended_patterns.items():
            if wrong in text:
                text = text.replace(wrong, correct)
                corrections += 1
        
        self.performance_stats['error_corrections'] += corrections
        return text
    
    def _morpheme_based_correction(self, text: str) -> str:
        """형태소 분석 기반 교정"""
        if not self.kiwi:
            return text
            
        try:
            # 문장별로 처리
            sentences = text.split('.')
            corrected_sentences = []
            
            for sentence in sentences:
                if sentence.strip():
                    # 형태소 분석
                    tokens = self.kiwi.tokenize(sentence.strip())
                    
                    # 형태소 기반 띄어쓰기 교정
                    corrected_words = []
                    for token in tokens:
                        # 조사, 어미는 앞 단어와 붙여쓰기
                        if token.tag.startswith(('J', 'E')) and corrected_words:
                            corrected_words[-1] += token.form
                        else:
                            corrected_words.append(token.form)
                    
                    corrected_sentences.append(' '.join(corrected_words))
                    self.performance_stats['morpheme_corrections'] += 1
            
            return '. '.join(corrected_sentences) + ('.' if text.endswith('.') else '')
            
        except Exception as e:
            logger.warning(f"형태소 분석 실패: {e}")
            return text
    
    def _advanced_spacing_correction(self, text: str) -> str:
        """고급 띄어쓰기 교정"""
        
        # 1. 조사 분리 (더 정교한 패턴)
        text = re.sub(r'([가-힣]{2,})(은|는|이|가|을|를|과|와|에|에서|에게|로|으로|의|도|만|부터|까지|처럼|같이|마다|보다)', r'\1 \2', text)
        
        # 2. 어미 분리 (확장된 패턴) 
        text = re.sub(r'([가-힣]{2,})(했습니다|합니다|됩니다|입니다|있습니다|없습니다|였습니다)', r'\1 \2', text)
        text = re.sub(r'([가-힣]{2,})(지만|에서|에도|에게|로서|로써|이나|거나|라도|라든지)', r'\1 \2', text)
        
        # 3. 시제 표현 정리
        text = re.sub(r'([가-힣]+)(고있[는다습니까])(?![가-힣])', r'\1고 있\2', text)
        text = re.sub(r'([가-힣]+)(어있[는다습니까])(?![가-힣])', r'\1어 있\2', text)
        text = re.sub(r'([가-힣]+)(아있[는다습니까])(?![가-힣])', r'\1아 있\2', text)
        
        # 4. 복합어 분리
        text = re.sub(r'([가-힣]{2,})(하기|되기|없이|있게|하게|되게|하려|하면|한다)', r'\1 \2', text)
        
        # 5. 관형사/부사 분리
        text = re.sub(r'(매우|정말|아주|너무|특히|항상|절대|전혀|모든|각각|여러)([가-힣]{2,})', r'\1 \2', text)
        
        # 6. 접속사 붙어쓰기 교정
        text = re.sub(r'([가-힣]{2,})(그리고|또한|하지만|그러나|따라서|즉|예를들어|예를들면)', r'\1 \2', text)
        
        return text
    
    def _improve_sentence_structure(self, text: str) -> str:
        """문장 구조 개선"""
        
        # 1. 문장 부호 앞 공백 제거
        text = re.sub(r'\s+([.!?,:;])', r'\1', text)
        
        # 2. 문장 부호 뒤 공백 추가
        text = re.sub(r'([.!?])([가-힣A-Za-z])', r'\1 \2', text)
        
        # 3. 괄호 내부 공백 정리
        text = re.sub(r'\(\s+', '(', text)
        text = re.sub(r'\s+\)', ')', text)
        
        # 4. 따옴표 정리
        text = re.sub(r'"\s+', '"', text)
        text = re.sub(r'\s+"', '"', text)
        
        return text
    
    def _apply_user_dictionary(self, text: str) -> str:
        """사용자 사전 적용"""
        for wrong, correct in self.user_dict.items():
            text = text.replace(wrong, correct)
        return text
    
    def _final_validation(self, text: str) -> str:
        """최종 검증 및 정리"""
        
        # 1. 중복 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        # 2. 줄 시작/끝 공백 제거
        text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
        
        # 3. 최종 trim
        return text.strip()
    
    def _count_corrections(self, original: str, processed: str) -> int:
        """적용된 교정 횟수 계산"""
        # 간단한 차이점 계산 (Levenshtein distance 간소화)
        return len(original) - len(processed) + abs(len(original.split()) - len(processed.split()))
    
    def _calculate_quality_score(self, text: str) -> float:
        """텍스트 품질 점수 계산 (0.0 ~ 1.0)"""
        if not text:
            return 0.0
        
        score = 0.8  # 기본 점수
        
        # 한글 비율
        korean_chars = len(re.findall(r'[가-힣]', text))
        total_chars = len(re.sub(r'\s', '', text))
        if total_chars > 0:
            korean_ratio = korean_chars / total_chars
            score += (korean_ratio * 0.1)
        
        # 문장 구조 점수
        sentences = text.count('.')
        if sentences > 0:
            avg_length = len(text) / sentences
            if 10 <= avg_length <= 100:  # 적절한 문장 길이
                score += 0.05
        
        # 특수문자 오류 점수 (감점)
        special_errors = len(re.findall(r'[？！，；：]', text))
        score -= (special_errors * 0.01)
        
        return min(1.0, max(0.0, score))
    
    def add_user_word(self, wrong: str, correct: str):
        """사용자 사전에 단어 추가"""
        self.user_dict[wrong] = correct
        logger.info(f"사용자 사전 추가: '{wrong}' → '{correct}'")
    
    def get_performance_stats(self) -> Dict:
        """성능 통계 반환"""
        if self.performance_stats['processing_times']:
            avg_time = sum(self.performance_stats['processing_times']) / len(self.performance_stats['processing_times'])
        else:
            avg_time = 0.0
            
        return {
            'total_corrections': self.performance_stats['error_corrections'],
            'morpheme_corrections': self.performance_stats['morpheme_corrections'],
            'average_processing_time': round(avg_time, 3),
            'total_processed': len(self.performance_stats['processing_times'])
        }
    
    def reset_stats(self):
        """통계 초기화"""
        self.performance_stats = {
            'processing_times': [],
            'error_corrections': 0,
            'morpheme_corrections': 0
        }

# 테스트 실행
if __name__ == "__main__":
    processor = EnhancedKoreanProcessor()
    
    test_text = "마이름상어가말했습니다.이것은테스트입니다.자유로위지세요."
    result = processor.process_text(test_text)
    
    print(f"원본: {result['original_text']}")
    print(f"처리결과: {result['processed_text']}")
    print(f"처리시간: {result['processing_time']:.3f}초")
    print(f"품질점수: {result['quality_score']:.2f}")
    print(f"교정횟수: {result['corrections_applied']}")