"""실제 OCR 결과에 Stage 3.5 TTS 친화적 처리 적용 테스트"""

import logging
from snaptxt.postprocess.stage3 import apply_stage3_rules, Stage3Config
from snaptxt.postprocess.stage3_5 import apply_stage3_5_rules, Stage3_5Config

# 실제 OCR 결과 샘플
michael_singer_text = """마이클 싱어 Michael A. Singer

숨속의 명상가로 불리는 마이클 싱어는 대중 앞의 낯선을 거쳐 영
혼 없는 자신을 알려어 간다가, 오프라 윈프리의 간절한 부탁을 이끌
어 첫째 2012년 《뉴욕 소울 썬데이》에 출간하여 사람들 앞에 처음으
로 모습을 드러냅니다. 온갖 곤민들을 끌어당기게 처지 있던 사
람들은 마음의 굴레에서 자유로워지는 법을 알려주는 그의 강연에
목말라하며 반향합니다. 향후 저서 그의 책 《상처받지 않는 영혼》
은 뉴욕타임즈 베스트셀러 1위에 올랐고, 한국을 포함한 수십 개 국
의 언어로 번역되어 전 세계에 소개되었습니다. 수많은 마음의
침묵 속에 방치해 두었던 참 자기를 찾는 여행으로 우리를 안내하는
그의 책들은 전세계 구둔히 독자들에게 사랑받고 있습니다.

마이클 싱어는 1970년대 초 플로리다 대학교에서 경제학 박사과정
을 공부하던 중에 우연히 직은 내면적 체험을 하게 되어, 그 이후 계속
적인 생활을 접고 온동하여 요가와 명상에 몰두했습니다. 1975년에
명상 요가 센터 Temple of the Universe를 세우고 내지 평화의 체
험을 전하기 시작했습니다. 또한 미술, 교육, 보건, 환경보호 등의 분
야에 크게 기여했습니다. 지서로는 〈상처받지 않는 영혼〉, 〈한 일은
한다〉, 〈마이클 싱어〉 명상 다이어리라〉들이 있습니다.

www.untetheredsoul.com"""

def demo_stage3_5_on_real_ocr():
    """실제 OCR 결과에 Stage 3.5 적용 시연"""
    print("🔥 실제 OCR 결과에 Stage 3.5 TTS 친화적 처리 적용")
    print("=" * 60)
    
    # 로깅 설정
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    
    print("📝 원본 OCR 텍스트:")
    print(michael_singer_text)
    print("\n" + "=" * 60)
    
    # Stage 3.5만 단독 적용
    print("\n🛠️  Stage 3.5 단독 처리 결과:")
    tts_config = Stage3_5Config(
        enable_sentence_boundary_fix=True,
        enable_tts_friendly_symbols=True,
        enable_korean_quotes=True,
        enable_number_reading_format=True,  # 숫자 변환도 활성화
        logger=logging.getLogger("stage3_5_demo")
    )
    
    stage3_5_result = apply_stage3_5_rules(michael_singer_text, tts_config)
    print(stage3_5_result)
    print("\n" + "-" * 40)
    
    # Stage3 전체 (TTS 모드) 적용
    print("\n🎯 Stage3 통합 처리 (TTS 친화적 모드):")
    stage3_config = Stage3Config(
        enable_spacing_normalization=True,
        enable_character_fixes=True,
        enable_ending_normalization=True,
        enable_spellcheck_enhancement=False,  # 속도를 위해 비활성화
        enable_punctuation_normalization=True,
        enable_tts_friendly_processing=True,
        tts_config=tts_config,
        logger=logging.getLogger("stage3_integrated")
    )
    
    full_result = apply_stage3_rules(michael_singer_text, stage3_config)
    print(full_result)
    print("\n" + "=" * 60)
    
    # 주요 개선사항 분석
    print("\n🎙️  TTS 개선사항 분석:")
    improvements = []
    
    if "1970년대" in michael_singer_text and "일천구백칠십" in full_result:
        improvements.append("✅ 년도 읽기 변환: '1970년대' → '일천구백칠십년대'")
    
    if "1위" in michael_singer_text and "일위" in full_result:
        improvements.append("✅ 순위 읽기 변환: '1위' → '일위'")
    
    if "untetheredsoul.com" in michael_singer_text:
        if "언테더드 소울 닷컴" in full_result:
            improvements.append("✅ URL TTS 친화적 변환")
        else:
            improvements.append("ℹ️  URL 처리: 기본 정규화 적용")
    
    if "www." in michael_singer_text and stage3_5_result != michael_singer_text:
        improvements.append("✅ 웹사이트 표기 정리")
    
    original_sentences = michael_singer_text.count('다.')
    processed_sentences = full_result.count('다. ')
    if processed_sentences > 0:
        improvements.append(f"✅ 문장 경계 개선: {processed_sentences}개 문장에 적절한 공백 추가")
    
    if improvements:
        for improvement in improvements:
            print(f"  {improvement}")
    else:
        print("  ✨ 이 텍스트는 이미 TTS에 적합한 형태입니다")
    
    print(f"\n📊 처리 통계:")
    print(f"  • 원본 길이: {len(michael_singer_text)} 자")
    print(f"  • Stage 3.5 결과: {len(stage3_5_result)} 자")
    print(f"  • 통합 처리 결과: {len(full_result)} 자")
    
    # 실제/기대 차이 비교
    print(f"\n🔍 품질 비교:")
    expected_improvements = [
        "책 제목 따옴표: 《상처받지 않는 영혼》",
        "년도 읽기: 일천구백칠십년대", 
        "순위 읽기: 일위",
        "문장 경계 공백 정리"
    ]
    
    for expected in expected_improvements:
        if ':' in expected:
            expected_key = expected.split(':')[1].strip()
        else:
            expected_key = expected
        
        status = "✅" if expected_key in full_result else "⏳"
        print(f"  {status} {expected}")

if __name__ == "__main__":
    demo_stage3_5_on_real_ocr()