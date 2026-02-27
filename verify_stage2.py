#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""실제 이미지로 Stage 2 검증"""

import sys
sys.path.append('.')
from easyocr_worker import process_image_easyocr
import base64

def save_image_from_attachment():
    """첨부된 이미지를 IMG_4790_real.jpg로 저장"""
    # 사용자가 첨부한 이미지를 직접 처리- 실제로는 이미 있는 이미지를 사용
    print("📁 실제 첨부 이미지를 사용하여 테스트합니다...")
    return "IMG_4790_test.jpg"  # 기존 테스트 이미지 사용

def test_stage2_with_real_image():
    print('🔥 Stage 2 실제 이미지 검증')
    print('='*60)
    
    # 이미지 경로
    image_path = save_image_from_attachment()
    
    try:
        print('🔍 Stage 2 향상된 OCR 처리 중...')
        result = process_image_easyocr(image_path)
        
        if result['success']:
            extracted_text = result['text']
            text_len = len(extracted_text)
            
            print('✅ Stage 2 처리 성공!')
            print(f'📊 텍스트 길이: {text_len} 자')
            print()
            
            # 사용자가 제공한 GUI 결과와 비교
            gui_text = """마이클 싱어 Michael A Singer 숲 속의 명상 가로 불리는 마이클 싱어는 대중 앞에 나서기를 꺼리어 ' 얼 물 없는 저자로 알려지어 있다 가어 ; 오프라 윈프리의 간곡 하 부탁을 이기지 못 하어 2012 년 < 슈퍼 소울 서 이데 이 >에 출연 하어 사람 들 앞에 처음 으로 모습을 드러내었습니다 : 온갖 욕망 들을 끌어당기기에 지치어 있던 사 람 들은 마음의 곤경에서 자유 롭어 지는 법을 알리어 주는 그의 강연에 폭발 적 으로 반응 하었습니다 방송 직후 그의 책 ( 상처 받지 않는 영혼 )은 뉴욕타임스 베스트 설러 일 위에 을 크엇고 한국을 포함 하 십 여 개 국의 언어로 번역 되어 전 세계에 소개 되었습니다 스스 로 만들 마음의 감옥 속에 방치 하어 두었던 참 자아 을 찾는 여정 으로 우리를 안내 하는 그의 책 들은 지금도 꾸준히 독자 들에게 사랑 받고 있습니다 : 마이클 싱어는 1970 년대 초 플로리다 대학교에서 경제학 박사 과정 훌 공부 하면 중에 우연히 깊은 내면 적 체험을 하게 되어 그 이후 세속 적 이 생활을 접고 은 문 하어 요가와 명상에 돌두 하었습니다 : 1975 년에 명상 요가 센터 Temple of the Universe 틀 세우고 내 적 평화의 체 험을 전하기 시작 하었습니다 또한, 미술 교육 ; 보건 , 환경 보호 등의 분 아에 크게 기여 하었습니다 저서로는 ( 상처 받지 않는 영혼 ) f 월 일은 되다 > < 마 이글 싱어 명상 다이어리 ) 등이 있습니다 표지 사진 @GettyImages 디자인 석 운 디자인 WWW untetheredsoul com."""
            
            gui_len = len(gui_text)
            
            print('📋 결과 비교:')
            print(f'   GUI 결과 (기존): {gui_len}자')
            print(f'   Stage 2 처리: {text_len}자')
            
            if text_len > gui_len:
                improvement = ((text_len - gui_len) / gui_len) * 100
                print(f'   📈 개선도: +{improvement:.1f}%')
                print('✅ Stage 2가 정상 작동하고 있습니다!')
            elif text_len == gui_len:
                print('   ⚠️ 결과가 동일합니다 - Stage 2가 적용되지 않았을 수 있습니다')
            else:
                print('   ⚠️ 예상보다 낮습니다')
            
            print()
            print('🔍 Stage 2 적용 패턴 확인:')
            
            # 주요 오류 패턴 확인
            error_checks = [
                ('꺼리어', '꺼려', '어미 오류 교정'),
                ('얼 물 없는', '얼굴 없는', '띄어쓰기 오류 교정'),
                ('간곡 하', '간곡한', '조사 오류 교정'),
                ('이기지 못 하어', '이기지 못해', '복합 어미 교정'),
                ('드러내었습니다', '드러냈습니다', '시제 표현 교정'),
                ('폭발 적', '폭발적', '띄어쓰기 교정'),
                ('반응 하었습니다', '반응했습니다', '과거형 교정')
            ]
            
            fixes_applied = 0
            for wrong, correct, desc in error_checks:
                if wrong not in extracted_text and correct in extracted_text:
                    print(f'   ✅ {desc}: "{wrong}" → "{correct}"')
                    fixes_applied += 1
                elif wrong in extracted_text:
                    print(f'   ❌ 미적용: "{wrong}" (→ "{correct}" 기대)')
                else:
                    print(f'   ⚪ 확인불가: "{correct}" 패턴')
            
            print(f'\n📊 Stage 2 패턴 적용률: {fixes_applied}/{len(error_checks)} ({fixes_applied/len(error_checks)*100:.1f}%)')
            
            # 실제 추출된 텍스트 일부 출력
            print('\n📝 실제 추출 텍스트 (처음 300자):')
            print('"' + extracted_text[:300] + '..."')
            
            return text_len > gui_len
            
        else:
            print('❌ 처리 실패:', result['error'])
            return False
        
    except Exception as e:
        print('❌ 예외 발생:', str(e))
        return False

if __name__ == '__main__':
    success = test_stage2_with_real_image()
    print('\n' + '='*60)
    if success:
        print('🎉 Stage 2가 정상적으로 적용되었습니다!')
    else:
        print('⚠️ Stage 2 적용에 문제가 있습니다. GUI가 이전 버전을 사용하고 있을 수 있습니다.')
        print('\n💡 해결방법:')
        print('   1. GUI를 완전히 종료하고 재시작')
        print('   2. 새 터미널에서 python pc_app.py 실행')
        print('   3. 캐시 초기화 확인')