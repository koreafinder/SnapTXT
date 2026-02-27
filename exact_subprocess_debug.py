#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Subprocess 정확한 디버깅"""

import subprocess
import sys
import json
import tempfile
import os
from pathlib import Path

def debug_exact_subprocess():
    print('🔍 GUI Subprocess 정확한 디버깅')
    print('='*50)
    
    # 현재 이미지로 GUI와 동일한 subprocess 테스트
    try:
        import cv2
        image = cv2.imread('IMG_4790_test.jpg')
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            
        cv2.imwrite(tmp_path, image)
        
        print(f'📁 임시 파일: {tmp_path}')
        
        # GUI와 완전히 동일한 subprocess 호출
        result = subprocess.run([
            sys.executable,
            'easyocr_worker.py',
            tmp_path,
            'ko+en'
        ], capture_output=True, text=True, timeout=60)
        
        Path(tmp_path).unlink(missing_ok=True)
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            if response['success']:
                return len(response['text']), response['text'][:100]
        
    except Exception as e:
        print(f'❌ 예외: {e}')
        
    return None, None

def debug_direct_call():
    print('📊 직접 함수 호출 테스트')
    try:
        sys.path.append('.')
        from easyocr_worker import process_image_easyocr
        
        result = process_image_easyocr('IMG_4790_test.jpg')
        if result['success']:
            return len(result['text']), result['text'][:100]
    except Exception as e:
        print(f'❌ 예외: {e}')
        
    return None, None

def main():
    print('🎯 정확한 비교 분석\n')
    
    # 1. GUI 방식 (subprocess)
    sub_len, sub_sample = debug_exact_subprocess()
    print(f'GUI 방식: {sub_len}자')
    print(f'샘플: "{sub_sample}..."')
    
    # 2. 직접 호출
    dir_len, dir_sample = debug_direct_call() 
    print(f'직접 호출: {dir_len}자')
    print(f'샘플: "{dir_sample}..."')
    
    print(f'\n차이: {abs(sub_len - dir_len) if sub_len and dir_len else "N/A"}자')
    
    if sub_len == 791 and dir_len == 797:
        print('\n🔍 문제 확인됨: Subprocess 환경에서 다른 결과')
        print('💡 해결책: easyocr_worker.py에 환경별 디버깅 추가')

if __name__ == '__main__':
    main()