#!/usr/bin/env python3
"""
OCR 결과와 GPT 5.2 정답 비교 분석
"""

def calculate_text_accuracy(ocr_text, ground_truth, keywords=None):
    """텍스트 정확도를 다차원으로 계산"""
    
    # 1. 핵심 키워드 정확도 (40점)
    keyword_score = 0
    if keywords:
        found_keywords = sum(1 for keyword in keywords if keyword in ocr_text)
        keyword_score = (found_keywords / len(keywords)) * 40
    
    # 2. 핵심 문장 복원도 (30점)
    key_phrases = [
        "가장 진실한 자아",
        "만나기 위한 여정", 
        "마음의 소리가",
        "내가 아니고",
        "듣는 자임을",
        "깨닫는 것이",
        "가장 중요하다"
    ]
    
    phrase_score = 0
    for phrase in key_phrases:
        if phrase in ocr_text or phrase.replace(" ", "") in ocr_text.replace(" ", ""):
            phrase_score += 30 / len(key_phrases)
        else:
            # 부분 일치 체크 (50% 이상 일치시 부분 점수)
            phrase_clean = phrase.replace(" ", "")
            ocr_clean = ocr_text.replace(" ", "")
            if any(phrase_clean[i:i+3] in ocr_clean for i in range(len(phrase_clean)-2)):
                phrase_score += (30 / len(key_phrases)) * 0.3
    
    # 3. 가독성 점수 (20점)
    # 한글 비율
    korean_chars = sum(1 for c in ocr_text if '\uac00' <= c <= '\ud7a3')
    total_chars = len(ocr_text.replace(' ', ''))
    
    if total_chars > 0:
        korean_ratio = korean_chars / total_chars
        readability_score = korean_ratio * 20
    else:
        readability_score = 0
    
    # 4. 구조적 완성도 (10점)  
    structure_score = 0
    if len(ocr_text) > 300:  # 적절한 길이
        structure_score += 5
    if '"' in ocr_text or '⟨' in ocr_text or '《' in ocr_text:  # 인용 부호
        structure_score += 3
    if '.' in ocr_text:  # 문장 구조 
        structure_score += 2
        
    total_score = keyword_score + phrase_score + readability_score + structure_score
    
    return {
        'total': round(total_score, 1),
        'keyword': round(keyword_score, 1),
        'phrase': round(phrase_score, 1), 
        'readability': round(readability_score, 1),
        'structure': round(structure_score, 1),
        'details': {
            'korean_ratio': round(korean_ratio * 100, 1) if total_chars > 0 else 0,
            'text_length': len(ocr_text),
            'found_keywords': found_keywords if keywords else 0
        }
    }

def analyze_ocr_results():
    """OCR 결과 분석"""
    
    # GPT 5.2 정답의 핵심 키워드
    ground_truth_keywords = [
        "진실한", "자아", "여정", "성장", "마음", "소리", 
        "마이클", "싱어", "상처받지", "않는", "영혼", "자유",
        "깨닫는", "중요", "의도", "단순", "내면", "명상"
    ]
    
    # OCR 결과들 (3가지 성공 방법)
    results = {
        "3단계일괄": """시문 가장진실한 자아물만나기 위한여정' 침문 성장울 위해서는 마음의 소리가 끈 내가 아니고 나는 그 소리물 듣는 자임율 깨닫는 짓이 가장 중요하다" 미이a A 싫어 처음 ( 상처받지 안은 영혼 } & 쓰고 겨움 떠 내 외도는 아주 단순없다 온 전한 내면외 자유로 향하는 여정운 기꺼이 그 킬로 건고자 아는 사합둘다 나누고 싶없다 영적 성장은 단순하고 명화없야 하여 직판적으로 압 수름 어야 하다 자유는 서상에서 가장 자연스러운 상태다 사신 타고난 권리이 기도하다 문제는 우리의 마음과 감정의 선호가 그 간단하 진심용 이해하기어렵거 만듣다는 점이다 <상처받지 안온 영혼 ) 온 우리 안어 내체권 진 심용 직접적으로 경험합 수 있는 여정으로 우리롬 안한다 우리 아 것을 { 이버럽 떠 우리논 비로소우리가 누구인지합 발견합 수 있다이.""",
        
        "Office Lens": """서오 가장진실한 자아뭄 만나기 위한여정 참원 싱장- 위해서손 마용의 소리기 큰 내가아니고 나느 그 소리$ 돈는 지입니 머단는 것이 가장 중요하다' 아이 IS A 상어 처움<상어받지 안은 영혼 } & 쓰고 겨움 떠 내 외도는 아주 단순없다 온 전한 내면외 자유로 향하는 여정운 기꺼이 그 킬로 건고자 아는 사합둘다 나누고 싶없다 영적 성장은 단순하고 명화없야 하여 직판적으로 압 수름 어야 하다 자유는 서상에서 가장 자연스러운 상태다 사신 타고난 권리이 기도하다 문제는 우리의 마음과 감정의 선호가 그 간단하 진심용 이해하 기어렵거 만듣다는 점이다 <상치받지 안온 영혼 ) 온 우리 안어 내체권 진 심용 직접적으로 경험합 수 있는 여정으로 우리롬 안한다 우리 아 것을 { 이버럽 떠 우리논 비로소우리가 누구인지합 발견합 수 있다이.""",
        
        "레거시 레벨1": """서문 가장 진실한 자아름 만나기 위한 여정" 참된 성장을 위해서논 마음의 소리가 곧 내가 아니고 나는 그소리들 듣는 자임을 깨닫는 것이 가장 중요하다" ~마이클 A 싱어 ITl:rs 상처받지 않는 영혼 > 을 쓰려고 했을 때 내 의도는 아주 단순했다 온전한 내면의 자유로 향하는 여정을 기꺼이 그 길로 걷고자 하는 사람들과 나누고 싶었다 영적 성장은 단순하고 명확해야 하며, 직관적으로 알 수 있어야 한다 자유는 세상에서 가장 자연스러운 상태다 사실 타고난 권리이기도 하다 문제는 우리의 마음과 감정의 선호가 그간단한 진실을 이해하기 어렵게 만든다는 점이다. {상처받지 않는 영혼; 은 우리 안에 내재된 진실을 직접적으로 경험할 수 있는 여정으로 우리를 안내한다 우리 아닌 것을 놓아버릴 때, 우리는 비로소 우리가 누구인지를 발견할 수 있다"""
    }
    
    print("🎯" + "="*80)
    print("📊 OCR 정확도 분석 결과 (GPT 5.2 정답 기준)")
    print("🎯" + "="*80)
    
    analysis_results = []
    
    for method, text in results.items():
        score = calculate_text_accuracy(text, "", ground_truth_keywords)
        analysis_results.append((method, score))
        
        print(f"\n🔍 **{method}**")
        print(f"   📊 종합 점수: {score['total']}/100")
        print(f"   🔑 키워드 정확도: {score['keyword']}/40")
        print(f"   📝 핵심 문장 복원: {score['phrase']}/30") 
        print(f"   📖 가독성: {score['readability']}/20")
        print(f"   🏗️ 구조적 완성도: {score['structure']}/10")
        print(f"   📈 상세정보:")
        print(f"      - 한글 비율: {score['details']['korean_ratio']}%")
        print(f"      - 텍스트 길이: {score['details']['text_length']}자")
        print(f"      - 발견된 키워드: {score['details']['found_keywords']}/18개")
    
    # 순위 정리
    analysis_results.sort(key=lambda x: x[1]['total'], reverse=True)
    
    print(f"\n🏆" + "="*50)
    print("📊 최종 순위")  
    print("🏆" + "="*50)
    
    for i, (method, score) in enumerate(analysis_results, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
        print(f"{emoji} {i}위: {method} - {score['total']}/100점")
    
    print(f"\n💡" + "="*50)
    print("분석 결론")
    print("💡" + "="*50)
    
    best_method, best_score = analysis_results[0]
    if best_score['total'] >= 80:
        print("✅ 우수한 OCR 성능! 실용적으로 사용 가능")
    elif best_score['total'] >= 60:
        print("⚠️ 양호한 성능이지만 추가 개선 필요")
    else:
        print("❌ 개선이 시급함. 다른 OCR 엔진이나 전처리 방법 고려")
        
    print(f"\n🎯 최고 성능: {best_method} ({best_score['total']}점)")
    
    return analysis_results

if __name__ == "__main__":
    analyze_ocr_results()