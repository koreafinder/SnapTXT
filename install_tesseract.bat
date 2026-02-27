@echo off
echo ⚡ Windows용 Tesseract OCR 자동 설치 스크립트
echo ===============================================
echo.

echo 📋 설치 방법:
echo 1. Chocolatey 사용 (권장)
echo 2. 수동 다운로드
echo.

echo 🍫 방법 1: Chocolatey로 설치 (관리자 권한 필요)
echo    choco install tesseract
echo.

echo 📥 방법 2: 수동 설치
echo    1. https://github.com/UB-Mannheim/tesseract/wiki 방문
echo    2. Windows용 installer 다운로드 
echo    3. 설치 시 "Additional language data" 체크 (한국어 포함)
echo    4. 기본 경로: C:\Program Files\Tesseract-OCR\
echo.

echo 🔧 설치 후 확인:
echo    tesseract --version
echo.

echo 🌏 한국어 언어팩 추가 설치:
echo    https://github.com/tesseract-ocr/tessdata/raw/main/kor.traineddata
echo    위 파일을 C:\Program Files\Tesseract-OCR\tessdata\ 폴더에 복사
echo.

pause