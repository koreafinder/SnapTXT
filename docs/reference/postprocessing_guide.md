# 후처리 시스템 사용자 가이드

> **최종 업데이트**: 2026-03-02  
> **작성자**: SnapTXT 팀  
> **관련 모듈**: `snaptxt.postprocess`

## 📌 개요

SnapTXT 후처리는 **3단계 파이프라인**으로 OCR 원본 텍스트를 읽기 편한 자연스러운 한국어로 변환합니다.

```
OCR 원본 → Stage2 → Stage3 → Stage3.5 → 최종 결과
```

## 🔄 처리 단계별 기능

### **Stage2: OCR 기본 오류 수정**
**목적**: 명백한 인식 오류와 기본적인 문장 구조 정리

#### **주요 기능**
- **딕셔너리 기반 교체**: `숨속의` → `숲속의`, `곤민들을` → `욕망들을`
- **정규식 패턴 매칭**: 띄어쓰기 패턴, 숫자-문자 조합 정리
- **문맥 인식 교정**: 문장 길이와 키워드 기반 스마트 교정

#### **설정 예시**
```python
from snaptxt.postprocess import Stage2Config, apply_stage2_rules

config = Stage2Config(
    enable_contextual_rules=True,     # 문맥 기반 교정 사용
    enable_spacing_refinements=True   # 띄어쓰기 정제 사용
)

result = apply_stage2_rules("숨속의 명상가로", config)
# 결과: "숲속의 명상가로"
```

### **Stage3: 자연스러운 한국어 복원**
**목적**: 읽기 자연성 100% 달성, 한국어 문법 정규화

#### **주요 기능**
- **띄어쓰기 정규화**: 과분리된 단어 복원 (`숲속 의 명상가 로` → `숲속의 명상가로`)
- **문자 오류 수정**: 457개 패턴 기반 교정 (`드러워습니다` → `드러났습니다`)
- **어미 정규화**: 한국어 문법에 맞는 어미 형태 복원
- **맞춤법 체인**: `py-hanspell` + `pykospacing` + `ftfy` 통합 처리

#### **설정 예시**
```python
from snaptxt.postprocess import Stage3Config, apply_stage3_rules

config = Stage3Config(
    enable_spacing_normalization=True,      # 띄어쓰기 정규화
    enable_character_fixes=True,           # 문자 오류 수정
    enable_spellcheck_enhancement=True,    # 맞춤법 체인 사용
    enable_punctuation_normalization=True  # 기호 정규화
)

result = apply_stage3_rules("드러워습니다 숲속 의 명상가", config)
# 결과: "드러났습니다 숲속의 명상가"
```

### **Stage3.5: TTS 친화적 최적화** (선택사항)
**목적**: 웹 TTS 재생 시 자연스러운 발음과 호흡

#### **주요 기능**
- **문장 경계 정리**: 마침표 뒤 공백, 문장 시작 정리
- **TTS 친화 기호**: 세미콜론 → 쉼표, @ → "제공" 등
- **한국어 인용부호**: `"말"` → `《말》` 스타일 적용
- **숫자 읽기 형태**: `1970년` → `천구백칠십년` (옵션)

#### **설정 예시**
```python
from snaptxt.postprocess.stage3_5 import Stage3_5Config, apply_stage3_5_rules

config = Stage3_5Config(
    enable_sentence_boundary_fix=True,    # 문장 경계 정리
    enable_tts_friendly_symbols=True,     # 기호 변환
    enable_korean_quotes=True,            # 한국어 인용부호
    enable_number_reading_format=False    # 숫자 읽기 변환 (무거움)
)

result = apply_stage3_5_rules("습니다.오프라", config)
# 결과: "습니다. 오프라"
```

## 🚀 통합 사용법

### **기본 사용 (모든 Stage 적용)**
```python
from snaptxt.postprocess import run_pipeline

# 기본 설정으로 전체 파이프라인 실행
result = run_pipeline(ocr_text)
```

### **세부 설정 사용**
```python
from snaptxt.postprocess import (
    Stage2Config, Stage3Config, apply_stage2_rules, apply_stage3_rules
)

# Stage별 개별 실행
stage2_config = Stage2Config(enable_contextual_rules=True)
stage3_config = Stage3Config(enable_spellcheck_enhancement=True)

text = apply_stage2_rules(ocr_text, stage2_config)
result = apply_stage3_rules(text, stage3_config)
```

### **TTS 모드 사용**
```python
from snaptxt.postprocess import Stage3Config
from snaptxt.postprocess.stage3_5 import Stage3_5Config

# TTS 친화적 설정
stage3_config = Stage3Config(
    enable_tts_friendly_processing=True,
    tts_config=Stage3_5Config(
        enable_sentence_boundary_fix=True,
        enable_korean_quotes=True
    )
)

result = apply_stage3_rules(ocr_text, stage3_config)
```

## 🎯 성능 지표

### **품질 달성률** (2026-03-02 기준)
- **읽기 자연성**: 100% 달성 ✅
- **OCR 오류 수정**: 100% 완료 ✅
- **Overall Quality**: 0.991 (99.1%) ✅
- **평균 신뢰도**: 0.982 (98.2%) ✅

### **처리 속도**
- **Stage3 오버헤드**: 평균 0.031초
- **전체 파이프라인**: 평균 32.77초 (인터넷 연결 필요)
- **TTS 추가 처리**: +0.006초

## 🔧 고급 설정

### **커스텀 핸들러 사용**
```python
def my_custom_spellcheck(text: str) -> str:
    # 사용자 정의 맞춤법 교정
    return text.replace("특수패턴", "교정결과")

config = Stage3Config(
    spellcheck_handler=my_custom_spellcheck  # 커스텀 핸들러 주입
)
```

### **로깅 활성화**
```python
import logging

logger = logging.getLogger("my_postprocess")
config = Stage3Config(logger=logger)

# 상세한 처리 과정이 로그에 기록됨
result = apply_stage3_rules(text, config)
```

## ⚡ 빠른 참고

### **자주 사용하는 설정 조합**

#### **1. 고품질 모드 (기본)**
```python
# 모든 교정 기능 활성화 (권장)
Stage3Config()  # 기본값이 최적화됨
```

#### **2. 빠른 처리 모드**
```python
# 네트워크 기반 교정 비활성화
Stage3Config(enable_spellcheck_enhancement=False)
```

#### **3. 실험 모드**
```python
# 특정 기능만 테스트
Stage3Config(
    enable_spacing_normalization=True,
    enable_character_fixes=False,
    enable_spellcheck_enhancement=False
)
```

### **문제 해결**
- 처리 속도가 느림 → [성능 최적화 가이드](postprocessing_troubleshooting.md#성능-최적화) 참고
- 교정 결과가 맞지 않음 → [규칙 관리 가이드](rules_management.md) 참고
- 오류 발생 → [트러블슈팅 가이드](postprocessing_troubleshooting.md) 참고

## 📚 추가 문서

- **[규칙 관리 가이드](rules_management.md)**: YAML 규칙 추가/수정 방법
- **[트러블슈팅](postprocessing_troubleshooting.md)**: 문제 해결 및 성능 최적화
- **[아키텍처](postprocessing_architecture.md)**: 내부 구조와 확장 방법

---

💡 **팁**: 새로운 도메인(학술서적, 소설 등)을 처리할 때는 먼저 샘플 텍스트로 각 Stage를 개별 테스트해보세요!