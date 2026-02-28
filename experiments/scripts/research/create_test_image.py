#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PC 앱 OCR 테스트용 이미지 생성
"""

from PIL import Image, ImageDraw, ImageFont
import os

print("📸 PC 앱 OCR 테스트용 이미지 생성 중...")

# 테스트 이미지 생성
img = Image.new('RGB', (800, 600), color='white')
draw = ImageDraw.Draw(img)

try:
    # 한글과 영어가 모두 포함된 텍스트
    font_large = ImageFont.truetype("malgun.ttf", 36)  # 한글 폰트 
    font_medium = ImageFont.truetype("arial.ttf", 28)
except:
    font_large = ImageFont.load_default()
    font_medium = font_large

# 다양한 텍스트 작성
draw.text((50, 80), "SnapTXT OCR 테스트", fill='black', font=font_large)
draw.text((50, 150), "HELLO EASYOCR", fill='navy', font=font_medium)  
draw.text((50, 220), "안녕하세요 한글 테스트", fill='darkgreen', font=font_large)
draw.text((50, 290), "Numbers: 12345", fill='red', font=font_medium)
draw.text((50, 360), "Mixed: 한영혼합 Test123", fill='purple', font=font_medium)
draw.text((50, 430), "성공적으로 작동합니다!", fill='blue', font=font_large)

# uploads 디렉토리에 저장
os.makedirs("uploads", exist_ok=True)
output_path = os.path.join("uploads", "test_ocr_image.png")
img.save(output_path, "PNG")

print(f"✅ 테스트 이미지 생성 완료: {output_path}")
print("📋 포함된 텍스트:")
print("  - 'SnapTXT OCR 테스트'")
print("  - 'HELLO EASYOCR'") 
print("  - '안녕하세요 한글 테스트'")
print("  - 'Numbers: 12345'")
print("  - 'Mixed: 한영혼합 Test123'")
print("  - '성공적으로 작동합니다!'")
print("\n🎯 이제 PC 앱에서 이 이미지를 업로드하여 OCR 테스트를 진행하세요!")