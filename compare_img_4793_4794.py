#!/usr/bin/env python3
"""
IMG_4793 vs IMG_4794 OCR 결과 비교 분석
"""

from difflib import SequenceMatcher
import re
import time
import logging

# 로깅 설정 (상세 디버깅 활성화)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s'
)

# 후처리 시스템 import
try:
    from snaptxt.postprocess import run_pipeline, Stage2Config, Stage3Config
    print("✅ 후처리 시스템 import 성공")
except ImportError as e:
    print(f"❌ 후처리 시스템 import 실패: {e}")

def calculate_detailed_score(ocr_text: str, gt_text: str):
    """정확한 OCR 점수 계산"""
    
    # 텍스트 전처리
    def preprocess_text(text):
        # 공백 정규화 및 특수문자 제거
        text = re.sub(r'\s+', ' ', text.strip())
        return text
    
    ocr_clean = preprocess_text(ocr_text)
    gt_clean = preprocess_text(gt_text)
    
    print(f"🔍 텍스트 길이 비교:")
    print(f"   OCR 결과: {len(ocr_text)}자 (전처리 후: {len(ocr_clean)}자)")
    print(f"   정답 추정: {len(gt_text)}자 (전처리 후: {len(gt_clean)}자)")
    
    # 1. 전체 유사도 (SequenceMatcher)
    seq_ratio = SequenceMatcher(None, ocr_clean, gt_clean).ratio()
    
    # 2. 문자 단위 정확도
    max_len = max(len(ocr_clean), len(gt_clean))
    char_matches = sum(1 for i in range(min(len(ocr_clean), len(gt_clean))) 
                      if ocr_clean[i] == gt_clean[i])
    char_accuracy = char_matches / max_len if max_len > 0 else 0
    
    # 3. 단어 단위 정확도
    ocr_words = set(ocr_clean.split())
    gt_words = set(gt_clean.split())
    word_intersection = len(ocr_words.intersection(gt_words))
    word_union = len(ocr_words.union(gt_words))
    word_accuracy = word_intersection / word_union if word_union > 0 else 0
    
    # 4. 키워드 정확도 (중요 단어들)
    gt_keywords = [word for word in gt_words if len(word) >= 2 and word not in ['이다', '있다', '하다', '되다']]
    keyword_hits = sum(1 for keyword in gt_keywords if keyword in ocr_text)
    keyword_accuracy = keyword_hits / len(gt_keywords) if gt_keywords else 0
    
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

def apply_postprocessing_test(ocr_text: str, image_name: str):
    """후처리 시스템 테스트"""
    print(f"\n🧠 {image_name} 후처리 적용 테스트")
    
    try:
        start_time = time.time()
        processed_text = run_pipeline(
            ocr_text,
            stage2_config=Stage2Config(),
            stage3_config=Stage3Config()
        )
        processing_time = time.time() - start_time
        
        if not processed_text:
            processed_text = ocr_text  # 폴백
            print(f"   ⚠️  후처리 폴백 적용")
        else:
            print(f"   ✅ 후처리 완료 ({processing_time*1000:.1f}ms)")
            
        change_ratio = abs(len(processed_text) - len(ocr_text)) / len(ocr_text) * 100
        print(f"   📊 텍스트 길이 변화: {len(ocr_text)} → {len(processed_text)}자 ({change_ratio:.1f}%)")
        
        return processed_text, processing_time
        
    except Exception as e:
        import traceback
        print(f"❌ 후처리 실패: {e}")
        print(f"🔍 스택 트레이스:")
        traceback.print_exc()
        return ocr_text, 0.0

def analyze_error_patterns(ocr_text: str, image_name: str):
    """OCR 오류 패턴 분석"""
    print(f"\n🔍 {image_name} 주요 오류 패턴:")
    
    # 일반적인 OCR 오류 패턴들
    error_patterns = [
        (r'울(?=\s)', '을', 'ㅜ→ㅡ 혼동'),
        (r'논(?=\s)', '는', 'ㅗ→ㅡ 혼동'),
        (r'릎(?=\s)', '를', '받침 ㄹ 오류'),
        (r'틀(?=\s)', '를', '받침 ㄹ 오류'),
        (r'없다', '었다', '없→었 혼동'),
        (r'있다(?=\s[^.])', '었다', '있→었 혼동'),
        (r'쓰러고', '쓰려고', 'ㅓ→ㅕ 혼동'),
        (r'잎(?=\s)', '입', 'ㅣㅍ→ㅣㅂ 혼동'),
        (r'핑(?=\s)', '있', 'ㅍ→ㅂ 혼동'),
        (r'반지(?=\s)', '받지', 'ㄴ→ㅂ 혼동'),
        (r'계만', '게만', 'ㅖ→ㅔ 혼동')
    ]
    
    found_errors = []
    for pattern, correct, description in error_patterns:
        matches = re.findall(pattern, ocr_text)
        if matches:
            found_errors.append(f"   - '{pattern.replace('(?=\\s)', '').replace('(?=\\s[^.])', '')}' → '{correct}' ({description})")
    
    if found_errors:
        for error in found_errors[:5]:  # 최대 5개만 표시
            print(error)
    else:
        print("   주요 오류 패턴을 찾지 못했습니다")

def main():
    print("📊 IMG_4793 vs IMG_4794 비교 분석")
    print("=" * 70)
    
    # IMG_4793 OCR 결과
    img_4793_text = """서문 가장 진실한 자아를 만나기 위한 여정" 참된 성장울 위해서논 마음의 소리가 곧 내가 아니고 나는 그 소리들 듣는 자임을 깨닫는 것이 가장 중요하다" ~마이클 A 싱어 처음 <상처받지 않은 영혼 ) 을 쓰러고 햇을 때 내 의도는 아주 단순있다 온 전한 내면의 자유로 향하는 여정을 기꺼이 그 킬로 건고자 하는 사람들과 나누고 싶없다: 영적 성장은 단순하고 명확해야 하여 직관적으로 알 수 잎 어야 한다: 자유는 세상에서 가장 자연스러운 상태다 사실 타고난 권리이 기도 하다: 문제는 우리의 마음과 감정의 선호가 그 간단한 진실을 이해하 기 어렵게 만듣다는 점이다 ( 상처받지 않은 영혼은 우리 안에 내재된 진 실을 직접적으로 경험할 수 있는 여정으로 우리릎 안내한다 우리 아난 것을 놓아버길 때, 우리논 비로소 우리가 누구인지틀 발견할 수 있다이 깊은 내면으로의 여정은 신비주의자나 학자에계만 해당하는 이야기가 아니다: 이는 참나의 자리로 돌아가늘 여정이며 누구든 함께할 수 있다 이제 기쁨 마음으로 ( 상처반지 않은 영혼 ) 을 위한이 아름답고 실용적인 ( 명상 저널 ) 을 소개한다이 일지는 여러 분의 내면으로 여행할 수 핑게 안내 해 주즉 이상적인 수단이 덜 것이다 우리늄이 책울 통해 여러 분이 각자의 마"""
    
    # IMG_4794 OCR 결과 (이전 분석에서 사용한 것)
    img_4794_text = """음; 감정 내면의 에너지와 및고 있는 심오한 관계를 이해하도록 안내할 생각 이다: 여러 분은 시끄러운 마음을 놓아주고 마음속에 담아두/단 과거의 힘 듣경험과 상처클 놓아 보내게 덜 젓이다 그렇게 함으로씨 모든 것을 지켜보 고있는 가장 내밀한 참나의 자유와 행복에 도달할 수 있기 된다: 각각의 장은 ( 상처받지 않은 영혼에 나뒷년 가장 의미 있는 핵심 구절들 로시작한다 그다음에 이어지논 길잡이 글은 그가르침을 실생활에 적용할 수 잇도록 권장한다 이를 통해 가르침의 핵심으로 더 깊이 뛰어들고 그것 을일상의 일부로 만들 수 있다 가끔은 좁 더 자신을 돌아보고 숙고하도록 이끌기도 할 것이다: 그런가 하면 더 심오한 수행을 하도록 도와주는 연습도 있을 것이다 책의 가르침과 당신의 관계록 글로 씨 보면 가르침울 더 깊이 이해하는 데 도움이 되므로이 일지에 당신의 경험을 쓰고 그에 대해 생 각해 보과 그것이 바로 저널렁의 목적이다 말의 위력을 넘어서 직접적인 경험의 위력으로 가는 것 이제 당신은 상처 주위에 보호막을 둘러친 자기 자신을 넘어서서 내면의 자유; 행복 깨달음으로 가는 여정을 시작히려 한다이 저널을 읽고 생각하 고 직접 쓰면서 각 장이 치유의 이야기로 채워지는 것을 보게 되리라 어찌 면이 책의 제한된 공간에서 벗어나 다른 일지에 자신의 생각을 계속 씨나 갈 수도 있다 혹은 어떤 구절을 읽은 뒤에는 글을 쓰기보다는 생각에 더 잠 길 수도 있다 어떤 문장은 그대로 필사할 수도 있다 어떤 식이든 다 괜창 다이 일지률 당신만의 방식대로 활용하라 일지롭다 손 뒤에는 언제든가 장 여운이 큰길잡이 글로 돌아갈 수 있다 시간이 흐를수록 당신의 이해는 더 깊어질 것이다:"""
    
    # 공통 정답 (추정)
    ground_truth = """상처받지 않는 영혼 서문
가장 진실한 자아를 만나기 위한 여정

참된 성장을 위해서는 마음의 소리가 곧 내가 아니고, 나는 그 소리들을 듣는 자임을 깨닫는 것이 가장 중요하다.
~마이클 A. 싱어

처음 《상처받지 않는 영혼》을 쓰려고 했을 때, 내 의도는 아주 단순했다. 온전한 내면의 자유로 향하는 여정을 기꺼이 그 길로 걷고자 하는 사람들과 나누고 싶었다.

영적 성장은 단순하고 명확해야 하며, 직관적으로 알 수 있어야 한다. 자유는 세상에서 가장 자연스러운 상태다. 사실 타고난 권리이기도 하다. 문제는 우리의 마음과 감정의 선호가 그 간단한 진실을 이해하기 어렵게 만든다는 점이다.

《상처받지 않는 영혼》은 우리 안에 내재된 진실을 직접적으로 경험할 수 있는 여정으로 우리를 안내한다. 우리가 아닌 것을 놓아버릴 때, 우리는 비로소 우리가 누구인지를 발견할 수 있다.

이 깊은 내면으로의 여정은 신비주의자나 학자에게만 해당하는 이야기가 아니다. 이는 참나의 자리로 돌아가는 여정이며, 누구든 함께할 수 있다.

이제 기쁜 마음으로 《상처받지 않는 영혼》을 위한 이 아름답고 실용적인 《명상 저널》을 소개한다. 이 일지는 여러분의 내면으로 여행할 수 있게 안내해 주는 이상적인 수단이 될 것이다."""
    
    # IMG_4793 분석
    print(f"\n📈 🔹 IMG_4793 품질 분석")
    img_4793_scores = calculate_detailed_score(img_4793_text, ground_truth)
    
    print(f"\n📈 상세 점수 분석:")
    print(f"   🎯 전체 유사도: {img_4793_scores['sequence_similarity']:.3f} ({img_4793_scores['sequence_similarity']*100:.1f}%)")
    print(f"   📝 문자 정확도: {img_4793_scores['character_accuracy']:.3f} ({img_4793_scores['character_matches']}/{img_4793_scores['total_chars']} 매치)")
    print(f"   📖 단어 정확도: {img_4793_scores['word_accuracy']:.3f} ({img_4793_scores['word_matches']}/{img_4793_scores['total_words']} 매치)")
    print(f"   🔑 키워드 정확도: {img_4793_scores['keyword_accuracy']:.3f} ({img_4793_scores['keyword_matches']}/{img_4793_scores['total_keywords']} 매치)")
    print(f"   📄 구문 정확도: {img_4793_scores['sentence_accuracy']:.3f} ({img_4793_scores['sentence_matches']}/{img_4793_scores['total_sentences']} 매치)")
    print(f"\n🏆 IMG_4793 종합 품질 점수: {img_4793_scores['overall_score']:.3f} ({img_4793_scores['overall_score']*100:.1f}%)")
    
    # IMG_4794 비교를 위한 간단 분석 (이전 결과 사용)
    print(f"\n📈 🔸 IMG_4794 비교 (이전 분석 결과)")
    print(f"   🏆 IMG_4794 종합 품질 점수: 0.151 (15.1%)")
    
    # 오류 패턴 분석
    analyze_error_patterns(img_4793_text, "IMG_4793")
    
    # 후처리 테스트
    processed_4793, time_4793 = apply_postprocessing_test(img_4793_text, "IMG_4793")
    
    # 최종 비교
    print(f"\n📊 🎯 최종 비교 결과")
    print(f"=" * 50)
    print(f"📸 IMG_4793:")
    print(f"   📏 원본 길이: {len(img_4793_text)}자")
    print(f"   🏆 품질 점수: {img_4793_scores['overall_score']*100:.1f}%")
    print(f"   ⏱️  후처리 시간: {time_4793*1000:.1f}ms")
    
    print(f"\n📸 IMG_4794:")
    print(f"   📏 원본 길이: {len(img_4794_text)}자") 
    print(f"   🏆 품질 점수: 15.1%")
    print(f"   ⏱️  후처리 시간: ~176ms")
    
    # 품질 차이 분석
    quality_diff = (img_4793_scores['overall_score'] - 0.151) * 100
    print(f"\n🔍 품질 차이 분석:")
    if quality_diff > 0:
        print(f"   📈 IMG_4793이 {quality_diff:.1f}%p 더 우수")
    elif quality_diff < 0:
        print(f"   📉 IMG_4794가 {abs(quality_diff):.1f}%p 더 우수") 
    else:
        print(f"   ⚖️  두 이미지 품질이 유사함")
    
    # 공통 특징
    print(f"\n🎭 공통 특징:")
    print(f"   📚 동일한 서적: '상처받지 않는 영혼' 서문")
    print(f"   🔤 유사 오류: ㅜ↔ㅡ, ㅗ↔ㅡ, 받침 오류 등")
    print(f"   🛡️  안전성 정책: 두 이미지 모두 fallback 적용")
    
    # 등급 매기기
    def get_quality_grade(score):
        if score >= 0.9: return "A+ (우수)"
        elif score >= 0.8: return "A (양호)" 
        elif score >= 0.7: return "B+ (보통 상)"
        elif score >= 0.6: return "B (보통)"
        elif score >= 0.5: return "C+ (개선 필요)"
        elif score >= 0.3: return "C (상당한 개선 필요)"
        elif score >= 0.2: return "D+ (대폭 개선 필요)"
        else: return "D (품질 매우 낮음)"
    
    print(f"\n📊 최종 등급:")
    print(f"   IMG_4793: {get_quality_grade(img_4793_scores['overall_score'])}")
    print(f"   IMG_4794: D (품질 매우 낮음)")

if __name__ == "__main__":
    main()