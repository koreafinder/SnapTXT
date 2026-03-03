# 📚 SnapTXT 실험 루프 UI - 현실적 MVP 기획서

## 📋 프로젝트 개요

**목표**: **실험 루프 안정화** - "폴더 선택 → 샘플 생성 → GPT Pack → Profile 생성 → Apply Test" 5단계 실험 루프 구축

**Phase 2.8 중심**: Manual Bootstrap, 비용 0원, 로컬 중심, **측정으로 증명하는 시스템**

---

## 🎯 현실적 MVP 원칙 

### ✅ 실험 루프 안정화 (1순위)
- **끊기지 않는 실험**: 각 단계 Worker Thread로 UI 프리징 방지
- **간단 자동화**: 수동 클릭 최소화, 복잡한 AI 기능은 제외  
- **기본 로깅**: 진행 상황 + 에러 발생 시 로그 출력

### ✅ Phase 2.6+2.7 실험 도구
- **CER 분해 측정**: Apply Test로 before/after 정확한 측정
- **구조 복원 증명**: layout_specific 규칙의 실제 효과 검증  
- **실험 속도**: 복잡한 기능보다 빠른 실험 iteration

### ✅ Phase 2 설계 완전 준수
```
기본 샘플: 10장 (7/10/12/15 선택 가능)
분산 전략: 초반 2장 + 중반 6장 + 후반 2장  
품질 필터: 기본 블러 체크만 (간단 버전)
GPT 최적화: 파일 2개(프롬프트+OCR결과) 자동 생성
측정 시스템: Apply Test (CER_all/CER_space_only 분해)
```

---

## 🏗️ 실험 루프 UI 플로우 (현실적 MVP)

### 화면 A: Book Folder Scanner 📁
**목적**: 폴더 선택 + 자동 스캔 + 분산 미리보기

**자동 처리 (간단 버전)**:
```
폴더 선택 → 자동 실행:
1. 이미지 스캔 (중복제거 + 정렬)
2. .snaptxt 디렉토리 생성  
3. book_manifest.json 저장
4. 10장 분산 미리보기 표시
```

**화면 구성**:
- 📁 **폴더 선택** (큰 버튼)
- 📊 **스캔 결과** (총 이미지수 + 경로)
- 📄 **분산 미리보기** (초반2+중반6+후반2)
- ➡️ **다음: 샘플 생성**

**기본 로그**:
```
[15:23:12] 📁 폴더 선택완료: 100장 발견
[15:23:13] 🎯 분산 계획: 초반2+중반6+후반2
```

---

### 화면 B: Sample Generator 🎯  
**목적**: 원클릭으로 10장 샘플 자동 생성

**자동 프로세스 (단순화)**:
```
"🎯 Generate Samples" 클릭 → Worker Thread 실행:

1. 분산 알고리즘 (Phase 2 기준)
   - 초반: 5-15%, 중반: 35-70%, 후반: 80-95%

2. 기본 품질 체크 (간단 버전만)
   - 블러 체크 (OpenCV 라플라시안)
   - 과도한 기준 제외

3. 파일 복사
   - samples/ 디렉토리에 10장 복사
   - sample_01_IMG_4975.jpg 형식
```

**화면 구성**:
- 🎯 **Generate Samples** (진행 바 포함)
- 📊 **진행 상황**: `현재 작업: 7/10 복사 중`
- 🖼️ **썸네일 그리드** (생성되는 대로 표시)
- 🔄 **다시 뽑기** (전체 재생성)

**기본 로그**:
```
[15:25:01] 🎯 샘플 생성 시작 (목표: 10장)
[15:25:02] ✅ IMG_4975.jpg 선정 (블러: OK)
[15:25:03] 📁 복사완료: sample_01_IMG_4975.jpg
[15:25:05] ✅ 샘플 10장 완료
```

---

### 화면 C: GPT Pack Builder 📦
**목적**: GPT 업로드용 파일 2개 자동 생성

**자동 프로세스 (핵심만)**:
```
"📦 Build GPT Pack" 클릭 → 자동 실행:

1. 샘플 10장 OCR 배치
   - 기존 파이프라인 (전처리 + EasyOCR + Stage2/3)
   - Worker Thread로 UI 프리징 방지

2. 파일 생성
   - gpt_input_ocr.txt: 페이지별 블록
   - gpt_prompt.txt: Phase 2.7 구조복원 프롬프트

3. 간단 검증
   - 파일 크기 확인만
```

**화면 구성**:
- 📦 **Build GPT Pack** (메인 버튼)
- ⚡ **OCR 진행**: `7/10 완료 (진행 중...)`
- 📄 **생성 파일**:
  - gpt_input_ocr.txt (45KB)  
  - gpt_prompt.txt (2KB)
- 📋 **업로드 가이드**:
  ```
  1. ChatGPT에 두 파일 업로드
  2. "분석해주세요" 입력
  3. 결과를 다음 화면에 붙여넣기
  ```

**기본 로그**:
```
[15:27:10] 📦 GPT Pack 빌드 시작
[15:27:15] ✅ sample_01 OCR: 245자 추출
[15:28:45] ✅ 파일 생성 완료
```

---

### 화면 D: Profile Builder 🧠
**목적**: GPT 결과 → Book Profile 생성

**자동 프로세스 (기본만)**:
```
GPT 결과 붙여넣기 → 검증 → Profile 생성:

1. 기본 검증
   - 10개 샘플 포함 여부만
   - 너무 짧으면 경고

2. Profile 생성 (기본 규칙)
   - Phase 2.7 layout_specific 추출
   - 기본 패턴만 (복잡한 AI 분석 제외)

3. book_profile.yaml 저장
   - PatternScopePolicy 기본 적용
```

**화면 구성**:
- 📝 **GPT 결과 입력** (대형 텍스트 박스)
- 🔍 **검증 결과**: `✅ 샘플 10개 발견`
- 🧠 **Profile 요약**:
  ```
  📊 생성된 규칙: layout_specific 12개
  📋 스타일: 표준 띄어쓰기
  ```
- 💾 **Profile 저장**

**기본 로그**:
```
[15:30:15] 🧠 Profile 생성 시작
[15:30:16] ✅ 검증: 10/10 샘플 발견
[15:30:17] 💾 book_profile.yaml 저장 완료
```

---

### 🚨 화면 E: Apply Test (CER 분해 측정) 📊  **★ 가장 중요! ★**
**목적**: **Phase 2.6 스타일 CER 분해로 Profile 효과 정확 측정**

**측정 프로세스 (SnapTXT 핵심)**:
```
"📊 Apply Test (Random 5 pages)" 클릭 → 자동 실행:

1. 테스트 샘플 선택
   - 기존 샘플 10장 제외하고 5장 랜덤 선택
   - 분산 유지 (초반/중반/후반 섞어서)

2. Before/After OCR 실행
   - Before: 기본 파이프라인
   - After: 생성된 Book Profile 적용

3. CER 분해 계산
   - CER_all (전체 문자 오류율)
   - CER_space_only (공백 처리 오류율)  
   - CER_punctuation (문장부호 오류율)

4. 개선 효과 측정
   - Phase 2.6+2.7과 동일한 분석
   - 개선율 + 기여도 분석
```

**화면 구성**:
- 📊 **Apply Test** (메인 측정 버튼)
- 🎯 **테스트 샘플**: `5장 자동 선택 (샘플 제외)`
- 📈 **실시간 측정**:
  ```
  Before OCR: 3/5 완료
  After OCR: 1/5 완료  
  ```
- 📋 **CER 분해 결과** (Phase 2.6 스타일):
  ```
  🔍 Profile 효과 측정 (5페이지)
  
  전체 CER:     24.1% → 21.8% (+2.3% 개선) ✅
  ├── 글자 인식: 0.3% → 0.3% (변화 없음)
  ├── 공백 처리: 23.8% → 21.5% (+2.3% 개선) ⭐
  └── 문장부호: 2.1% → 2.1% (변화 없음)
  
  🎯 개선 기여도:
  - layout_specific 규칙: 100% (+2.3%)
  - 전통적 교정: 0%
  
  ✅ Phase 2.7 구조 복원 전략 효과 입증!
  ```
- 🔄 **재측정** (다른 5장으로)
- 💾 **결과 저장** (`test_results.json`)

**측정 로그**:
```
[15:32:10] 📊 Apply Test 시작 (Profile 효과 측정)
[15:32:11] 🎯 테스트 샘플: IMG_5045,IMG_5023,IMG_5067,IMG_5089,IMG_5034
[15:32:12] ⏳ Before OCR 실행 중...
[15:32:45] ⏳ After OCR 실행 중 (Book Profile 적용)...
[15:33:18] 📊 CER 분해 계산 중...
[15:33:20] ✨ 측정 완료: +2.3% 개선 (100% 공백 복원)
[15:33:20] 💾 결과 저장: .snaptxt/logs/test_results_20260302_153320.json
```

---

## 🚀 기술적 구현 (현실적 MVP)

### 1. 기본 자동화 엔진 (복잡한 AI 제외)
```python
class BasicSampleGenerator:
    def __init__(self, logger):
        self.logger = logger  # 기본 로깅만
        
    def generate_samples(self, image_files, target_count=10):
        """단순 자동화 - 복잡한 품질 분석 제외"""
        self.logger.info(f"🎯 샘플 생성 시작 (목표: {target_count}장)")
        
        # 1단계: 분산 계산 (Phase 2 기준)
        total = len(image_files)
        early_start, early_end = int(total * 0.05), int(total * 0.15)
        mid_start, mid_end = int(total * 0.35), int(total * 0.70)  
        late_start, late_end = int(total * 0.80), int(total * 0.95)
        
        # 2단계: 기본 품질 체크 (블러만)
        candidates = []
        for range_start, range_end, count in [
            (early_start, early_end, 2),
            (mid_start, mid_end, 6),
            (late_start, late_end, 2)
        ]:
            range_files = image_files[range_start:range_end]
            selected = self.basic_quality_filter(range_files, count)
            candidates.extend(selected)
        
        # 3단계: 파일 복사
        samples = self.copy_samples_to_directory(candidates)
        self.logger.info(f"✅ 샘플 생성 완료: {len(samples)}장")
        return samples
    
    def basic_quality_filter(self, files, target_count):
        """기본 블러 체크만 - 복잡한 분석 제외"""
        import cv2
        import numpy as np
        
        valid_files = []
        for file in files:
            img = cv2.imread(str(file), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                # 간단한 블러 체크만
                laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
                if laplacian_var > 100:  # 기본 임계값
                    valid_files.append(file)
                    
        return valid_files[:target_count]
```

### 2. Worker Thread 시스템 (UI 프리징 방지)
```python
from PySide6.QtCore import QThread, Signal

class OCRWorker(QThread):
    """OCR 배치 작업 - UI 프리징 방지용"""
    progress = Signal(int, str)  # percent, message
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, samples):
        super().__init__()
        self.samples = samples
        
    def run(self):
        """OCR 배치 실행 - 복잡한 진도 계산 제외"""
        try:
            results = {}
            total = len(self.samples)
            
            for i, sample in enumerate(self.samples):
                self.progress.emit(
                    int((i+1)/total*100), 
                    f"OCR 처리 중: {i+1}/{total}"
                )
                
                # 기본 OCR 실행
                ocr_result = self.run_basic_ocr(sample)
                results[sample.name] = ocr_result
                
            self.finished.emit(results)
            
        except Exception as e:
            self.error.emit(str(e))
```

### 3. 기본 에러 처리 (복잡한 해결책 제안 제외)
```python
class BasicErrorHandler:
    """간단한 에러 처리 - AI 제안 제외"""
    
    def __init__(self, logger):
        self.logger = logger
        
    def handle_error(self, operation, error):
        """기본 에러 로깅 + 사용자 재시도 안내"""
        self.logger.error(f"❌ {operation} 실패: {str(error)}")
        self.logger.info("💡 재시도 또는 다른 샘플 선택하세요")
        return False  # 자동 복구 시도 안함
```

### 4. CER 분해 측정 시스템 (Phase 2.6 기준)
```python
class CERAnalyzer:
    """Phase 2.6 스타일 CER 분해 분석"""
    
    def measure_improvement(self, before_texts, after_texts, ground_truths):
        """Profile 적용 전후 CER 분해 측정"""
        
        results = {
            'before': self.calculate_cer_breakdown(before_texts, ground_truths),
            'after': self.calculate_cer_breakdown(after_texts, ground_truths)
        }
        
        # 개선율 계산
        improvement = {
            'cer_all': results['before']['cer_all'] - results['after']['cer_all'],
            'cer_space_only': results['before']['cer_space_only'] - results['after']['cer_space_only'],
            'cer_punctuation': results['before']['cer_punctuation'] - results['after']['cer_punctuation']
        }
        
        return {
            'before': results['before'],
            'after': results['after'], 
            'improvement': improvement,
            'contribution_analysis': self.analyze_contributions(improvement)
        }
    
    def calculate_cer_breakdown(self, texts, ground_truths):
        """CER_all / CER_space_only / CER_punctuation 분해"""
        # Phase 2.6과 동일한 로직
        pass
        
    def analyze_contributions(self, improvement):
        """개선 기여도 분석 (Phase 2.7 검증용)"""
        total_improvement = improvement['cer_all']
        if total_improvement <= 0:
            return {'layout_specific': 0, 'traditional': 0}
            
        # 공백 개선이 전체 개선의 몇 %인지
        space_contribution = improvement['cer_space_only'] / total_improvement * 100
        return {
            'layout_specific': space_contribution,
            'traditional': 100 - space_contribution
        }
```

---

## 📊 현실적 사용자 경험

### ✅ 실제 사용 플로우 (5단계) **★ Apply Test 추가 ★**
```
1. 📁 폴더 선택
   → 자동: 스캔 + 분산 미리보기 (5초)

2. 🎯 샘플 생성  
   → 자동: 분산 + 기본 품질 + 복사 (30초)

3. 📦 GPT Pack 빌드
   → 자동: OCR + 파일 생성 (2분)

4. 🧠 Profile 생성
   → GPT 결과 입력 → Profile 저장 (10초)

5. 📊 Apply Test ★
   → 자동: 5페이지 측정 + CER 분해 분석 (1분)
```

**총 소요시간**: 약 4분 (기존 수동: 30분)
**핵심 차별점**: **측정으로 증명하는 실험 루프** 🎯

### ✅ MVP 디버깅 시스템 
- **기본 로그**: 각 단계 성공/실패만
- **Worker Thread**: UI 프리징 방지
- **간단 에러**: 재시도 안내만
- **CER 측정**: Phase 2.6+2.7 검증 강화

### ✅ Phase 2 설계 완전 구현
- **10장 분산**: 초반2 + 중반6 + 후반2
- **구조 복원**: Phase 2.7 layout_specific 
- **GPT 최적화**: 파일 업로드 + 구조복원 프롬프트
- **측정 시스템**: CER 분해로 효과 정량화 **★**

---

## 🏆 MVP의 핵심 가치

**실험 루프 완성**: 가설 → 구현 → 측정 → 검증
**속도 우선**: 복잡한 기능 < 빠른 iteration  
**측정 기반**: "만들고 끝" ❌ → "측정으로 증명" ✅
**Phase 2.7 검증**: layout_specific 규칙의 실제 효과 정량화

**SnapTXT 진화**: "OCR 도구" → **"실험으로 증명하는 책 이해 시스템"** 🚀

---

## 🔧 개발 우선순위

1. **1순위**: Apply Test 화면 (CER 분해 측정)  
2. **2순위**: Worker Thread (UI 프리징 방지)
3. **3순위**: 기본 자동화 (복잡한 AI 제외)
4. **나중**: 지능형 기능 (Phase 3에서)

**핵심**: **실험이 끊기지 않는 것**이 가장 중요! 🎯