# 후처리 규칙 관리 가이드

> **최종 업데이트**: 2026-03-02  
> **작성자**: SnapTXT 팀  
> **관련 파일**: `snaptxt/postprocess/patterns/*.yaml`

## 📌 개요

SnapTXT는 **YAML 기반 Hot-Reload 규칙 시스템**으로 코드 재시작 없이 실시간으로 후처리 규칙을 추가/수정할 수 있습니다.

## 🗂️ 규칙 파일 구조

### **Stage2 규칙** (`stage2_rules.yaml`)
```yaml
# 단순 문자 교체
replacements:
  "숨속의": "숲속의"
  "곤민들을": "욕망들을"
```

### **Stage3 규칙** (`stage3_rules.yaml`)
```yaml
spacing:
  fixed_patterns:
    - pattern: '명\s*상\s*가\s*로'
      replacement: '명상가로'
  josas: ["은", "는", "이", "가"]

characters:
  replacements:
    "드러워습니다": "드러났습니다"
  regex:
    - pattern: '\b헐 수 있\b'
      replacement: '할 수 있'
```

## 🚀 새 규칙 추가하기

### **방법 1: YAML 파일 직접 수정** (30초 완료!)

#### **1단계: 파일 열기**
```bash
# Stage2 규칙 수정
notepad snaptxt/postprocess/patterns/stage2_rules.yaml

# Stage3 규칙 수정  
notepad snaptxt/postprocess/patterns/stage3_rules.yaml
```

#### **2단계: 규칙 추가**
```yaml
# Stage3 띄어쓰기 패턴 추가 예시
spacing:
  fixed_patterns:
    - pattern: '새로운\s*오타\s*패턴'    # 👈 여기에 추가
      replacement: '새로운 오타 패턴'
```

#### **3단계: 즉시 적용** (재시작 불필요!)
```python
from snaptxt.postprocess import reload_stage3_rules

# 변경사항 즉시 적용
reload_stage3_rules()
print("새 규칙이 적용되었습니다!")
```

### **방법 2: 환경변수로 실험용 규칙 세트**
```bash
# 실험용 규칙 파일 사용
set SNAPTXT_STAGE3_RULES_FILE=my_experimental_rules.yaml
python main.py  # 새 규칙으로 실행!
```

### **방법 3: PC 앱에서 자동 학습** (개발 예정)
```python
# 사용자 교정을 자동으로 규칙에 추가
def learn_from_user_correction(original: str, corrected: str):
    pattern = extract_pattern(original, corrected)
    append_to_yaml(pattern)
    reload_rules()  # 즉시 적용
```

## 📋 규칙 타입별 가이드

### **Stage2: 단순 교체 규칙**

#### **딕셔너리 교체**
```yaml
replacements:
  "잘못된텍스트": "올바른텍스트"
  "또다른오타": "수정된텍스트"
```

**사용 시기**: 명확하고 일관된 오타가 반복될 때

#### **정규식 교체**  
```yaml
regex:
  - pattern: '\b([0-9]+)([가-힣]+)년\b'
    replacement: '\1\2 년'
```

**사용 시기**: 복잡한 패턴이나 문맥 기반 교체가 필요할 때

### **Stage3: 고급 규칙**

#### **띄어쓰기 정규화**
```yaml
spacing:
  fixed_patterns:
    - pattern: '단어\s*분리\s*패턴'
      replacement: '단어분리패턴'
  
  josas: ["은", "는", "이", "가", "을", "를"]  # 조사 목록
  
  safe_two_char_words: ["사람", "마음", "생활"]  # 안전한 2글자 단어
```

#### **문자 오류 수정**
```yaml
characters:
  replacements:
    "특정오타": "수정결과"
  
  contextual:
    - wrong: "문맥에서만 잘못된"
      correct: "올바른 형태"
  
  regex:
    - pattern: '정규식\s*패턴'
      replacement: '대체결과'
```

#### **어미 정규화 그룹**
```yaml
endings:
  - name: "존댓말"
    patterns:
      - pattern: '습니다(?=\s|$|[.!?])'
        replacement: '습니다'
  
  - name: "과거형"
    patterns:
      - pattern: '했었습니다'
        replacement: '했습니다'
```

## 🧪 테스트 및 검증

### **규칙 추가 후 테스트**
```bash
# Stage3 회귀 테스트 실행
powershell scripts/run_regression.ps1

# 또는 직접 pytest 실행
python -m pytest -m stage3
```

### **특정 규칙 테스트**
```python
# 개별 규칙 테스트
from snaptxt.postprocess import apply_stage3_rules

test_text = "테스트할 텍스트"
result = apply_stage3_rules(test_text)
print(f"입력: {test_text}")
print(f"결과: {result}")
```

### **규칙 변경사항 추적**
```bash
# 규칙 파일 변경사항 비교
python tools/rule_diff.py \
  --stage3-base reports/stage3_rules_baseline_20260301.yaml \
  --stage3-compare snaptxt/postprocess/patterns/stage3_rules.yaml
```

## 🎯 실전 예시

### **예시 1: 새로운 오타 패턴 발견**

**문제**: "마이 클 싱어" → "마이클 싱어"로 교정이 안됨

**해결**:
```yaml
# stage3_rules.yaml에 추가
spacing:
  fixed_patterns:
    - pattern: '마이\s*클\s*싱\s*어'
      replacement: '마이클 싱어'
```

**테스트**:
```python
from snaptxt.postprocess import reload_stage3_rules, apply_stage3_rules

reload_stage3_rules()  # 새 규칙 적용
result = apply_stage3_rules("마이 클 싱 어")
print(result)  # "마이클 싱어"
```

### **예시 2: 도메인별 전문 용어**

**문제**: 의학 도서에서 "심 리 학" → "심리학" 교정 필요

**해결**:
```yaml
# 전문 용어 규칙 추가
spacing:
  fixed_patterns:
    - pattern: '심\s*리\s*학'
      replacement: '심리학'
    - pattern: '물\s*리\s*학'  
      replacement: '물리학'
    - pattern: '화\s*학\s*과'
      replacement: '화학과'
```

### **예시 3: 영어-한국어 혼용 패턴**

**문제**: "Facebook페이지" → "Facebook 페이지"

**해결**:
```yaml
# stage2_rules.yaml에 regex 추가
regex:
  - pattern: '([A-Za-z]+)([가-힣]{2,})'
    replacement: '\1 \2'
```

## ⚡ 빠른 참고

### **자주 사용하는 규칙 패턴**

#### **띄어쓰기 교정**
```yaml
# 과분리 → 올바른 형태
- pattern: '단어1\s*단어2'
  replacement: '단어1단어2'
```

#### **오타 교정**
```yaml
# 자주 발생하는 오타
replacements:
  "드러워습니다": "드러났습니다"
  "돌두했습니다": "몰두했습니다"
```

#### **숫자-문자 조합**
```yaml
# 숫자와 단어 사이 띄어쓰기
- pattern: '([0-9]+)([가-힣]{2,})'
  replacement: '\1 \2'
```

### **규칙 우선순위**
1. **fixed_patterns** (최높음)
2. **replacements**
3. **contextual**
4. **regex** (최낮음)

### **성능 최적화 팁**
- 자주 사용되는 패턴을 위쪽에 배치
- 복잡한 정규식은 마지막에
- 테스트 후에만 운영 적용

## 🚨 주의사항

### **규칙 작성 시 주의점**
1. **정확성**: 정규식 패턴이 의도하지 않은 텍스트에 매치되지 않는지 확인
2. **성능**: 너무 복잡한 패턴은 처리 속도 저하
3. **충돌**: 기존 규칙과 상충되지 않는지 검토
4. **테스트**: 반드시 회귀 테스트 실행

### **롤백 방법**
```bash
# 규칙 파일 백업에서 복원
cp snaptxt/postprocess/patterns/stage3_rules.yaml.backup \
   snaptxt/postprocess/patterns/stage3_rules.yaml

# 즉시 적용
python -c "from snaptxt.postprocess import reload_stage3_rules; reload_stage3_rules()"
```

## 📚 추가 자료

- **[후처리 사용자 가이드](postprocessing_guide.md)**: 기본 사용법
- **[트러블슈팅](postprocessing_troubleshooting.md)**: 문제 해결  
- **정규식 학습**: [regexr.com](https://regexr.com) 추천

---

💡 **몰랐나요?** 규칙을 수정한 후 PC 앱을 재시작할 필요가 없습니다! Hot-reload로 즉시 적용됩니다! 🔥