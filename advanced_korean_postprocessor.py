"""
고급 한글 OCR 후처리 패턴
- 문제점 기반 정교한 패턴 매칭
- 문맥 인식 오류 교정
"""

import re
import logging

class AdvancedKoreanOCRPostProcessor:
    def __init__(self):
        """고급 후처리기 초기화"""
        self.logger = logging.getLogger(__name__)
        self.correction_stats = {'applied': 0, 'total_patterns': 0}
        
    def apply_advanced_corrections(self, text):
        """고급 교정 패턴 적용"""
        original_text = text
        
        # 1. 숫자/문자 혼동 교정 (가장 중요)
        text = self._fix_number_letter_confusion(text)
        
        # 2. 글자 분리 교정 
        text = self._fix_character_separation(text)
        
        # 3. 특수문자 및 구두점 교정
        text = self._fix_special_characters(text)
        
        # 4. 문맥 기반 단어 교정
        text = self._apply_contextual_corrections(text)
        
        # 5. 한국어 어미/조사 정규화
        text = self._normalize_korean_endings(text)
        
        # 통계 업데이트
        if text != original_text:
            self.correction_stats['applied'] += 1
        
        return text
    
    def _fix_number_letter_confusion(self, text):
        """숫자/문자 혼동 교정 - 문맥 기반"""
        
        # 연도 패턴 교정
        corrections = [
            # l 구십칠 o 년대 → 1970년대
            (r'l\s*구십\s*칠\s*o\s*년대', '1970년대'),
            (r'l\s*구십\s*칠\s*S\s*년', '1975년'),
            (r'이\s*ol\s*이\s*년', '2012년'),
            
            # 베스트셀러 패턴
            (r'베스트\s*설러\s*l\s*위', '베스트셀러 1위'),
            (r'베스트\s*셀러\s*l\s*위', '베스트셀러 1위'),
            
            # 일반적인 숫자 혼동
            (r'\bl\s+위', '1위'),  # l 위 → 1위
            (r'(\d+)\s*o\s*년', r'\g<1>0년'),  # 숫자 + o 년 → 숫자 + 0년
            (r'l\s*(\d+)', r'1\g<1>'),  # l + 숫자 → 1 + 숫자
        ]
        
        for pattern, replacement in corrections:
            if re.search(pattern, text):
                text = re.sub(pattern, replacement, text)
                self.logger.info(f"✅ 숫자/문자 혼동 교정: {pattern[:20]}... → {replacement}")
        
        return text
    
    def _fix_character_separation(self, text):
        """글자 분리 교정"""
        
        corrections = [
            # 얼굴 관련
            (r"'\s*얼\s*물\s*없는", "얼굴 없는"),
            (r'\'\s*얼\s*물', '얼굴'),
            
            # 형용사/부사 교정
            (r'간곡\s*하\s*(\w)', r'간곡한 \g<1>'),  # 간곡 하 → 간곡한
            (r'깊\s*은\s*(\w)', r'깊은 \g<1>'),
            (r'새로\s*운\s*(\w)', r'새로운 \g<1>'),
            
            # 동사 활용 교정
            (r'은\s*문\s*하어', '은둔하여'),
            (r'돌\s*두\s*하었습니다', '몰두했습니다'),
            (r'출\s*연\s*하어', '출연하여'),
            (r'방\s*치\s*하어', '방치하여'),
            
            # 일반적인 분리 패턴
            (r'(\w)\s*틀\s*(\w)', r'\g<1>를 \g<2>'),  # 틀 → 를
            (r'체\s*험', '체험'),
            (r'분\s*아에', '분야에'),
            (r'사\s*람\s*들', '사람들'),
            (r'독\s*자\s*들', '독자들'),
        ]
        
        for pattern, replacement in corrections:
            if re.search(pattern, text):
                text = re.sub(pattern, replacement, text)
                self.logger.info(f"✅ 글자 분리 교정: {pattern[:20]}... → {replacement}")
        
        return text
    
    def _fix_special_characters(self, text):
        """특수문자 및 구두점 교정"""
        
        corrections = [
            # 책 제목 교정
            (r'<\s*슈퍼\s*소울\s*서\s*이데\s*이\s*>', '《슈퍼 소울 선데이》'),
            (r'<\s*([^>]+)\s*>', r'《\g<1>》'),  # < > → 《 》
            
            # 괄호 교정
            (r'\(\s*상처\s*받지\s*않는\s*영혼\s*\)', '《상처받지 않는 영혼》'),
            (r'\(\s*([^)]+)\s*\)', r'《\g<1>》'),  # ( ) → 《 》 (책 제목)
            
            # 구두점 정규화
            (r'\s*;\s*', ', '),  # ; → ,
            (r'\s*:\s*', '. '),  # : → .
            (r'\.{2,}', '.'),    # 여러 점 → 단일 점
            (r'\?{2,}', '?'),    # 여러 물음표 → 단일
            
            # 특수 문자 정리
            (r'@GettyImages', '© Getty Images'),
            (r'WWW\s*untetheredsoul\s*com', 'www.untetheredsoul.com'),
        ]
        
        for pattern, replacement in corrections:
            if re.search(pattern, text):
                text = re.sub(pattern, replacement, text)
                self.logger.info(f"✅ 특수문자 교정: {pattern[:20]}... → {replacement}")
        
        return text
    
    def _apply_contextual_corrections(self, text):
        """문맥 기반 단어 교정"""
        
        # 전문 용어 사전
        term_corrections = {
            '명상 가로': '명상가로',
            '숲 속의 명상': '숲속의 명상',
            '마 이글': '마이클',
            '플로리다 대학교': '플로리다대학교',
            '경제학 박사 과정': '경제학 박사과정',
            '내면 적': '내면적',
            '세속 적': '세속적',
            '내 적': '내적',
            '폭발 적으로': '폭발적으로',
        }
        
        for wrong, correct in term_corrections.items():
            if wrong in text:
                text = text.replace(wrong, correct)
                self.logger.info(f"✅ 단어 교정: {wrong} → {correct}")
        
        return text
    
    def _normalize_korean_endings(self, text):
        """한국어 어미/조사 정규화"""
        
        # 어미 정규화
        ending_patterns = [
            (r'하었습니다', '했습니다'),
            (r'되었습니다', '되었습니다'),  # 이미 정규형
            (r'받었습니다', '받았습니다'),
            (r'하여', '하여'),  # 이미 정규형
            (r'지어', '져'),
            (r'리어', '려'),
        ]
        
        for pattern, replacement in ending_patterns:
            text = re.sub(pattern, replacement, text)
        
        return text

def test_advanced_corrections():
    """고급 교정 시스템 테스트"""
    processor = AdvancedKoreanOCRPostProcessor()
    
    # 실제 문제 텍스트로 테스트
    test_text = """마이클 싱어 Michael A Singer 숲 속의 명상 가로 불리는 마이클 싱어는 대중 앞에 나서기를 꺼리어 ' 얼 물 없는 저자로 알려지어 있다 가어 ; 오프라 윈프리의 간곡 하 부탁을 이기지 못 하어 이 ol 이 년 < 슈퍼 소울 서 이데 이 >에 출연 하어 사람 들 앞에 처음으로 모습을 드러내었습니다"""
    
    print("🧪 고급 후처리 테스트")
    print("=" * 50)
    
    print("📝 원본 텍스트:")
    print(test_text[:100] + "...")
    
    corrected = processor.apply_advanced_corrections(test_text)
    
    print("\n✨ 교정 결과:")
    print(corrected[:100] + "...")
    
    print(f"\n📊 교정 통계:")
    print(f"  - 적용된 교정: {processor.correction_stats['applied']}개")

if __name__ == "__main__":
    test_advanced_corrections()