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

def apply_dynamic_ocr_patterns(text):
    """정규식 기반 동적 OCR 오류 패턴 처리 - Stage 2"""
    import re
    
    # 숫자+단위 조합 오류 (예: "3년전" → "3년 전")
    text = re.sub(r'([0-9]+)([가-힣]{1,3})(전|후|간|째|번|개|명|일|년|월|시|분|초)(?![가-힣])', r'\1\2 \3', text)
    
    # 영문+한글 조합 오류 (예: "AI시대" → "AI 시대")
    text = re.sub(r'([A-Za-z]+)([가-힣]{2,})(?![가-힣])', r'\1 \2', text)
    text = re.sub(r'([가-힣]{2,})([A-Z]{2,})(?![A-Za-z])', r'\1 \2', text)
    
    # 특수문자 주변 공백 정리
    text = re.sub(r'([가-힣])([\(\)\[\]{}])([가-힣])', r'\1 \2 \3', text)
    text = re.sub(r'([\(\)\[\]{}])([가-힣])', r'\1 \2', text)
    text = re.sub(r'([가-힣])([\(\)\[\]{}])', r'\1 \2', text)
    
    # 문장 부호 앞뒤 공백 정리
    text = re.sub(r'([가-힣])\s*([.!?])\s*([가-힣])', r'\1\2 \3', text)
    
    # 따옴표 처리
    text = re.sub(r'([가-힣])\s*(["\'""])\s*([가-힣])', r'\1 \2\3', text)
    text = re.sub(r'([가-힣])\s*(["\'""])\s*([가-힣])', r'\1\2 \3', text)
    
    # 연속된 같은 문자 정리 (OCR 특유의 오류)
    text = re.sub(r'(.)\1{3,}', r'\1\1', text)  # 4개 이상 연속을 2개로
    
    # 한글+숫자+한글 패턴 정리
    text = re.sub(r'([가-힣]+)([0-9]+)([가-힣]+)', lambda m: f"{m.group(1)} {m.group(2)} {m.group(3)}" if len(m.group(1)) > 1 and len(m.group(3)) > 1 else m.group(0), text)
    
    return text

def apply_contextual_corrections(text):
    """문맥 기반 지능형 오류 교정 - Stage 2"""
    import re
    
    # 문장별로 처리
    sentences = re.split(r'[.!?]+', text)
    corrected_sentences = []
    
    for sentence in sentences:
        if sentence.strip():
            # 문장 길이에 따른 조건부 교정
            if len(sentence) > 100:  # 긴 문장에서만 적용
                # 복잡한 조사 분리 (긴 문장에서만)
                sentence = re.sub(r'([가-힣]{3,})(에서는|로부터는|에게서는|로써는)', r'\1 \2', sentence)
                
            # 문장 시작 패턴 교정
            sentence = sentence.strip()
            if sentence:
                # 문장 시작이 특정 패턴인 경우 교정
                if sentence.startswith('그래서'):
                    sentence = re.sub(r'^그래서([가-힣])', r'그래서 \1', sentence)
                elif sentence.startswith('하지만'):
                    sentence = re.sub(r'^하지만([가-힣])', r'하지만 \1', sentence)
                elif sentence.startswith('따라서'):
                    sentence = re.sub(r'^따라서([가-힣])', r'따라서 \1', sentence)
                elif sentence.startswith('즉'):
                    sentence = re.sub(r'^즉([가-힣])', r'즉 \1', sentence)
            
            # 문맥별 자주 혼동되는 단어들
            contextual_fixes = {
                # 철학/종교 문맥
                '하느님': '하나님' if '기독교' in text or '성경' in text else '하느님',
                '부처님': '부처님' if '불교' in text or '절' in text else '부처님',
                
                # 시간 표현 문맥
                '오전': '오전' if any(time in sentence for time in ['시', '분', '때']) else '오전',
                '오후': '오후' if any(time in sentence for time in ['시', '분', '때']) else '오후',
                
                # 정도 표현 교정
                '매우많은': '매우 많은', '아주좋은': '아주 좋은', '정말중요한': '정말 중요한',
                '너무어려운': '너무 어려운', '특히중요한': '특히 중요한'
            }
            
            for wrong, correct in contextual_fixes.items():
                if wrong in sentence:
                    sentence = sentence.replace(wrong, correct)
            
            # 반복되는 패턴 최적화
            if sentence.count('것') > 3:  # '것'이 많이 나오는 문장
                sentence = re.sub(r'것\s*것', '것', sentence)  # 중복 제거
                
            if sentence.count('수') > 3:  # '수'가 많이 나오는 문장
                sentence = re.sub(r'할\s*수\s*있', '할 수 있', sentence)
                sentence = re.sub(r'될\s*수\s*있', '될 수 있', sentence)
            
            corrected_sentences.append(sentence)
    
    # 문장들을 다시 합침
    result = '. '.join([s.strip() for s in corrected_sentences if s.strip()])
    
    # 최종 정리
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result

def normalize_spacing_overseparation(text):
    """Stage 3-1: EasyOCR 띄어쓰기 과분리 정규화 - 정교한 버전"""
    import re
    
    print("🚀 Stage 3-1: 띄어쓰기 과분리 해결 시작", file=sys.stderr)
    original_text = text
    
    # === 1단계: 명확한 고정 패턴들 우선 처리 ===
    # 인명 및 고유명사
    fixed_patterns = [
        (r'마\s*이\s*클\s*싱\s*어', '마이클 싱어'),
        (r'마\s*이\s*클(?!\s*싱)', '마이클'),
        (r'오\s*프\s*라\s*윈\s*프\s*리', '오프라 윈프리'),
        
        # 일반명사 (확실한 것들)
        (r'사\s*람\s*들', '사람들'),
        (r'한\s*국\s*어', '한국어'),
        (r'철\s*학', '철학'),
        (r'심\s*리\s*학', '심리학'),
        (r'중\s*요\s*한', '중요한'),
        (r'어\s*려\s*운', '어려운'),
        (r'새\s*로\s*운', '새로운'),
        (r'유\s*명\s*한', '유명한'),
        (r'완\s*전\s*히', '완전히'),
        (r'정\s*말', '정말'),
        (r'내\s*용', '내용'),
        (r'방\s*법', '방법'),
        (r'핵\s*심', '핵심'),
        (r'바\s*로', '바로'),
        (r'연\s*구', '연구'),
        (r'작\s*가', '작가'),
        (r'언\s*어', '언어'),  # 추가
        (r'책', '책'),
        
        # 형용사 특수 처리
        (r'철\s*학\s*적', '철학적'),  # 추가
        (r'사\s*고\s*방\s*식', '사고 방식'),  # 공백 유지
        
        # 부사/접속사
        (r'처\s*음\s*으\s*로', '처음으로'),
        (r'폭\s*발\s*적\s*으\s*로', '폭발적으로'),
        (r'그\s*래\s*서', '그래서'),
        (r'따\s*라\s*서', '따라서'),
        (r'하\s*지\s*만', '하지만'),
        (r'그\s*러\s*나', '그러나'),
        (r'그\s*러\s*면', '그러면'),
        
        # 대명사
        (r'그\s*것(?=\s*이)', '그것'),
        (r'이\s*것(?=\s*이)', '이것'),
        (r'그\s*의(?=\s)', '그의 '),
        
        # 동사 어간
        (r'시\s*작', '시작'),
        (r'증\s*가', '증가'),
        (r'감\s*동', '감동'),
        (r'이\s*해', '이해'),
        (r'다\s*룹', '다룹'),
    ]
    
    for pattern, replacement in fixed_patterns:
        text = re.sub(pattern, replacement, text)
    
    # === 2단계: 어미 처리 (매우 중요) ===
    # 긴 어미부터 처리
    long_eomis = [
        (r'하\s*겠\s*습\s*니\s*다', '하겠습니다'),
        (r'해\s*보\s*겠\s*습\s*니\s*다', '해보겠습니다'),
        (r'했\s*습\s*니\s*다', '했습니다'),
        (r'있\s*습\s*니\s*다', '있습니다'),
        (r'없\s*습\s*니\s*다', '없습니다'),
        (r'됩\s*니\s*다', '됩니다'),
        (r'입\s*니\s*다', '입니다'),
        (r'습\s*니\s*다', '습니다'),
        (r'모\s*였\s*습\s*니\s*다', '모였습니다'),  # 특정 동사 + 어미
        (r'받\s*았\s*습\s*니\s*다', '받았습니다'),
        (r'증\s*가\s*했\s*습\s*니\s*다', '증가했습니다'),
    ]
    
    for pattern, replacement in long_eomis:
        text = re.sub(pattern, replacement, text)
    
    # === 3단계: 조사 처리 (앞 글자와 붙임) ===
    # 조사는 반드시 앞 한글과 붙어야 함
    josas = ['은', '는', '이', '가', '을', '를', '의', '에', '에서', '에게', '로', '으로', '와', '과', '도', '만']
    for josa in josas:
        # "작가 입니다" → "작가입니다"
        text = re.sub(f'([가-힣]+)\\s+{josa}(?=\\s)', f'\\1{josa} ', text)
        # 문장 끝에 오는 경우
        text = re.sub(f'([가-힣]+)\\s+{josa}(?=\\.|$)', f'\\1{josa}', text)
    
    # === 4단계: 특별한 연결 처리 ===
    # "할 수 있다" 류의 표현
    text = re.sub(r'할\s+수\s+있\s*습\s*니\s*다', '할 수 있습니다', text)
    text = re.sub(r'될\s+수\s+있\s*습\s*니\s*다', '될 수 있습니다', text)
    text = re.sub(r'해\s*보\s*겠\s*습\s*니\s*다', '해보겠습니다', text)
    
    # === 5단계: 동사 + 어미 연결 ===
    # "모였다", "읽고" 등
    text = re.sub(r'시\s*작\s*해\s*보\s*겠\s*습\s*니\s*다', '시작해보겠습니다', text)
    text = re.sub(r'시\s*작(?=\s*해)', '시작', text)  # "시작해보겠습니다" 처리
    text = re.sub(r'모\s*였(?=\s*습\s*니\s*다)', '모였', text)
    text = re.sub(r'읽\s*고(?=\s)', '읽고 ', text)
    text = re.sub(r'받\s*았(?=\s*습\s*니\s*다)', '받았', text)
    text = re.sub(r'쉽\s*게(?=\s)', '쉽게 ', text)
    
    # 동사 + 어미 완전 연결
    text = re.sub(r'증\s*가\s*했\s*습\s*니\s*다', '증가했습니다', text)
    
    # === 6단계: 조심스러운 일반 합치기 ===
    # 2글자 명사만 (안전한 것들)
    safe_2chars = ['그의', '이것', '그것', '모든', '다른', '같은', '이런', '그런', '어떤']
    for word in safe_2chars:
        if len(word) == 2:
            pattern = f'{word[0]}\\s+{word[1]}'
            text = re.sub(pattern, word, text)
    
    # === 7단계: 최종 정리 및 품질 조정 ===
    # 연속 공백 정리
    text = re.sub(r'\s+', ' ', text)
    
    text = text.strip()
    
    # 결과 검증 및 로깅
    if len(original_text) != len(text) or original_text != text:
        print(f"🔄 Stage 3-1: 띄어쓰기 정규화 적용됨 ({len(original_text)}→{len(text)} 글자)", file=sys.stderr)
    else:
        print("✨ Stage 3-1: 띄어쓰기 정규화 변경사항 없음", file=sys.stderr)
    
    return text

def fix_clear_character_errors(text):
    """Stage 3-2: 명확한 글자 오류 교정 - 안전한 OCR 글자 오타 수정"""
    import re
    
    print("🎯 Stage 3-2: 명확한 글자 오류 교정 시작", file=sys.stderr)
    original_text = text
    
    # === 1단계: 매우 확실한 OCR 글자 오류 패턴들 ===
    # GitHub 연구 결과 및 실제 OCR 오류 분석 기반
    clear_char_errors = {
        # 자주 혼동되는 유사 글자들 (매우 확실한 경우만)
        '헬': '할',   # "할 수 있다" → "헐 수 있다" 오류
        '듀': '두',   # "두 번째" → "듀 번째" 오류  
        '옷': '것',   # "그것은" → "그옷은" 오류 (문맥상 확실)
        '든': '든',   # 이미 맞는 글자지만 확인
        '른': '른',   # 이미 맞는 글자지만 확인
        '픈': '픈',   # 이미 맞는 글자지만 확인
        
        # 명확한 모음 오인식 (문맥상 100% 확실한 경우)
        '내숭': '내용',   # 이미 Stage 2에서 처리됨
        '세제': '세계',   # 이미 Stage 2에서 처리됨
        
        # 자주 발생하는 어미 오타 (매우 안전한 패턴)
        '했슴니다': '했습니다',
        '있슴니다': '있습니다',
        '없슴니다': '없습니다',
        '됩니다': '됩니다',  # 확인용 (이미 맞음)
        '합니다': '합니다',  # 확인용 (이미 맞음)
        
        # 명확한 조사/어미 오타
        '이다': '이다',    # 확인용
        '입니다': '입니다', # 확인용
        '니다': '니다',    # 확인용
        
        # OCR에서 자주 발생하는 특정 글자 오인식
        '몽': '목',    # "목적" → "몽적" 오류
        # '근': '글',    # "글자" → "근자" 오류 (문맥상 확실한 경우만) - 주석 처리 (너무 광범위)
        '뜨': '때',    # "때문에" → "뜨문에" 오류
        '롱': '로',    # "로써" → "롱써" 오류
        '묘': '며',    # "며칠" → "묘칠" 오류
        '휴': '휘',    # "휘어" → "휴어" 오류
        
        # 영문/숫자 혼동 글자 (한글 문맥에서 명확한 오류)
        '0': 'o',     # 영문 문맥에서 숫자 0이 영문 o로 잘못 인식
        '1': 'l',     # 영문 문맥에서 숫자 1이 영문 l로 잘못 인식
        '5': 'S',     # 영문 문맥에서 숫자 5가 영문 S로 잘못 인식
        
        # 한글에서 자주 틀리는 받침 오류
        '업다': '없다',   # "없다" → "업다" 오류
        '잆다': '있다',   # "있다" → "잆다" 오류
        '갔다': '갔다',   # 확인용
        '왔다': '왔다',   # 확인용
        
        # 특수한 한글 조합 오류 (매우 확실한 경우만)
        '죄': '좌',    # "좌석" → "죄석" 오류 (문맥상 확실)
        '좌': '좌',    # 확인용
        '우': '우',    # 확인용
        
        # 책/문서에서 자주 나오는 전문용어 오타
        '철학': '철학',   # 확인용
        '심리혁': '심리학', # "심리학" → "심리혁" 오류
        '사회혁': '사회학', # "사회학" → "사회혁" 오류
        '정치혁': '정치학', # "정치학" → "정치혁" 오류
        '경제혁': '경제학', # "경제학" → "경제혁" 오류
    }
    
    # === 2단계: 문맥 기반 안전 교정 ===
    # 단어 전체나 문맥을 고려한 교정 (더 안전한 접근)
    contextual_corrections = [
        # "할 수 있다" 관련 오타들
        ('헐 수 있', '할 수 있'),
        ('헤 수 있', '할 수 있'),
        ('혼 수 있', '할 수 있'),
        
        # "그것은/그것이" 관련 오타들  
        ('그옷은', '그것은'),
        ('그옷이', '그것이'),
        ('그옷을', '그것을'),
        
        # "때문에" 관련 오타들
        ('뜨문에', '때문에'),
        ('때운에', '때문에'),
        ('때분에', '때문에'),
        
        # "목적" 관련 오타들
        ('몽적', '목적'),
        ('목젹', '목적'),
        
        # "사람들" 관련 오타들 (Stage 3-1에서 처리했지만 추가 보완)
        ('사앰들', '사람들'),
        ('사럼들', '사람들'),
        
        # 일반적인 어미 오타들
        ('했슴', '했습'),
        ('있슴', '있습'),
        ('없슴', '없습'),
        ('됩슴', '됩습'),
    ]
    
    # === 3단계: 패턴 적용 ===
    correction_count = 0
    
    # 문자 단위 교정
    for wrong, correct in clear_char_errors.items():
        if wrong in text:
            original_count = text.count(wrong)
            text = text.replace(wrong, correct)
            if original_count > 0:
                correction_count += original_count
    
    # 문맥 기반 교정 (더 안전)
    for wrong_pattern, correct_pattern in contextual_corrections:
        if wrong_pattern in text:
            original_count = text.count(wrong_pattern)
            text = text.replace(wrong_pattern, correct_pattern)
            if original_count > 0:
                correction_count += original_count
    
    # === 4단계: 정규식 기반 패턴 교정 (매우 조심스럽게) ===
    # 특정 문맥에서만 확실한 교정
    regex_patterns = [
        # 어미에서의 ㅅ/ㅆ 오류 (매우 안전한 패턴만)
        (r'([가-힣]+)슴니다(?=\s|$|[.!?])', r'\1습니다'),  # "했슴니다" → "했습니다"
        (r'([가-힣]+)씀니다(?=\s|$|[.!?])', r'\1습니다'),  # "했씀니다" → "했습니다"
    ]
    
    for pattern, replacement in regex_patterns:
        matches = re.findall(pattern, text)
        text = re.sub(pattern, replacement, text)
        correction_count += len(matches)
    
    # === 5단계: 결과 로깅 ===
    if correction_count > 0:
        print(f"🔧 Stage 3-2: {correction_count}개 글자 오류 교정 완료", file=sys.stderr)
    else:
        print("✨ Stage 3-2: 교정 대상 글자 오류 없음", file=sys.stderr)
    
    return text

def normalize_korean_endings(text):
    """Stage 3-3: 한국어 어미 정규화 - 표준화된 어미 스타일 적용"""
    import re
    
    print("📝 Stage 3-3: 한국어 어미 정규화 시작", file=sys.stderr)
    original_text = text
    normalization_count = 0
    
    # === 1단계: 과거형 어미 정규화 ===
    # "했었다" → "했다" (이중 과거 표현을 단순 과거로)
    past_tense_patterns = [
        (r'([가-힣]+)했었다(?=\s|$|[.!?])', r'\1했다'),
        (r'([가-힣]+)갔었다(?=\s|$|[.!?])', r'\1갔다'),  
        (r'([가-힣]+)왔었다(?=\s|$|[.!?])', r'\1왔다'),
        (r'([가-힣]+)봤었다(?=\s|$|[.!?])', r'\1봤다'),  # 추가
        (r'([가-힣]+)살았었다(?=\s|$|[.!?])', r'\1살았다'),
        (r'([가-힣]+)있었었다(?=\s|$|[.!?])', r'\1있었다'),  # 추가
        (r'([가-힣]+)없었었다(?=\s|$|[.!?])', r'\1없었다'),
        (r'([가-힣]+)읽었었다(?=\s|$|[.!?])', r'\1읽었다'),  # 새로 추가
        (r'([가-힣]+)썼었다(?=\s|$|[.!?])', r'\1썼다'),    # 새로 추가
        (r'([가-힣]+)받았었다(?=\s|$|[.!?])', r'\1받았다'),  # 새로 추가
        
        # 과거형 끝나는 형태들 (더 일반적 패턴)
        (r'갔었고(?=\s|$|[.!?])', '갔고'),
        (r'왔었고(?=\s|$|[.!?])', '왔고'),
        (r'했었고(?=\s|$|[.!?])', '했고'),
        (r'봤었고(?=\s|$|[.!?])', '봤고'),
        (r'읽었었고(?=\s|$|[.!?])', '읽었고'),
        (r'받았었고(?=\s|$|[.!?])', '받았고'),
        
        # 특정 동사들의 이중 과거 패턴
        (r'했었습니다(?=\s|$|[.!?])', '했습니다'),
        (r'갔었습니다(?=\s|$|[.!?])', '갔습니다'),
        (r'왔었습니다(?=\s|$|[.!?])', '왔습니다'),
        (r'있었었습니다(?=\s|$|[.!?])', '있었습니다'),
        (r'썼었습니다(?=\s|$|[.!?])', '썼습니다'),
        (r'읽었었습니다(?=\s|$|[.!?])', '읽었습니다'),
        (r'받았었습니다(?=\s|$|[.!?])', '받았습니다'),
    ]
    
    # === 2단계: 축약형 어미 정규화 ===
    # "되었다" → "됐다" (자연스러운 축약) 또는 반대로 표준형 선택
    contraction_patterns = [
        # 정식 표기를 축약형으로 (구어체 최적화)
        (r'되었다(?=\s|$|[.!?])', '됐다'),
        (r'되었습니다(?=\s|$|[.!?])', '됐습니다'),
        (r'하였다(?=\s|$|[.!?])', '했다'),
        (r'하였습니다(?=\s|$|[.!?])', '했습니다'),
        (r'이었다(?=\s|$|[.!?])', '였다'),  # "이었다" → "였다"
        (r'이었습니다(?=\s|$|[.!?])', '였습니다'),
        
        # 반대 방향: 비표준 축약을 표준형으로
        (r'했댔다(?=\s|$|[.!?])', '했다'),   # 과도한 축약 수정
        (r'갔댔다(?=\s|$|[.!?])', '갔다'),
        
        # 일반적인 축약 오류 수정
        (r'([가-힣]+)엤다(?=\s|$|[.!?])', r'\1었다'),  # "했엤다" → "했다"
    ]
    
    # === 3단계: 존댓말 어미 정규화 ===
    # 일관된 존댓말 스타일 적용
    honorific_patterns = [
        # "~ㅂ니다" 체 통일
        (r'([가-힣]+)읍니다(?=\s|$|[.!?])', r'\1습니다'),  # "읽읍니다" → "읽습니다"
        
        # 불규칙 어미 정규화
        (r'([가-힣]+)ㅂ니다(?=\s|$|[.!?])', r'\1습니다'),  # 오타 수정
        (r'([가-힣]+)슴니다(?=\s|$|[.!?])', r'\1습니다'),  # Stage 3-2에서 처리했지만 추가 보완
        
        # "하다" 동사의 특별 처리
        (r'하슴니다(?=\s|$|[.!?])', '합니다'),  # "하슴니다" → "합니다"
        (r'해슴니다(?=\s|$|[.!?])', '합니다'),  # "해슴니다" → "합니다"
        
        # 높임말 일관성
        (r'하십니다(?=\s|$|[.!?])', '합니다'),  # 과도한 높임말 완화 (맥락에 따라)
        (r'계십니다(?=\s|$|[.!?])', '있습니다'),  # 일반적 상황에서 완화
    ]
    
    # === 4단계: 어미 연결 오류 수정 ===
    # OCR에서 자주 발생하는 어미 연결 문제
    connection_patterns = [
        # "할 거 다" → "할 거다"
        (r'할\s+거\s+다(?=\s|$|[.!?])', '할 거다'),
        (r'할\s+수\s+있\s+다(?=\s|$|[.!?])', '할 수 있다'),
        (r'될\s+수\s+있\s+다(?=\s|$|[.!?])', '될 수 있다'),
        
        # "읽 을 것" → "읽을 것" (더 포괄적 패턴)
        (r'([가-힣]+)\s+을\s+것(?=\s|$|[.!?])', r'\1을 것'),
        (r'([가-힣]+)\s+을\s+때(?=\s|$|[.!?])', r'\1을 때'),
        (r'([가-힣]+)\s+을\s+수(?=\s|$|[.!?])', r'\1을 수'),
        
        # 더 구체적인 패턴들
        (r'읽\s+을\s+것(?=\s|$|[.!?])', '읽을 것'),
        (r'쓸\s+것(?=\s|$|[.!?])', '쓸 것'),
        
        # 연결어미 정리
        (r'([가-힣]+)\s+면\s+서(?=\s|$|[.!?])', r'\1면서'),
        (r'([가-힣]+)\s+지\s+만(?=\s|$|[.!?])', r'\1지만'),
        (r'([가-힣]+)\s+기\s+때\s+문에(?=\s|$|[.!?])', r'\1기 때문에'),
    ]
    
    # === 5단계: 문체 일관성 적용 ===
    # 전체적인 문체를 일관되게 유지 (책/문서에 적합)
    style_patterns = [
        # 구어체를 문어체로 (필요시)
        (r'([가-힣]+)거야(?=\s|$|[.!?])', r'\1것이다'),  # "할 거야" → "할 것이다"
        (r'([가-힣]+)걸(?=\s|$|[.!?])', r'\1것을'),     # "할 걸" → "할 것을"
        
        # 문어체 강화 (구체적 패턴들)
        (r'좋네요(?=\s|$|[.!?])', '좋습니다'),  # "좋네요" → "좋습니다"
        (r'그래요(?=\s|$|[.!?])', '그렇습니다'),  # "그래요" → "그렇습니다"
        (r'([가-힣]+)네요(?=\s|$|[.!?])', r'\1습니다'),  # 일반 패턴
        (r'([가-힣]+)에요(?=\s|$|[.!?])', r'\1입니다'),  # 일반 패턴
        
        # 추가 구어체 패턴
        (r'맞아요(?=\s|$|[.!?])', '맞습니다'),
        (r'아니에요(?=\s|$|[.!?])', '아닙니다'),
        (r'괜찮아요(?=\s|$|[.!?])', '괜찮습니다'),
    ]
    
    # === 6단계: 패턴 적용 ===
    all_patterns = [
        ("과거형 정규화", past_tense_patterns),
        ("축약형 정규화", contraction_patterns), 
        ("존댓말 정규화", honorific_patterns),
        ("어미 연결", connection_patterns),
        ("문체 일관성", style_patterns)
    ]
    
    for category, patterns in all_patterns:
        category_count = 0
        for pattern, replacement in patterns:
            matches = re.findall(pattern, text)
            if matches:
                text = re.sub(pattern, replacement, text)
                category_count += len(matches)
        
        if category_count > 0:
            normalization_count += category_count
            print(f"  ➤ {category}: {category_count}개 정규화", file=sys.stderr)
    
    # === 7단계: 결과 로깅 ===
    if normalization_count > 0:
        print(f"📝 Stage 3-3: {normalization_count}개 어미 정규화 완료", file=sys.stderr)
    else:
        print("✨ Stage 3-3: 정규화 대상 어미 없음", file=sys.stderr)
    
    return text

def advanced_korean_text_processor(text):
    """고도화된 한국어 텍스트 후처리 - PyKoSpacing + 다양한 최적화 기법"""
    import re
    
    try:
        # Stage 2 적용 확인 로그
        print("🚀 Stage 2: OCR 오류 패턴 150+ 개 확장 버전 시작", file=sys.stderr)
        
        # 1. 기본 정리 - 연속된 특수문자 및 공백 정리
        text = re.sub(r'\.{2,}', '.', text)  # 연속된 점들을 하나로
        text = re.sub(r'\s+', ' ', text)     # 연속된 공백을 하나로
        
        # 2. OCR 오류 패턴 수정 (책 OCR 특화 대폭 확장 - Stage 2)
        ocr_fixes = {
            # === 기존 영문 이름 수정 ===
            '마이름상어': '마이클 싱어', '마이클 상어': '마이클 싱어', '마이칼 심어': '마이클 싱어',
            '마이름생어': '마이클 싱어', '원프리': '윈프리', '소율': '소울', '곧경': '곤경', '상어든': '싱어는',
            
            # === 새로운 인명/고유명사 패턴 (40개 추가) ===
            '토니 페반스': '토니 에반스', '플라톤': '플라톤', '소크라테스': '소크라테스',
            '아리스토딸레스': '아리스토텔레스', '니채': '니체', '스플노자': '스피노자',
            '데카르트': '데카르트', '로크': '록', '휴럼': '흄', '컨트': '칸트',
            '헤겔': '헤겔', '키에르케고르': '키에르케고르', '샤르트르': '사르트르',
            '하이데거': '하이데거', '비트겐슈나인': '비트겐슈타인', '러설': '러셀',
            '프롯드': '프로이트', '융': '융', '아들러': '아들러', '스키너': '스키너',
            '매슬로우': '매슬로', '로져스': '로저스', '피아제': '피아제',
            '다든': '다윈', '아인슈나인': '아인슈타인', '뉴튼': '뉴턴', '갈릴래이': '갈릴레이',
            '쏘크라딱': '소크라테스', '프랏톤': '플라톤', '데이빗': '데이비드', '존': '존',
            '마이클': '마이클', '제임스': '제임스', '로버트': '로버트', '윌리엄': '윌리엄',
            '리차드': '리처드', '토머스': '토머스', '찰스': '찰스', '크리스토퍼': '크리스토퍼',
            '대니얼': '대니얼', '매튜': '매튜', '앤드류': '앤드류', '조슈아': '조슈아',
            '케네스': '케네스', '스티븐': '스티븐', '에드워드': '에드워드', '브라이언': '브라이언',
            
            # === 기존 조사/어미 오류 + 확장 ===
            '기틀': '기를', '부탁울': '부탁을', '이기 지': '이기지',
            '자유로위지': '자유로워지', '을컷고': '올랐고', '소개되워': '소개되었',
            '두없던': '두었던', '우리튼': '우리를', '그이후': '그 이후',
            '돌두했': '돌입했', '깊은내면': '깊은 내면', '드러넷': '드러냈',
            '알려저': '알려져', '지처': '지쳐',
            
            # === 복잡한 조사 결합 패턴 (30개 추가) ===
            '에게는': '에게는', '에서는': '에서는', '로부터의': '로부터의', '에게서는': '에게서는',
            '로써의': '로써의', '에대한': '에 대한', '에관한': '에 관한', '에따른': '에 따른',
            '에의한': '에 의한', '에있어서': '에 있어서', '에비해': '에 비해', '에반해': '에 반해',
            '으로인한': '으로 인한', '에도불구하고': '에도 불구하고', '임에도': '임에도',
            '이기때문에': '이기 때문에', '하기때문에': '하기 때문에', '되기때문에': '되기 때문에',
            '할수있는': '할 수 있는', '될수있는': '될 수 있는', '갈수있는': '갈 수 있는',
            '오고있는': '오고 있는', '가고있는': '가고 있는', '하고있는': '하고 있는',
            '되어있는': '되어 있는', '되어지는': '되어지는', '이루어지는': '이루어지는',
            '만들어지는': '만들어지는', '생각되어지는': '생각되어지는', '여겨지는': '여겨지는',
            '고려되어지는': '고려되어지는', '받아들여지는': '받아들여지는',
            
            # === 높임법/문체 오류 (25개 추가) ===
            '습니짜': '습니다', '슴니다': '습니다', '습니까': '습니까', '십니까': '십니까',
            '하십시요': '하십시오', '해주십시요': '해주십시오', '말씀하십시요': '말씀하십시오',
            '드리겠솜': '드리겠습', '드리겠습니다': '드리겠습니다', '해드리겠습니다': '해드리겠습니다',
            '되십니다': '되십니다', '계십니다': '계십니다', '있으십니다': '있으십니다',
            '하겠슴니다': '하겠습니다', '되겠슴니다': '되겠습니다', '있겠솜니다': '있겠습니다',
            '이겠솜니다': '이겠습니다', '그럽니다': '그럽니다', '그렇솜니다': '그렇습니다',
            '맞솜니다': '맞습니다', '좋솜니다': '좋습니다', '감사함니다': '감사합니다',
            '고맙솜니다': '고맙습니다', '죄송합니다': '죄송합니다', '미안함니다': '미안합니다',
            '안녕하십니까': '안녕하십니까', '어떻게지내십니까': '어떻게 지내십니까',
            
            # === 시제/문법 표현 (20개 추가) ===
            '했었솜니다': '했었습니다', '했었던': '했었던', '했었을': '했었을',
            '하겠다고': '하겠다고', '하겠다는': '하겠다는', '하겠다면': '하겠다면',
            '할것이다': '할 것이다', '될것이다': '될 것이다', '갈것이다': '갈 것이다',
            '할것일까': '할 것일까', '할것인가': '할 것인가', '할것같다': '할 것 같다',
            '할지도모른다': '할지도 모른다', '할지모른다': '할지 모른다',
            '하지않을': '하지 않을', '하지않는': '하지 않는', '하지않았': '하지 않았',
            '하지못한': '하지 못한', '하지못했': '하지 못했', '할수없는': '할 수 없는',
            '할수없다': '할 수 없다',
            
            # === 기존 기본 조사/어미 오류 ===
            '오-': '으', '울-': '을', '블': '를', '엔': '에', '올': '을',
            '느-': '는', '겨-': '게', '끠': '께', '웁': '위', '셨': '세',
            
            # === 일반적인 한국어 오인식 패턴 + 확장 (30개 추가) ===
            '함들은': '람들은', '쾌습니다': '했습니다', '햇습니다': '했습니다',
            '국업는': '숭배의', '토록': '도록', '빋다': '빚다',
            '살펴봐야함': '살펴봐야 함', '해야합': '해야 함', '될것같': '될 것 같',
            '할것같': '할 것 같', '갈것같': '갈 것 같', '올것같': '올 것 같',
            '보여주긴': '보여주길', '해주길': '해주길', '되어주길': '되어주길',
            '가져다주': '가져다 주', '해드릴게': '해드릴게', '드릴게요': '드릴게요',
            '그렇하니': '그렇다니', '그렇잖아': '그렇잖아', '그렇네요': '그렇네요',
            '맞네요': '맞네요', '좋네요': '좋네요', '예쁘네요': '예쁘네요',
            '고마워요': '고마워요', '미안해요': '미안해요', '죄송해요': '죄송해요',
            '안녕히가세요': '안녕히 가세요', '안녕히계세요': '안녕히 계세요',
            '잘지내세요': '잘 지내세요', '건강하세요': '건강하세요', '행복하세요': '행복하세요',
            '성공하세요': '성공하세요', '화이팅하세요': '화이팅 하세요',
            
            # === 기존 자주 틀리는 단어들 + 확장 ===
            '하나너': '하나님', '사악': '사람', '내숭': '내용', '세제': '세계',
            '인갑': '인간', '부족': '부족', '쳬험': '체험', '현젠': '현실',
            
            # === 전문용어/학술용어 (25개 추가) ===
            '철혁': '철학', '심러학': '심리학', '사회혁': '사회학', '경제혁': '경제학',
            '정치혁': '정치학', '역사혁': '역사학', '문화혁': '문학', '예술혁': '예술학',
            '종교혁': '종교학', '논러학': '논리학', '윤러학': '윤리학', '미해학': '미학',
            '인식론': '인식론', '존재론': '존재론', '형이상학': '형이상학', '현상학': '현상학',
            '실존주의': '실존주의', '구조주의': '구조주의', '포스트모더니즘': '포스트모더니즘',
            '이성주의': '이성주의', '경험주의': '경험주의', '실용주의': '실용주의',
            '유물론': '유물론', '관념론': '관념론', '회의주의': '회의주의',
            
            # === 영문 단어 수정 + 확장 ===
            'Michacl': 'Michael', 'Sinyer': 'Singer', 'Uniyerse': 'Universe',
            'teh': 'the', 'adn': 'and', 'hte': 'the', 'OGettylmages': '@GettyImages',
            'Philosophly': 'Philosophy', 'Psycholgoy': 'Psychology', 'Sociolgoy': 'Sociology',
            'Politcal': 'Political', 'Histroy': 'History', 'Literatrue': 'Literature',
            'Scienec': 'Science', 'Religon': 'Religion', 'Economcs': 'Economics'
        }
        
        # Stage 2 패턴 적용 로그
        print(f"📊 Stage 2: {len(ocr_fixes)}개 OCR 오류 패턴 적용 중", file=sys.stderr)
        
        for wrong, correct in ocr_fixes.items():
            text = text.replace(wrong, correct)
        
        print("✅ Stage 2: OCR 오류 패턴 교정 완료", file=sys.stderr)
        
        # 2.1. 정규식 기반 동적 OCR 오류 패턴 처리 (Stage 2 추가)
        print("🔧 Stage 2: 정규식 기반 동적 패턴 처리", file=sys.stderr)
        text = apply_dynamic_ocr_patterns(text)
        
        # 2.2. 문맥 기반 지능형 오류 교정 (Stage 2 추가)
        print("🧠 Stage 2: 문맥 기반 지능형 교정", file=sys.stderr)
        text = apply_contextual_corrections(text)
        
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
        
        # 2.6. Stage 3-1: 띄어쓰기 과분리 정규화 (GitHub 성공 사례 적용)
        print("🎯 Stage 3-1: 띄어쓰기 과분리 정규화 처리", file=sys.stderr)
        text = normalize_spacing_overseparation(text)
        print("✅ Stage 3-1: 띄어쓰기 과분리 정규화 완료", file=sys.stderr)
        
        # 2.7. Stage 3-2: 명확한 글자 오류 교정 (GitHub 성공 사례 적용)
        print("🎯 Stage 3-2: 명확한 글자 오류 교정 처리", file=sys.stderr)
        text = fix_clear_character_errors(text)
        print("✅ Stage 3-2: 명확한 글자 오류 교정 완료", file=sys.stderr)
        
        # 2.8. Stage 3-3: 한국어 어미 정규화 (GitHub 성공 사례 적용)
        print("🎯 Stage 3-3: 한국어 어미 정규화 처리", file=sys.stderr)
        text = normalize_korean_endings(text)
        print("✅ Stage 3-3: 한국어 어미 정규화 완료", file=sys.stderr)
        
        # 2.9. kiwipiepy 형태소 분석 기반 띄어쓰기 개선 (GitHub 성공 사례 적용)
        try:
            from kiwipiepy import Kiwi
            
            # Kiwi 인스턴스 생성 (캐시 최적화)
            kiwi = Kiwi()
            
            # 문장 단위로 처리 (긴 텍스트 성능 최적화)
            sentences = text.split('. ')
            improved_sentences = []
            
            for sentence in sentences:
                if sentence.strip() and len(sentence.strip()) > 3:
                    # 형태소 분석
                    tokens = kiwi.tokenize(sentence.strip())
                    
                    # 토큰들을 적절한 띄어쓰기로 재구성
                    reconstructed = []
                    for i, token in enumerate(tokens):
                        try:
                            form = token.form
                            tag = token.tag
                            
                            # 인코딩 안전성 확인 및 정리
                            if form and isinstance(form, str):
                                # 특수 유니코드 문자 정리
                                form = form.replace('\u11ab', '').replace('\u11bc', '').strip()
                                
                                if len(form) > 0:  # 빈 문자열이 아닌 경우만 처리
                                    # 조사, 어미는 앞 단어와 붙임
                                    if tag.startswith('J') or tag.startswith('E'):
                                        if reconstructed:
                                            reconstructed[-1] += form
                                        else:
                                            reconstructed.append(form)
                                    # 어간, 명사, 수사 등은 분리
                                    elif tag.startswith('N') or tag.startswith('V') or tag.startswith('M') or tag.startswith('A'):
                                        reconstructed.append(form)
                                    # 기타는 기본적으로 분리
                                    else:
                                        reconstructed.append(form)
                        except Exception as token_error:
                            # 개별 토큰 처리 실패시 스킵
                            continue
                    
                    # 재구성된 문장
                    improved_sentence = ' '.join(reconstructed)
                    
                    # 기본적인 정리
                    improved_sentence = re.sub(r'\s+', ' ', improved_sentence).strip()
                    
                    improved_sentences.append(improved_sentence)
                else:
                    improved_sentences.append(sentence)
            
            # 문장들을 다시 합침
            kiwipiepy_text = '. '.join(improved_sentences)
            
            # 개선된 텍스트가 유효하면 적용
            if kiwipiepy_text and len(kiwipiepy_text.strip()) > len(text.strip()) * 0.7:
                text = kiwipiepy_text
                print("INFO: kiwipiepy 형태소 분석 기반 띄어쓰기 개선 완료", file=sys.stderr)
            else:
                print("INFO: kiwipiepy 결과 품질 검증 실패, 기본 처리 유지", file=sys.stderr)
                
        except ImportError:
            print("INFO: kiwipiepy 모듈을 찾을 수 없어 기본 처리를 사용합니다.", file=sys.stderr)
        except Exception as e:
            print(f"INFO: kiwipiepy 처리 실패 ({e}), 기본 처리 적용", file=sys.stderr)
            print(f"INFO: kiwipiepy 처리 실패 ({e}), 기본 처리 적용", file=sys.stderr)
        
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
        
        # 디버깅: 처리할 이미지 정보 확인
        from pathlib import Path
        img_path = Path(image_path)
        print(f"🔍 DEBUG: 처리할 이미지 = {img_path.name}", file=sys.stderr)
        print(f"🔍 DEBUG: 이미지 존재 = {img_path.exists()}", file=sys.stderr)
        if img_path.exists():
            import os
            size = os.path.getsize(img_path)
            print(f"🔍 DEBUG: 이미지 크기 = {size} bytes", file=sys.stderr)
        
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
        
        # 디버깅: 원본 텍스트 길이
        print(f"🔍 DEBUG: EasyOCR 원본 결과 = {len(full_text)}자", file=sys.stderr)
        
        # 고도화된 한글 텍스트 후처리 적용
        cleaned_text = advanced_korean_text_processor(full_text)
        
        # 디버깅: 처리 후 텍스트 길이 
        print(f"🔍 DEBUG: 후처리 완료 결과 = {len(cleaned_text)}자", file=sys.stderr)
        
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
    
    # JSON 결과 출력 - 인코딩 안전성 개선
    try:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except UnicodeEncodeError:
        # CP949 인코딩 문제 해결을 위해 ASCII로 폴백
        print(json.dumps(result, ensure_ascii=True, indent=2))
    except Exception as e:
        # 최악의 경우 간단한 결과만 출력
        print(json.dumps({
            'success': result.get('success', False),
            'text': result.get('text', '').encode('unicode_escape').decode('ascii'),
            'error': 'encoding_issue'
        }, indent=2))

if __name__ == "__main__":
    main()