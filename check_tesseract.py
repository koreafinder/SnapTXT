#!/usr/bin/env python3
"""
Tesseract 한국어 언어팩 설치 확인 스크립트
"""

try:
    import pytesseract
    
    print("🔍 Tesseract 정보 확인")
    print("=" * 50)
    
    try:
        version = pytesseract.get_tesseract_version()
        print(f"📌 Tesseract 버전: {version}")
    except Exception as e:
        print(f"❌ 버전 확인 실패: {e}")
    
    try:
        languages = pytesseract.get_languages(config='')
        print(f"📋 지원 언어 수: {len(languages)}개")
        print("📝 설치된 언어:")
        for i, lang in enumerate(sorted(languages)):
            print(f"   {i+1:2d}. {lang}")
            
        # 한국어 확인
        if 'kor' in languages:
            print("\n✅ 한국어 언어팩이 설치되어 있습니다!")
        else:
            print("\n❌ 한국어 언어팩이 없습니다.")
            print("💡 설치 방법:")
            print("   1. https://github.com/tesseract-ocr/tessdata 에서 kor.traineddata 다운로드")
            print("   2. Tesseract 설치 폴더의 tessdata 폴더에 복사")
            
    except Exception as e:
        print(f"❌ 언어 확인 실패: {e}")
        print("💡 Tesseract가 제대로 설치되지 않았을 수 있습니다.")
        
except ImportError:
    print("❌ pytesseract 모듈을 찾을 수 없습니다.")
    print("설치 명령어: pip install pytesseract")

print("\n" + "=" * 50)