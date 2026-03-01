#!/usr/bin/env python3
"""Stage3 규칙별 디버깅 스크립트 - 어떤 규칙이 텍스트를 삭제하는지 확인"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from snaptxt.postprocess.stage3 import apply_stage3_rules, Stage3Config
from snaptxt.postprocess.stage2 import apply_stage2_rules, Stage2Config

def test_stage3_rules():
    """Stage3 각 규칙을 개별적으로 테스트하여 문제 규칙 식별"""
    
    # IMG_4793.JPG에서 Stage2까지 처리된 텍스트 (620자 → 628자)
    test_text = '''서문
가장 진실한 자아름 만나기 위한여정
"참문 성장을 위해서논 마음의 소리가 곧 내가 아니고 나는 그 소리들 듣는 자임올 깨닫는 것이 가장 중요하다"   -마이름 A 싫어
처음 (상처받지 않은 영혼) 올 쓰러고 햇을 때 내 의도는 아주 단순있다 온
전한 내면의 자유로 향하는 여정올 기꺼이 그 킬로 걷고자 하는 사람들과
나누고 싶없다 영적 성장은 단순하고 명확해야 하여, 직관적으로 알 수 잎
어야 한다 자유는 세상에서 가장 자연스러운 상태다 사실 타고난 권리이
기도 하다: 문제는 우리의 마음과 감정의 선호가 그 간단한 진실올 이해하
기 어렵게 만듣다는 점이다 (상처받지 않은 영혼 은 우리 안에 내재된 진
실올 직접적으로 경험할 수 있는 여정으로 우리름 안내한다 우리 아난 것
올 놓아버길 때, 우리논 비로소 우리가 누구인지틀 발견할 수 있다 이 깊은
내면으로의 여정은 신비주의자나 학자에계만 해당하는 이야기가 아니다:
이는 참나의 자리로 돌아가늘 여정이며 누구든 함께할 수있다
이제 기쁨 마음으로 (상처받지 않은 영혼) 올 위한 이 아름답고 실용적인
(명상 저널) 올 소개한다 이 일지논 여러분의 내면으로 여행할 수 잎게 안내
해 주는 이상적인 수단이 덜 것이다 우리논이 책올 통해 여러분이 각자의 마'''

    print("🔍 Stage3 규칙별 디버깅")
    print("=" * 60)
    print(f"📝 원본 텍스트 길이: {len(test_text)}자")
    print(f"📝 원본 미리보기: {test_text[:100]}...")
    print()

    # Stage3 각 기능을 개별적으로 테스트
    stage3_features = [
        ("spacing_normalization", "띄어쓰기 정규화"),
        ("character_fixes", "문자 오류 수정"),
        ("ending_normalization", "어미 정규화"),
        ("paragraph_formatting", "문단 나누기"),
        ("spellcheck_enhancement", "맞춤법 검사"),
        ("punctuation_normalization", "구두점 정규화"),
    ]
    
    results = {}
    
    for feature_name, feature_desc in stage3_features:
        print(f"\n🧪 테스트: {feature_desc} ({feature_name})")
        print("-" * 50)
        
        try:
            # 해당 기능만 활성화
            config_kwargs = {
                "enable_spacing_normalization": False,
                "enable_character_fixes": False, 
                "enable_ending_normalization": False,
                "enable_paragraph_formatting": False,
                "enable_spellcheck_enhancement": False,
                "enable_punctuation_normalization": False,
            }
            config_kwargs[f"enable_{feature_name}"] = True
            
            cfg = Stage3Config(**config_kwargs)
            result = apply_stage3_rules(test_text, cfg)
            
            print(f"   ✅ 처리 성공")
            print(f"   📊 결과 길이: {len(result)}자 (원본: {len(test_text)}자)")
            print(f"   📝 결과 미리보기: {result[:100]}...")
            
            if len(result) == 0:
                print(f"   🚨 경고: {feature_desc}에서 모든 텍스트가 사라짐!")
                results[feature_name] = "DANGEROUS"
            elif len(result) < len(test_text) // 2:
                print(f"   ⚠️  경고: {feature_desc}에서 텍스트가 크게 줄어듦!")
                results[feature_name] = "RISKY"
            else:
                print(f"   ✅ {feature_desc} 안전함")
                results[feature_name] = "SAFE"
                
        except Exception as e:
            print(f"   ❌ 오류: {e}")
            results[feature_name] = f"ERROR: {e}"
    
    # 전체 Stage3 테스트 (모든 기능 활성화)
    print(f"\n🧪 테스트: 전체 Stage3 (모든 기능 활성화)")
    print("-" * 50)
    
    try:
        cfg_full = Stage3Config(
            enable_spacing_normalization=True,
            enable_character_fixes=True,
            enable_ending_normalization=True,
            enable_paragraph_formatting=True,
            enable_spellcheck_enhancement=True,
            enable_punctuation_normalization=True,
        )
        result_full = apply_stage3_rules(test_text, cfg_full)
        
        print(f"   📊 전체 Stage3 결과 길이: {len(result_full)}자")
        print(f"   📝 결과 미리보기: {result_full[:100]}...")
        results["full_stage3"] = "SAFE" if len(result_full) > 0 else "DANGEROUS"
        
    except Exception as e:
        print(f"   ❌ 전체 Stage3 오류: {e}")
        results["full_stage3"] = f"ERROR: {e}"
    
    # 결과 요약
    print(f"\n📊 Stage3 규칙별 안전성 분석 결과")
    print("=" * 60)
    
    dangerous_rules = []
    risky_rules = []
    safe_rules = []
    
    for feature, status in results.items():
        if feature == "full_stage3":
            continue
            
        feature_desc = next((desc for name, desc in stage3_features if name == feature), feature)
        
        if status == "DANGEROUS":
            dangerous_rules.append(feature_desc)
            print(f"🚨 위험: {feature_desc} - 텍스트 완전 삭제")
        elif status == "RISKY":
            risky_rules.append(feature_desc)
            print(f"⚠️  위험: {feature_desc} - 텍스트 대량 삭제")
        elif status == "SAFE":
            safe_rules.append(feature_desc)
            print(f"✅ 안전: {feature_desc}")
        else:
            print(f"❌ 오류: {feature_desc} - {status}")
    
    print(f"\n🎯 권장사항:")
    if dangerous_rules:
        print(f"   🚨 즉시 비활성화 필요: {', '.join(dangerous_rules)}")
    if risky_rules:
        print(f"   ⚠️  주의깊게 검토 필요: {', '.join(risky_rules)}")
    if safe_rules:
        print(f"   ✅ 안전하게 사용 가능: {', '.join(safe_rules)}")

if __name__ == "__main__":
    test_stage3_rules()