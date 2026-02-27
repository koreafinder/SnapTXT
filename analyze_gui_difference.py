#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GUI vs 명령줄 결과 차이점 정확 분석"""

import sys
import subprocess
import json
import time
sys.path.append('.')
from easyocr_worker import process_image_easyocr

def analyze_gui_difference():
    print('🔍 GUI vs 명령줄 Stage 2 결과 정확 분석')
    print('='*60)
    
    image_path = 'IMG_4790_test.jpg'
    
    # 1. 직접 함수 호출 (명령줄 방식)
    print('1️⃣ 직접 함수 호출 (명령줄 방식)')
    try:
        direct_result = process_image_easyocr(image_path)
        if direct_result['success']:
            direct_text = direct_result['text']
            direct_len = len(direct_text)
            print(f'   ✅ 성공: {direct_len}자')
        else:
            print(f'   ❌ 실패: {direct_result["error"]}')
            return
    except Exception as e:
        print(f'   ❌ 예외: {e}')
        return
    
    # 2. subprocess 호출 (GUI와 동일한 방식)
    print('2️⃣ Subprocess 호출 (GUI와 동일)')
    try:
        result = subprocess.run([
            sys.executable,
            'easyocr_worker.py', 
            image_path, 
            'ko+en'
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            subprocess_result = json.loads(result.stdout)
            if subprocess_result['success']:
                subprocess_text = subprocess_result['text']
                subprocess_len = len(subprocess_text)
                print(f'   ✅ 성공: {subprocess_len}자')
                
                # stderr 확인
                if result.stderr:
                    print('   📝 Stderr 메시지:')
                    stderr_lines = result.stderr.split('\n')
                    stage2_count = 0
                    for line in stderr_lines:
                        if 'Stage 2' in line:
                            stage2_count += 1
                            print(f'     {line}')
                    print(f'   🎯 Stage 2 메시지 개수: {stage2_count}')
            else:
                print(f'   ❌ 실패: {subprocess_result["error"]}')
                return
        else:
            print(f'   ❌ 프로세스 실패 (코드 {result.returncode}): {result.stderr}')
            return
    except Exception as e:
        print(f'   ❌ 예외: {e}')
        return
    
    # 3. GUI 결과와 비교
    gui_result_len = 791  # GUI에서 나온 결과
    
    print('\n📊 상세 결과 비교')
    print(f'   직접 호출: {direct_len}자')
    print(f'   Subprocess: {subprocess_len}자')
    print(f'   GUI 실제: {gui_result_len}자')
    
    print('\n🔍 분석')
    if direct_len == subprocess_len:
        print('   ✅ 명령줄과 subprocess 결과 동일')
        if subprocess_len != gui_result_len:
            print('   ⚠️ GUI 결과만 다름 - GUI 내부 처리 문제일 수 있음')
            print('   💡 가능한 원인:')
            print('     - 임시 파일 처리 차이')
            print('     - JSON 파싱/전달 과정 차이')
            print('     - multi_ocr_processor.py의 추가 처리')
    else:
        print('   ⚠️ 모든 결과가 다름')
    
    # 4. 실제 텍스트 샘플 비교
    print('\n📝 텍스트 샘플 (처음 200자)')
    print(f'직접: "{direct_text[:200]}..."')
    print(f'Sub: "{subprocess_text[:200]}..."')
    
    return {
        'direct': direct_len,
        'subprocess': subprocess_len,
        'gui': gui_result_len
    }

if __name__ == '__main__':
    results = analyze_gui_difference()
    if results:
        print('\n🎯 최종 결론:')
        if results['direct'] == results['subprocess'] == results['gui']:
            print('   ✅ 모든 방식에서 동일한 결과')
        elif results['direct'] == results['subprocess'] != results['gui']:
            print('   ⚠️ GUI만 다른 결과 - GUI 내부 문제')
        else:
            print('   ❓ 복잡한 차이 - 추가 디버깅 필요')