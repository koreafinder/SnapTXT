# 🔧 Tesseract OCR 설치 가이드

## 📥 1단계: Tesseract 실행파일 다운로드

### Windows 설치파일 다운로드
- **링크**: https://github.com/UB-Mannheim/tesseract/wiki
- **추천**: `tesseract-ocr-w64-setup-5.3.3.20231005.exe` (64bit)

## 🎯 2단계: 설치 시 중요 설정

### 설치 옵션 선택
1. **기본 경로 사용**: `C:\Program Files\Tesseract-OCR\`
2. **Important**: "Additional language data" 체크 ✅
3. **Korean (kor)** 언어팩 선택 ✅
4. **English (eng)** 언어팩 선택 ✅

## 🔧 3단계: 환경변수 설정 (선택사항)

### PATH 환경변수 추가 (자동으로 안 될 경우)
```
C:\Program Files\Tesseract-OCR\
```

## ✅ 4단계: 설치 확인

### 명령 프롬프트에서 테스트
```bash
tesseract --version
tesseract --list-langs
```

### 한국어 지원 확인
```
kor     # 이 항목이 있어야 함
eng     # 영어도 있어야 함
```

## 🚀 5단계: PC 앱에서 테스트

1. PC 앱 재실행: `py pc_app.py`
2. 폴더 추가 → 이미지 폴더 선택
3. **Tesseract (고정밀)** 체크 ✅
4. OCR 시작

---

## 💡 문제 해결

### "tesseract is not found" 오류 시
1. 설치 경로 확인: `C:\Program Files\Tesseract-OCR\tesseract.exe`
2. 환경변수 PATH 확인
3. cmd에서 `tesseract --version` 실행 테스트

### 한국어 인식 안 될 시
1. `tesseract --list-langs` 확인
2. `kor` 언어팩 없으면 수동 다운로드:
   - https://github.com/tesseract-ocr/tessdata/raw/main/kor.traineddata
   - `C:\Program Files\Tesseract-OCR\tessdata\` 폴더에 복사

---

## ⏱️ 예상 소요시간: 5-10분