#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
깔끔한 한국어 테스트 이미지 생성기
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

def create_korean_test_image(save_path="test_korean_clean.png"):
    """
    깔끔한 한국어 테스트 이미지 생성
    """
    # 이미지 크기
    width, height = 800, 400
    
    # 흰색 배경 생성
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # 텍스트 내용
    korean_text = [
        "마이클 싱어의 철학",
        "내면의 목소리를 들어보세요",
        "자유로운 마음의 여행",
        "Numbers: 12345 Mixed: Test123",
        "성공적인 한국어 OCR 테스트"
    ]
    
    # 기본 폰트 사용 (시스템에 따라 다를 수 있음)
    try:
        # Windows 한글 폰트 시도
        font = ImageFont.truetype("malgun.ttf", 24)
    except:
        try:
            # 기본 폰트 백업
            font = ImageFont.load_default()
        except:
            font = None
    
    # 텍스트 그리기
    y_pos = 50
    for text in korean_text:
        if font:
            draw.text((50, y_pos), text, font=font, fill='black')
        else:
            # 폰트 로드 실패시 기본 텍스트
            draw.text((50, y_pos), text, fill='black')
        y_pos += 60
    
    # 이미지 저장
    uploads_dir = "uploads"
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
    
    full_path = os.path.join(uploads_dir, save_path)
    image.save(full_path)
    print(f"✅ 테스트 이미지 생성 완료: {full_path}")
    
    return full_path

if __name__ == "__main__":
    create_korean_test_image()