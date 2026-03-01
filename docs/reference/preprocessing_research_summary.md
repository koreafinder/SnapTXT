# OCR 전처리 연구 요약

## 연구 목적
기존의 단순한 레벨 기반 전처리에서 벗어나 과학적이고 평가 기반의 전처리 시스템으로 전환하기 위한 연구

## 주요 OCR 시스템 분석

### 1. PaddleOCR PP-DocLayoutV3
- **핵심 기술**: 불규칙한 문서 레이아웃 위치 지정
- **지원 시나리오**: 기울어짐, 뒤틀림, 스캔, 다양한 조명, 화면 촬영
- **성능**: OmniDocBench에서 94.5% 정밀도
- **특징**: 다중 시나리오 문서 파싱, 적응형 전처리

### 2. Tesseract OCR
- **핵심 기술**: LSTM 기반 현대화된 엔진
- **전처리 중요성**: 이미지 품질 개선 가이드라인 강조
- **권장 사항**: 
  - 최소 300 DPI 해상도
  - 명확한 전경-배경 분리
  - 수평 정렬된 텍스트
  - 높은 대비와 선명도

### 3. OpenCV 전처리 기법
- **단순 Threshold**: THRESH_BINARY, THRESH_BINARY_INV 등
- **적응형 Threshold**: 다양한 조명 조건 처리
- **Otsu's Binarization**: 자동 최적 threshold 값 결정

## 이미지 품질 평가 기준

### 객관적 평가 방법
1. **Full-reference (FR)**: 원본과 비교
2. **Reduced-reference (RR)**: 특징 추출 후 비교  
3. **No-reference (NR)**: 참조 없이 품질 평가

### 핵심 품질 속성
1. **Sharpness (선명도)**: 세부 정보 전달 능력
2. **Noise (노이즈)**: 랜덤 변화, 입자성
3. **Dynamic Range (동적 범위)**: 캡처 가능한 광 레벨 범위
4. **Contrast (대비)**: 톤 재현 곡선의 기울기
5. **Color Accuracy (색상 정확도)**: 색상 응답 측정
6. **Distortion (왜곡)**: 직선의 곡률화

## 과학적 전처리 파이프라인 설계

### Phase 1: 이미지 품질 평가
```python
def assess_image_quality(image):
    metrics = {
        'resolution': check_resolution(image),
        'contrast': calculate_contrast(image),
        'noise_level': estimate_noise(image),
        'sharpness': measure_sharpness(image),
        'skew_angle': detect_skew(image),
        'brightness': analyze_brightness(image)
    }
    return metrics
```

### Phase 2: 조건부 전처리 결정
```python
def decide_preprocessing(quality_metrics):
    preprocessing_steps = []
    
    if quality_metrics['noise_level'] > threshold:
        preprocessing_steps.append('denoise')
    
    if quality_metrics['contrast'] < threshold:
        preprocessing_steps.append('enhance_contrast')
    
    if quality_metrics['skew_angle'] > threshold:
        preprocessing_steps.append('deskew')
        
    return preprocessing_steps
```

### Phase 3: 적응형 전처리 적용
- **노이즈 제거**: 중위 필터, 가우시안 블러
- **대비 향상**: 히스토그램 균등화, 적응형 threshold
- **기울기 보정**: 최소 면적 사각형, 아핀 변환
- **해상도 조정**: 바이큐빅 보간법으로 스케일링

## 구현 계획

### 1단계: 품질 평가 모듈 개발
- 이미지 메트릭 계산 함수들 구현
- 임계값 설정을 위한 실험적 데이터 수집

### 2단계: 조건부 전처리 엔진 구현
- 품질 분석 결과에 따른 전처리 파이프라인 자동 구성
- 여러 전처리 기법의 모듈화

### 3단계: 성능 검증 및 최적화
- 다양한 문서 유형에 대한 테스트
- OCR 정확도 개선 효과 측정
- 처리 시간과 품질의 균형점 찾기

## 기대 효과

1. **정확도 향상**: 이미지별 맞춤형 전처리로 OCR 성능 개선
2. **과처리 방지**: 불필요한 전처리로 인한 품질 저하 방지
3. **자동화**: 수동 조정 없이 최적 전처리 자동 선택
4. **확장성**: 새로운 전처리 기법 쉽게 추가 가능

## 참고 자료

- PaddleOCR PP-DocLayoutV3 문서
- Tesseract 이미지 품질 개선 가이드
- OpenCV Thresholding 튜토리얼
- Wikipedia Image Quality Assessment
- Nanonets OCR 전처리 베스트 프랙티스

## 다음 단계

1. 이미지 품질 평가 모듈 프로토타입 개발
2. 실제 SnapTXT 이미지 샘플로 품질 메트릭 테스트
3. 조건부 전처리 로직 구현
4. A/B 테스트를 통한 성능 검증