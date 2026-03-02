# 후처리 트러블슈팅 가이드

> **최종 업데이트**: 2026-03-02  
> **작성자**: SnapTXT 팀  
> **분류**: 문제 해결, 성능 최적화, 디버깅

## 🚨 자주 발생하는 문제들

### **문제 1: 처리 속도가 너무 느림**

**증상**: 
- Stage3 처리가 5초 이상 소요
- PC 앱이 멈춘 것처럼 보임

**원인 및 해결**:

#### **원인 A: 네트워크 기반 맞춤법 검사 지연**
```python
# 해결: 맞춤법 검사 비활성화
from snaptxt.postprocess import Stage3Config

config = Stage3Config(
    enable_spellcheck_enhancement=False  # 👈 네트워크 교정 끄기
)
# 처리 속도: 0.031초 → 0.006초로 개선
```

#### **원인 B: 복잡한 정규식 패턴**
```yaml
# 문제가 되는 패턴 예시 (너무 복잡)
- pattern: '(?:복잡한|정규식|패턴){2,5}\s*(?:[가-힣]+\s*){3,10}(?:패턴)'
  replacement: '간단한대체'

# 해결: 단순화
- pattern: '복잡한\s*정규식\s*패턴'
  replacement: '간단한 대체'
```

#### **원인 C: 너무 많은 규칙**
```bash
# 규칙 개수 확인
wc -l snaptxt/postprocess/patterns/stage3_rules.yaml
# 500줄 이상이면 정리 필요
```

**해결책**:
```python
# 자주 사용되는 패턴만 적용
config = Stage3Config(
    enable_spacing_normalization=True,    # 필수
    enable_character_fixes=True,          # 필수
    enable_ending_normalization=False,    # 선택적 비활성화
    enable_punctuation_normalization=False  # 선택적 비활성화
)
```

### **문제 2: 교정 결과가 이상함**

**증상**:
- "안녕하세요" → "안녕하세 요"로 잘못 분리
- 원래 맞는 단어가 틀리게 바뀜

**디버깅 방법**:
```python
import logging

# 디버그 로깅 활성화
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("debug_postprocess")

config = Stage3Config(logger=logger)
result = apply_stage3_rules("문제가 되는 텍스트", config)

# 로그에서 어떤 단계에서 변경되었는지 확인
```

**자주 발생하는 원인**:

#### **원인 A: 규칙 충돌**
```yaml
# 충돌하는 규칙 예시
spacing:
  fixed_patterns:
    - pattern: '안녕\s*하세요'     # 첫 번째 규칙
      replacement: '안녕하세요'
    - pattern: '안녕하세\s*요'    # 두 번째 규칙 (충돌!)
      replacement: '안녕하세 요'
```

**해결**: 우선순위가 높은 규칙만 남기고 다른 규칙 제거

#### **원인 B: 정규식 과매칭**
```yaml
# 문제: 너무 광범위한 패턴
- pattern: '([가-힣]+)\s+([가-힣]+)'
  replacement: '\1\2'  # 모든 띄어쓰기를 제거 (위험!)

# 해결: 구체적인 패턴
- pattern: '마이클\s+싱어'
  replacement: '마이클 싱어'
```

### **문제 3: 규칙이 적용되지 않음**

**증상**: YAML에 규칙을 추가했는데 변화가 없음

**체크리스트**:

#### **1단계: 파일 경로 확인**
```python
from snaptxt.postprocess.patterns.stage3_rules import rules_file_path

print(f"현재 사용 중인 규칙 파일: {rules_file_path()}")
# 예상과 다른 경로라면 SNAPTXT_STAGE3_RULES_FILE 환경변수 확인
```

#### **2단계: YAML 문법 확인**
```bash
# YAML 문법 검증
python -c "import yaml; yaml.safe_load(open('snaptxt/postprocess/patterns/stage3_rules.yaml'))"
# 오류가 나면 YAML 문법 오류 → 수정 필요
```

#### **3단계: 핫리로드 실행**
```python
from snaptxt.postprocess import reload_stage3_rules

try:
    reload_stage3_rules()
    print("규칙 재로드 성공!")
except Exception as e:
    print(f"규칙 재로드 실패: {e}")
```

#### **4단계: 패턴 매칭 테스트**
```python
import re

# 정규식 패턴이 의도한 텍스트에 매치되는지 확인
pattern = r'테스트\s*패턴'
test_text = '테스트 패턴'

if re.search(pattern, test_text):
    print("패턴 매칭 성공!")
else:
    print("패턴이 매칭되지 않음 - 패턴 수정 필요")
```

### **문제 4: 메모리 사용량 증가**

**증상**: 
- 연속 처리 시 메모리 사용량 계속 증가
- PC 앱이 느려짐

**해결**:
```python
# 명시적 메모리 정리
import gc

def process_batch_images(image_paths):
    for path in image_paths:
        result = process_single_image(path)
        
        # 매 10개마다 메모리 정리
        if len(processed) % 10 == 0:
            gc.collect()
    
    return results
```

### **문제 5: 한글 깨짐 현상**

**증상**: "한글"이 "??????"으로 표시

**원인과 해결**:
```python
# UTF-8 인코딩 강제 설정
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 파일 읽기 시 인코딩 명시
with open('file.txt', 'r', encoding='utf-8') as f:
    text = f.read()
```

## 🔧 성능 최적화

### **최적화 레벨별 가이드**

#### **레벨 1: 기본 최적화 (즉시 적용 가능)**
```python
# 네트워크 의존성 제거
config = Stage3Config(
    enable_spellcheck_enhancement=False  # py-hanspell 비활성화
)
# 성능 향상: 32.77초 → 0.006초
```

#### **레벨 2: 선택적 기능 비활성화**
```python
# 필요한 기능만 활성화
config = Stage3Config(
    enable_spacing_normalization=True,     # 필수: 띄어쓰기 교정
    enable_character_fixes=True,           # 필수: 오타 교정
    enable_ending_normalization=False,     # 선택: 어미 정규화
    enable_punctuation_normalization=False # 선택: 기호 정규화
)
```

#### **레벨 3: 규칙 최적화**
```yaml
# 자주 사용되는 패턴을 위쪽으로
spacing:
  fixed_patterns:
    - pattern: '마이클\s*싱어'      # 👈 가장 빈번한 패턴
      replacement: '마이클 싱어'
    - pattern: '드러워습니다'        # 👈 두 번째로 빈번
      replacement: '드러났습니다'
    # ... 덜 빈번한 패턴들
```

#### **레벨 4: 배치 처리 최적화**
```python
def optimize_batch_processing(texts):
    """여러 텍스트를 효율적으로 처리"""
    
    # 1. 설정 객체 재사용
    config = Stage3Config()
    
    # 2. 규칙을 한번만 로드
    from snaptxt.postprocess.patterns import stage3_rules
    rules = stage3_rules._get_rules()
    
    # 3. 배치로 처리
    results = []
    for text in texts:
        result = apply_stage3_rules(text, config)
        results.append(result)
    
    return results
```

### **성능 측정 도구**

#### **처리 시간 측정**
```python
import time
from contextlib import contextmanager

@contextmanager
def measure_time(stage_name):
    start = time.time()
    yield
    elapsed = time.time() - start
    print(f"{stage_name}: {elapsed:.3f}초")

# 사용 예시
with measure_time("Stage3 처리"):
    result = apply_stage3_rules(text)
```

#### **메모리 사용량 측정**
```python
import tracemalloc

tracemalloc.start()

# 후처리 실행
result = apply_stage3_rules(large_text)

# 메모리 사용량 출력
current, peak = tracemalloc.get_traced_memory()
print(f"현재 메모리: {current / 1024 / 1024:.1f}MB")
print(f"최대 메모리: {peak / 1024 / 1024:.1f}MB")
tracemalloc.stop()
```

## 🐛 디버깅 가이드

### **단계별 디버깅**

#### **1단계: 로그 활성화**
```python
import logging

# 디버그 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Stage별 로거 사용
config = Stage3Config(logger=logging.getLogger("stage3"))
```

#### **2단계: 단계별 결과 확인**
```python
def debug_postprocess_pipeline(text):
    """각 단계별 결과를 출력하며 디버깅"""
    
    print(f"원본: {repr(text)}")
    
    # Stage2
    stage2_result = apply_stage2_rules(text)
    print(f"Stage2: {repr(stage2_result)}")
    
    # Stage3 세부 단계
    config = Stage3Config()
    
    # 띄어쓰기 정규화만
    config.enable_character_fixes = False
    config.enable_ending_normalization = False
    spacing_result = apply_stage3_rules(stage2_result, config)
    print(f"Stage3-spacing: {repr(spacing_result)}")
    
    # 전체 Stage3
    full_result = apply_stage3_rules(text)
    print(f"Stage3-full: {repr(full_result)}")
    
    return full_result
```

#### **3단계: 특정 규칙 테스트**
```python
def test_specific_rule(pattern, replacement, test_cases):
    """특정 규칙이 올바르게 동작하는지 테스트"""
    import re
    
    for test_input, expected in test_cases:
        result = re.sub(pattern, replacement, test_input)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{test_input}' → '{result}' (기대: '{expected}')")
```

### **자주 확인해야 할 로그**

#### **정상 처리 로그**
```
Stage 3-1: spacing normalized (45→42 chars)
Stage 3-2: fixed 3 character issues  
Stage 3-3: applied spellcheck enhancement
```

#### **문제 있는 로그**
```
WARNING: Rule pattern failed to compile: ...
ERROR: YAML syntax error in rules file
WARNING: Spellcheck API timeout after 30s
```

## ⚡ 빠른 문제 해결

### **증상별 즉시 해결법**

| 증상 | 즉시 해결 방법 | 상세 가이드 |
|------|----------------|-------------|
| 💀 **처리가 안됨** | `reload_stage3_rules()` 실행 | [규칙 적용 안됨](#문제-3-규칙이-적용되지-않음) |
| 🐌 **너무 느림** | `enable_spellcheck_enhancement=False` | [성능 최적화](#성능-최적화) |
| 😵 **결과가 이상함** | Debug 로깅 활성화 | [교정 결과 이상](#문제-2-교정-결과가-이상함) |
| 💾 **메모리 부족** | `gc.collect()` 호출 | [메모리 최적화](#문제-4-메모리-사용량-증가) |
| 🔤 **한글 깨짐** | `PYTHONIOENCODING=utf-8` | [인코딩 문제](#문제-5-한글-깨짐-현상) |

### **응급 복구 명령어**
```bash
# 1. 기본 설정으로 되돌리기
git checkout HEAD -- snaptxt/postprocess/patterns/stage3_rules.yaml

# 2. 캐시 강제 재로드
python -c "from snaptxt.postprocess import reload_stage3_rules; reload_stage3_rules()"

# 3. 전체 회귀 테스트
powershell scripts/run_regression.ps1

# 4. 품질 검증
powershell scripts/run_quality_suite.ps1
```

## 📞 추가 지원

### **문의 전 체크리스트**
- [ ] 로그 확인 완료
- [ ] 회귀 테스트 실행 완료  
- [ ] 설정 파일 백업 완료
- [ ] 재현 가능한 테스트 케이스 준비

### **관련 문서**
- **[후처리 사용자 가이드](postprocessing_guide.md)**: 기본 사용법
- **[규칙 관리 가이드](rules_management.md)**: YAML 규칙 수정법
- **[GitHub Issues](../../issues)**: 버그 리포트 및 기능 요청

---

💡 **꿀팁**: 문제가 생겼을 때는 먼저 `reload_stage3_rules()`를 실행해보세요. 90%의 문제가 해결됩니다! ✨