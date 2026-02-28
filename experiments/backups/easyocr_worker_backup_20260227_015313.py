#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EasyOCR 전용 워커 스크립트 - PyQt5와 완전 분리
"""

import sys
import json
import os
from pathlib import Path
import time

def setup_environment():
    """EasyOCR 실행 환경 최적화"""
    try:
        # 환경 변수 최적화
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        
        # PyTorch CPU 전용 모드
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        
        return True
    except Exception as e:
        print(f"ERROR: 환경 설정 실패: {e}", file=sys.stderr)
        return False

def advanced_korean_text_processor(text):
    """고도화된 한국어 텍스트 후처리 - PyKoSpacing + 다양한 최적화 기법"""
    import re
    
    try:
        # 1. 기본 정리 - 연속된 특수문자 및 공백 정리
        text = re.sub(r'\.{2,}', '.', text)  # 연속된 점들을 하나로
        text = re.sub(r'\s+', ' ', text)     # 연속된 공백을 하나로
        
        # 2. OCR 오류 패턴 수정 (책 OCR 특화 대폭 확장)
        ocr_fixes = {
            # 영문 이름 수정
            '마이름상어': '마이클 싱어', '마이클 상어': '마이클 싱어', '마이칼 심어': '마이클 싱어',
            '마이름생어': '마이클 싱어',  # 새로 추가된 패턴
            '원프리': '윈프리', '소율': '소울', '곧경': '곤경', '상어든': '싱어는',
            
            # 조사/어미 오류 수정 (책에서 가장 빈번)
            '기틀': '기를', '부탁울': '부탁을', '이기 지': '이기지',
            '자유로위지': '자유로워지', '을컷고': '올랐고', '소개되워': '소개되었',
            '두없던': '두었던', '우리튼': '우리를', '그이후': '그 이후',
            '돌두했': '돌입했', '깊은내면': '깊은 내면', '드러넷': '드러냈',
            '알려저': '알려져', '지처': '지쳐',
            
            # 기본 조사/어미 오류
            '오-': '으', '울-': '을', '블': '를', '엔': '에', '올': '을',
            '느-': '는', '겨-': '게', '끠': '께', '웁': '위', '셨': '세',
            
            # 일반적인 한국어 오인식 패턴
            '함들은': '람들은', '쾌습니다': '했습니다', '햇습니다': '했습니다',
            '국업는': '숭배의', '토록': '도록', '빋다': '빚다',
            
            # 자주 틀리는 단어들
            '하나너': '하나님', '사악': '사람', '내숭': '내용', '세제': '세계',
            '인갑': '인간', '부족': '부족', '쳬험': '체험', '현젠': '현실',
            
            # 영문 단어 수정
            'Michacl': 'Michael', 'Sinyer': 'Singer', 'Uniyerse': 'Universe',
            'teh': 'the', 'adn': 'and', 'hte': 'the', 'OGettylmages': '@GettyImages'
        }
        
        for wrong, correct in ocr_fixes.items():
            text = text.replace(wrong, correct)
        
        # 2.5. 정규표현식 기반 띄어쓰기 개선 (고급 버전)
        import re
        
        # 한글+숫자 분리 (명확한 경우만)
        text = re.sub(r'([가-힣]{2,})([0-9]{4})', r'\1 \2', text)  # 단어+년도
        text = re.sub(r'([0-9]{1,})([가-힣]{2,})', r'\1 \2', text)  # 숫자+단어
        
        # 조사 분리 (더 정교한 패턴)
        text = re.sub(r'([가-힣]{2,})(은|는|이|가|을|를|과|와|에|에서|에게|로|으로|의|도|만|부터|까지|처럼|같이)', r'\1 \2', text)
        
        # 어미 분리 (확장된 패턴)
        text = re.sub(r'([가-힣]{2,})(했습니다|합니다|됩니다|입니다|있습니다|없습니다)', r'\1 \2', text)
        text = re.sub(r'([가-힣]{2,})(지만|에서|에도|에게|로서|로써|이나|거나)', r'\1 \2', text)
        
        # 시제 표현 분리 (책에서 자주 발생)
        text = re.sub(r'([가-힣]+)(고있[는다습니까])(?![가-힣])', r'\1고 있\2', text)
        text = re.sub(r'([가-힣]+)(어있[는다습니까])(?![가-힣])', r'\1어 있\2', text)
        text = re.sub(r'([가-힣]+)(아있[는다습니까])(?![가-힣])', r'\1아 있\2', text)
        
        # 연결어미 분리
        text = re.sub(r'([가-힣]{2,})(하면서|하거나|하지만|한다면|했다면)', r'\1 \2', text)
        
        # 복합어 분리 (일반적 패턴)
        text = re.sub(r'([가-힣]{2,})(하기|되기|없이|있게|하게|되게)', r'\1 \2', text)
        
        # 관형사/부사 분리
        text = re.sub(r'(매우|정말|아주|너무|특히|항상|절대|전혀|모든|각각|여러)([가-힣]{2,})', r'\1 \2', text)
        
        # 접속사 분리
        text = re.sub(r'([가-힣]{2,})(그리고|또한|하지만|그러나|따라서|즉|예를들어)', r'\1 \2', text)
        
        # 3. 한국어 문장 분리 및 띄어쓰기 개선 (soynlp + kss 활용)
        try:
            # KSS를 사용한 문장 분리 (더 정확함)
            import kss
            sentences = kss.split_sentences(text)
            
            # soynlp를 사용한 어절 단위 정리
            from soynlp.normalizer import repeat_normalize
            processed_sentences = []
            
            for sentence in sentences:
                if sentence.strip():
                    # 중복 문자 정리 (ㅋㅋㅋ -> ㅋㅋ, ㅜㅜㅜ -> ㅜㅜ 등)
                    normalized = repeat_normalize(sentence.strip(), num_repeats=2)
                    processed_sentences.append(normalized)
            
            # 문장들을 다시 조합
            text = ' '.join(processed_sentences)
            print("INFO: soynlp + kss 기반 문장 분리 및 정리 완료", file=sys.stderr)
                
        except ImportError:
            print("WARNING: soynlp 또는 kss 모듈을 찾을 수 없어 기본 문장 처리를 사용합니다.", file=sys.stderr)
        except Exception as e:
            print(f"WARNING: 한국어 문장 처리 실패 ({e}), 기본 처리 적용", file=sys.stderr)
        
        # 4. 문단 구조 개선
        text = improve_paragraph_structure(text)
        
        # 5. TTS 최적화 처리
        text = optimize_for_tts(text)
        
        # 6. 최종 정리
        text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
        
        return text
        
    except Exception as e:
        print(f"ERROR: 고급 후처리 실패 ({e}), 기본 처리 적용", file=sys.stderr)
        return basic_korean_text_cleanup(text)

def improve_paragraph_structure(text):
    """문단 구조 개선 - 책 읽기에 최적화"""
    import re
    
    # 문장 끝 패턴 정의
    sentence_endings = r'[.!?]'
    
    # 문단 분리 힌트들
    paragraph_hints = [
        r'\d+\.',  # 번호 목록 (1., 2., 3.)
        r'[가-힣]\)',  # 한글 목록 (가), 나), 다))
        r'•',      # 불릿 포인트
        r'-',      # 대시
        r'※',     # 참고 기호
    ]
    
    lines = text.split('\n')
    improved_lines = []
    
    for i, line in enumerate(lines):
        if not line.strip():
            continue
            
        # 현재 줄이 문단 시작인지 확인
        is_paragraph_start = False
        
        # 번호나 기호로 시작하는지 확인
        for hint in paragraph_hints:
            if re.match(hint, line.strip()):
                is_paragraph_start = True
                break
        
        # 이전 줄과 이어지는지 확인 (문장이 끝나지 않았으면 이어짐)
        if i > 0 and improved_lines:
            prev_line = improved_lines[-1]
            if not re.search(sentence_endings + r'\s*$', prev_line):
                # 이전 문장이 끝나지 않았으면 이어서 씀
                improved_lines[-1] += ' ' + line.strip()
            else:
                # 새로운 문단 시작
                if is_paragraph_start:
                    improved_lines.append('')  # 빈 줄 추가
                improved_lines.append(line.strip())
        else:
            improved_lines.append(line.strip())
    
    return '\n'.join(improved_lines)

def optimize_for_tts(text):
    """TTS(음성 합성) 최적화 처리"""
    import re
    
    # 숫자를 한글로 변환 (간단한 케이스만)
    number_to_korean = {
        '1': '일', '2': '이', '3': '삼', '4': '사', '5': '오',
        '6': '육', '7': '칠', '8': '팔', '9': '구', '0': '영'
    }
    
    # 단순 숫자 변환 (1-9, 10-99)
    def convert_simple_numbers(match):
        num = match.group()
        if len(num) == 1:
            return number_to_korean.get(num, num)
        elif len(num) == 2:
            tens = int(num[0])
            ones = int(num[1])
            result = ''
            if tens > 1:
                result += number_to_korean[str(tens)] + '십'
            elif tens == 1:
                result += '십'
            if ones > 0:
                result += number_to_korean[str(ones)]
            return result
        return num
    
    # 1-99까지 숫자 변환
    text = re.sub(r'\b([1-9]|[1-9][0-9])\b', convert_simple_numbers, text)
    
    # 영어 단어 발음 표기 (자주 나오는 단어들)
    english_pronunciation = {
        'AI': '에이 아이',
        'IT': '아이 티',
        'CEO': '씨 이 오',
        'PDF': '피 디 에프',
        'PC': '피씨',
        'TV': '티비',
        'OK': '오케이',
        'NO': '노',
        'YES': '예스'
    }
    
    for eng, kor in english_pronunciation.items():
        text = re.sub(r'\b' + eng + r'\b', kor, text, flags=re.IGNORECASE)
    
    # 긴 문장에 쉼표 추가 (TTS 호흡 개선)
    sentences = re.split(r'[.!?]', text)
    improved_sentences = []
    
    for sentence in sentences:
        if len(sentence) > 50:  # 긴 문장인 경우
            # 적절한 지점에 쉼표 추가 (접속사, 부사 뒤)
            sentence = re.sub(r'(그리고|하지만|그러나|따라서|즉|또한|또|만약|만일)', r'\1,', sentence)
            sentence = re.sub(r'(때문에|경우에|상황에서)', r'\1,', sentence)
        improved_sentences.append(sentence)
    
    # 문장 재조합 (종결어미 복원)
    text = '. '.join([s.strip() for s in improved_sentences if s.strip()])
    if not text.endswith('.'):
        text += '.'
    
    return text

def basic_korean_text_cleanup(text):
    """기본 한글 텍스트 정리 (고급 후처리 실패시 fallback)"""
    import re
    
    # 기본적인 정리만 수행
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'\s+', ' ', text)
    text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
    
    return text

def process_image_easyocr(image_path, languages=['ko', 'en']):
    """EasyOCR로 이미지 처리"""
    try:
        import easyocr
        
        # EasyOCR 리더 생성 (GPU 비활성화)
        reader = easyocr.Reader(languages, gpu=False, verbose=False)
        
        # 이미지 처리 (한글 책 페이지 최적화 파라미터)
        results = reader.readtext(
            image_path, 
            detail=False,
            width_ths=0.9,      # 텍스트 폭 임계값 (한글 자간 최적화)
            height_ths=0.9,     # 텍스트 높이 임계값  
            paragraph=True,     # 문단 단위 인식 (책 페이지에 적합)
            x_ths=0.3,          # 텍스트 블록 간 수평 거리
            y_ths=0.3           # 텍스트 블록 간 수직 거리
        )
        
        # 결과 변환 (detail=False 모드)
        extracted_results = []
        full_text_parts = []
        
        # detail=False일 때는 text만 반환됨
        for text in results:
            if text.strip():  # 빈 텍스트가 아닌 경우만 포함
                extracted_results.append({
                    'text': text.strip(),
                    'confidence': 1.0,  # detail=False에서는 신뢰도 정보 없음
                    'bbox': []  # bbox 정보 없음
                })
                full_text_parts.append(text.strip())
        
        full_text = '\n'.join(full_text_parts)  # 웹 버전과 동일하게 줄바꿈으로 구분
        
        # 고도화된 한글 텍스트 후처리 적용
        cleaned_text = advanced_korean_text_processor(full_text)
        
        return {
            'success': True,
            'text': cleaned_text,
            'details': extracted_results,
            'total_blocks': len(extracted_results),
            'engine': 'easyocr',
            'execution_time': 0  # 추후 추가 가능
        }
        
    except ImportError as e:
        return {
            'success': False, 
            'error': f'EasyOCR 모듈을 찾을 수 없습니다: {e}',
            'engine': 'easyocr'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'EasyOCR 처리 실패: {e}',
            'engine': 'easyocr'
        }

def main():
    """메인 실행 함수"""
    if len(sys.argv) < 2:
        result = {
            'success': False,
            'error': '사용법: python easyocr_worker.py <image_path> [languages]'
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)
    
    # 환경 설정
    if not setup_environment():
        result = {
            'success': False,
            'error': '환경 설정 실패'
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)
    
    # 인자 파싱
    image_path = sys.argv[1]
    languages = ['ko', 'en']
    
    if len(sys.argv) > 2:
        lang_arg = sys.argv[2]
        # 다양한 구분자 처리: '+', ',', 또는 공백
        if '+' in lang_arg:
            languages = [lang.strip() for lang in lang_arg.split('+')]
        elif ',' in lang_arg:
            languages = [lang.strip() for lang in lang_arg.split(',')]
        else:
            languages = [lang_arg]
    
    # 이미지 파일 존재 확인
    if not Path(image_path).exists():
        result = {
            'success': False,
            'error': f'이미지 파일을 찾을 수 없습니다: {image_path}'
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)
    
    # EasyOCR 처리 실행
    start_time = time.time()
    result = process_image_easyocr(image_path, languages)
    end_time = time.time()
    
    # 실행 시간 추가
    if result.get('success'):
        result['execution_time'] = round(end_time - start_time, 3)
    
    # JSON 결과 출력
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()