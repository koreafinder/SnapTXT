#!/usr/bin/env python3
"""
IMG_4790.JPG OCR 결과 vs Ground Truth 비교 점수 계산
"""

from difflib import SequenceMatcher
import re

def calculate_detailed_score(ocr_text: str, gt_text: str):
    """정확한 OCR 점수 계산"""
    
    # 기본 전처리 (공백 정규화)
    ocr_clean = ' '.join(ocr_text.split())
    gt_clean = ' '.join(gt_text.split())
    
    print(f"🔍 텍스트 길이 비교:")
    print(f"   OCR 결과: {len(ocr_text)}자 (전처리 후: {len(ocr_clean)}자)")
    print(f"   정답(GT): {len(gt_text)}자 (전처리 후: {len(gt_clean)}자)")
    
    # 1. 전체 유사도 (SequenceMatcher)
    seq_ratio = SequenceMatcher(None, ocr_clean, gt_clean).ratio()
    
    # 2. 문자 단위 정확도
    min_len = min(len(ocr_clean), len(gt_clean))
    max_len = max(len(ocr_clean), len(gt_clean))
    char_matches = sum(1 for i in range(min_len) if i < len(ocr_clean) and i < len(gt_clean) and ocr_clean[i] == gt_clean[i])
    char_accuracy = char_matches / max_len if max_len > 0 else 0
    
    # 3. 단어 단위 정확도
    ocr_words = set(ocr_clean.split())
    gt_words = set(gt_clean.split())
    word_intersection = len(ocr_words & gt_words)
    word_union = len(ocr_words | gt_words)
    word_accuracy = word_intersection / word_union if word_union > 0 else 0
    
    # 4. 키워드 정확도 (GT에서 중요 키워드 확인) 
    gt_keywords = ["마이클", "싱어", "명상가", "오프라", "베스트셀러", "상처받지 않는 영혼", "플로리다", "대학교", "Temple", "Universe"]
    keyword_hits = sum(1 for kw in gt_keywords if kw in ocr_text)
    keyword_accuracy = keyword_hits / len(gt_keywords)
    
    # 5. 구문 단위 정확도 (문장 구분 기준)
    ocr_sentences = [s.strip() for s in re.split(r'[.!:]\s*', ocr_text) if s.strip()]
    gt_sentences = [s.strip() for s in re.split(r'[.!:]\s*', gt_text) if s.strip()]
    
    sentence_matches = 0
    for gt_sent in gt_sentences:
        best_match = max([SequenceMatcher(None, gt_sent, ocr_sent).ratio() for ocr_sent in ocr_sentences] or [0])
        if best_match > 0.7:  # 70% 이상 유사하면 매치로 간주
            sentence_matches += 1
    
    sentence_accuracy = sentence_matches / len(gt_sentences) if gt_sentences else 0
    
    # 6. 종합 품질 점수 (가중 평균)
    overall_score = (
        seq_ratio * 0.3 +           # 전체 유사도 30%
        char_accuracy * 0.2 +       # 문자 정확도 20%  
        word_accuracy * 0.2 +       # 단어 정확도 20%
        keyword_accuracy * 0.2 +    # 키워드 정확도 20%
        sentence_accuracy * 0.1     # 구문 정확도 10%
    )
    
    return {
        "sequence_similarity": seq_ratio,
        "character_accuracy": char_accuracy,
        "word_accuracy": word_accuracy, 
        "keyword_accuracy": keyword_accuracy,
        "sentence_accuracy": sentence_accuracy,
        "overall_score": overall_score,
        "character_matches": char_matches,
        "total_chars": max_len,
        "word_matches": word_intersection,
        "total_words": word_union,
        "keyword_matches": keyword_hits,
        "total_keywords": len(gt_keywords),
        "sentence_matches": sentence_matches,
        "total_sentences": len(gt_sentences)
    }

def main():
    print("📊 IMG_4790.JPG OCR 품질 점수 계산")
    print("=" * 60)
    
    # Ground Truth (정답)
    ground_truth = """마이클 싱어 Michael A. Singer

숲속의 명상가로 불리는 마이클 싱어는 대중 앞에 나서기를 꺼려
'얼굴 없는 저자'로 알려져 있다가, 오프라 윈프리의 간곡한 부탁을 이기지 못해
2012년 <슈퍼 소울 선데이>에 출연하며 사람들 앞에 처음으로 모습을 드러냈습니다.

온갖 욕망들을 끌어당기기에 지쳐 있던 사람들은
마음의 곤경에서 자유로워지는 법을 알려주는 그의 강연에
폭발적으로 반응했습니다.

방송 직후 그의 책 《상처받지 않는 영혼》은
뉴욕타임스 베스트셀러 1위에 올랐고,
한국을 포함한 십여 개 국의 언어로 번역되어
전 세계에 소개되었습니다.

스스로 만든 마음의 감옥 속에 방치해 두었던 참 자아를 찾는 여정으로
우리를 안내하는 그의 책들은 지금도 꾸준히 독자들에게 사랑받고 있습니다.

마이클 싱어는 1970년대 초 플로리다 대학교에서 경제학 박사과정을 공부하던 중
우연히 깊은 내면적 체험을 하게 되어,
이후 세속적인 생활을 접고 은둔하여 요가와 명상에 몰두했습니다.

1975년에 명상 요가 센터 Temple of the Universe를 세우고
내적 평화의 체험을 전하기 시작했습니다.

저서로는 《상처받지 않는 영혼》, 《될 일은 된다》,
《마이클 싱어 명상 다이어리》 등이 있습니다."""
    
    # OCR 결과 (사용자 제공)
    ocr_result = """마이컨생어 Michael A Singer 숲속의 명상가로 불리는 마이클 싱어는 대중 앞에 나서기를 꺼려' 얼 물없는 저자로 알려져 있다가 오프라 윈프리의 간곡한 부탁을 이기지 못해 2012년 <슈퍼 소울 선데이>에 출연하여 사람들 앞에 처음으로 모습을 드러움습니다: 온갖 욕망들을 끌어당기기에 지쳐 있던 사 감들은 마음의 곤경에서 자유로워지는 법을 알려주는 그의 강연에 폭발적으로 반응했습니다: 방송 직후 그의 책 ( 상처받지 않는 영혼 ) 은 뉴욕타임스 베스트셀러 1위에 올랐고 한국을 포함한 십여 개 국의 언어로 번역되어 전 세계에 소개됐습니다 스스로 만든 마음의 감옥 속에 방치해 두었던 참 자아를 찾는 여정으로 우리를 안내하는 그의 책들은 지금도 꾸준히 독자들에계 사랑반고 있습니다 마이클 싱어는 1970 년대 초 플로리다 대학교에서 경제학 박사과정 을공부하던 중에 우연히 깊은 내면적 체험을 하게 되어 그 이후 세속적인 생활을 접고 은둔하여 요가와 명상에 몰두했습니다: 1975 년에 명상 요가 센터 Ternple of the Universe틀 세우고 내적 평화의 체 힘을 전하기 시작했습니다: 또한 미술, 교육; 보건 환경보호 등의 분야에 크게 기여했습니다 저서로는 ( 상처받지 않는 영혼 ( 될 일은 된다 , ( 마이클 싱어 명상 다이어리 ) 등이 있습니다: 표치사진 OGettyimages 다사인 식운디자인 WWW untethieredsoulcom"""
    
    # 점수 계산
    scores = calculate_detailed_score(ocr_result, ground_truth)
    
    print(f"\n📈 상세 점수 분석:")
    print(f"   🎯 전체 유사도: {scores['sequence_similarity']:.3f} ({scores['sequence_similarity']*100:.1f}%)")
    print(f"   📝 문자 정확도: {scores['character_accuracy']:.3f} ({scores['character_matches']}/{scores['total_chars']} 매치)")
    print(f"   📖 단어 정확도: {scores['word_accuracy']:.3f} ({scores['word_matches']}/{scores['total_words']} 매치)")  
    print(f"   🔑 키워드 정확도: {scores['keyword_accuracy']:.3f} ({scores['keyword_matches']}/{scores['total_keywords']} 매치)")
    print(f"   📄 구문 정확도: {scores['sentence_accuracy']:.3f} ({scores['sentence_matches']}/{scores['total_sentences']} 매치)")
    
    print(f"\n🏆 종합 품질 점수: {scores['overall_score']:.3f} ({scores['overall_score']*100:.1f}%)")
    
    # 등급 매기기
    if scores['overall_score'] >= 0.9:
        grade = "A+ (최우수)"
    elif scores['overall_score'] >= 0.8:
        grade = "A (우수)"  
    elif scores['overall_score'] >= 0.7:
        grade = "B (양호)"
    elif scores['overall_score'] >= 0.6:
        grade = "C (보통)"
    else:
        grade = "D (개선 필요)"
    
    print(f"📊 품질 등급: {grade}")
    
    # Ground Truth와 비교했을 때의 예상 정확도
    expected_accuracy = 0.85  # Ground Truth에서 제시된 예상 정확도
    print(f"\n📋 Ground Truth 정보:")
    print(f"   예상 OCR 정확도: {expected_accuracy:.1%}")
    print(f"   실제 측정 정확도: {scores['overall_score']:.1%}")
    
    if scores['overall_score'] >= expected_accuracy:
        print(f"   ✅ 예상보다 {(scores['overall_score'] - expected_accuracy)*100:.1f}%p 높음")
    else:
        print(f"   📉 예상보다 {(expected_accuracy - scores['overall_score'])*100:.1f}%p 낮음")
    
    # 주요 오류 분석
    print(f"\n❌ 발견된 주요 오류:")
    errors = []
    if "마이컨생어" in ocr_result:
        errors.append("- '마이컨생어' → '마이클 싱어' (이름 인식 오류)")
    if "얼 물없는" in ocr_result:
        errors.append("- '얼 물없는' → '얼굴 없는' (OCR 문자 인식 오류)")
    if "사 감들은" in ocr_result:
        errors.append("- '사 감들은' → '사람들은' (단어 분할 오류)")
    if "에계" in ocr_result:
        errors.append("- '에계' → '에게' (문법 오류)")
    if "사랑반고" in ocr_result:
        errors.append("- '사랑반고' → '사랑받고' (OCR 인식 오류)")
    if "Ternple" in ocr_result:
        errors.append("- 'Ternple' → 'Temple' (영어 철자 오류)")
    if "체 힘을" in ocr_result:
        errors.append("- '체 힘을' → '체험을' (단어 인식 오류)")
    
    if errors:
        for error in errors:
            print(f"   {error}")
    else:
        print("   (주요 오류 없음)")
    
    print(f"\n🎯 개선을 위한 제안:")
    if scores['character_accuracy'] < 0.8:
        print("   - OCR 엔진의 문자 인식 정확도 개선 필요")
    if scores['keyword_accuracy'] < 0.8:
        print("   - 중요 키워드 후처리 규칙 강화")
    if scores['sentence_accuracy'] < 0.7:
        print("   - 구문 단위 후처리 및 문맥 분석 강화")

if __name__ == "__main__":
    main()