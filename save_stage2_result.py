#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 2 결과를 텍스트 파일로 저장하여 비교"""

import sys
sys.path.append('.')
from easyocr_worker import process_image_easyocr
from datetime import datetime

def save_stage2_result():
    print('📄 Stage 2 결과를 텍스트 파일로 저장합니다...')
    
    try:
        result = process_image_easyocr('IMG_4790_test.jpg')
        
        if result['success']:
            extracted_text = result['text']
            text_len = len(extracted_text)
            
            # 결과를 텍스트 파일로 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stage2_result_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Stage 2 OCR 결과 - {datetime.now()}\n")
                f.write(f"텍스트 길이: {text_len}자\n")
                f.write("="*60 + "\n\n")
                f.write(extracted_text)
            
            print(f'✅ 결과 저장 완료: {filename}')
            print(f'📊 텍스트 길이: {text_len}자')
            
            # 사용자가 제공한 GUI 결과와 비교
            gui_result_len = len("""마이클 싱어 Michael A Singer 숲 속의 명상 가로 불리는 마이클 싱어는 대중 앞에 나서기를 꺼리어 ' 얼 물 없는 저자로 알려지어 있다 가어 ; 오프라 윈프리의 간곡 하 부탁을 이기지 못 하어 2012 년 < 슈퍼 소울 서 이데 이 >에 출연 하어 사람 들 앞에 처음 으로 모습을 드러내었습니다 : 온갖 욕망 들을 끌어당기기에 지치어 있던 사 람 들은 마음의 곤경에서 자유 롭어 지는 법을 알리어 주는 그의 강연에 폭발 적 으로 반응 하었습니다 방송 직후 그의 책 ( 상처 받지 않는 영혼 )은 뉴욕타임스 베스트 설러 일 위에 을 크엇고 한국을 포함 하 십 여 개 국의 언어로 번역 되어 전 세계에 소개 되었습니다 스스 로 만들 마음의 감옥 속에 방치 하어 두었던 참 자아 을 찾는 여정 으로 우리를 안내 하는 그의 책 들은 지금도 꾸준히 독자 들에게 사랑 받고 있습니다 : 마이클 싱어는 1970 년대 초 플로리다 대학교에서 경제학 박사 과정 훌 공부 하면 중에 우연히 깊은 내면 적 체험을 하게 되어 그 이후 세속 적 이 생활을 접고 은 문 하어 요가와 명상에 돌두 하었습니다 : 1975 년에 명상 요가 센터 Temple of the Universe 틀 세우고 내 적 평화의 체 험을 전하기 시작 하었습니다 또한, 미술 교육 ; 보건 , 환경 보호 등의 분 아에 크게 기여 하었습니다 저서로는 ( 상처 받지 않는 영혼 ) f 월 일은 되다 > < 마 이글 싱어 명상 다이어리 ) 등이 있습니다 표지 사진 @GettyImages 디자인 석 운 디자인 WWW untetheredsoul com.""")
            
            print('\n📋 비교 결과:')
            print(f'   GUI 결과: {gui_result_len}자')
            print(f'   Stage 2 명령줄: {text_len}자')
            
            if text_len > gui_result_len:
                improvement = ((text_len - gui_result_len) / gui_result_len) * 100
                print(f'   📈 개선도: +{improvement:.1f}%')
                print('✅ Stage 2가 더 좋은 결과를 제공합니다!')
            elif text_len == gui_result_len:
                print('   ⚠️ 결과가 동일합니다')
            else:
                print('   ⚠️ 예상과 다릅니다')
                
            print(f'\n💡 이제 GUI에서 같은 이미지를 처리하고 결과를 비교해보세요')
            print(f'   현재 Stage 2 결과: {filename}')
            
            return filename
            
        else:
            print('❌ 처리 실패:', result['error'])
            return None
        
    except Exception as e:
        print('❌ 예외 발생:', str(e))
        return None

if __name__ == '__main__':
    filename = save_stage2_result()
    if filename:
        print('\n🎯 다음 단계:')
        print('1. GUI에서 같은 이미지(IMG_4790.JPG) 처리')
        print('2. 로그에서 "Stage 2" 메시지 확인')
        print('3. 결과 텍스트 길이 비교')
        print(f'4. {filename} 파일과 GUI 결과 비교')