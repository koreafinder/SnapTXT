#!/usr/bin/env python3
"""
Mermaid 다이어그램을 JPG 이미지로 변환하는 스크립트 (온라인 API 버전)
"""

import os
import sys
import requests
import base64
import json
from pathlib import Path
from urllib.parse import quote
from PIL import Image
import io

def mermaid_to_jpg(mermaid_file_path: str, output_dir: str = None):
    """Mermaid 파일을 JPG로 변환 (온라인 API 사용)"""
    
    # 파일 경로 설정
    mermaid_path = Path(mermaid_file_path)
    if not mermaid_path.exists():
        print(f"❌ Mermaid 파일을 찾을 수 없습니다: {mermaid_file_path}")
        return False
    
    # 출력 디렉토리 설정
    if output_dir is None:
        output_dir = mermaid_path.parent
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(exist_ok=True)
    
    # Mermaid 코드 읽기
    mermaid_code = mermaid_path.read_text(encoding='utf-8').strip()
    
    try:
        # Mermaid Ink API 사용 (무료 온라인 서비스)
        # URL 인코딩된 mermaid 코드
        encoded_mermaid = quote(mermaid_code)
        
        # API URL 생성
        api_url = f"https://mermaid.ink/img/{encoded_mermaid}"
        
        print(f"🔄 API 호출 중: {mermaid_path.stem}")
        
        # 이미지 다운로드
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        # PNG 이미지 데이터
        png_data = response.content
        
        # PIL로 이미지 처리
        with Image.open(io.BytesIO(png_data)) as png_image:
            # 투명도 제거 (흰 배경으로)
            if png_image.mode == 'RGBA':
                rgb_image = Image.new('RGB', png_image.size, (255, 255, 255))
                rgb_image.paste(png_image, mask=png_image.split()[-1])
            else:
                rgb_image = png_image.convert('RGB')
            
            # PNG 저장
            png_path = output_dir / f"{mermaid_path.stem}.png"
            png_image.save(png_path, 'PNG')
            print(f"✅ PNG 생성 완료: {png_path}")
            
            # JPG 저장
            jpg_path = output_dir / f"{mermaid_path.stem}.jpg"
            rgb_image.save(jpg_path, 'JPEG', quality=95, optimize=True)
            print(f"✅ JPG 생성 완료: {jpg_path}")
            
            return True
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API 호출 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 변환 중 오류 발생: {e}")
        return False


def main():
    """메인 실행 함수"""
    print("🎨 Mermaid to JPG 변환기")
    print("=" * 50)
    
    # 변환할 파일들
    diagram_files = [
        "docs/diagrams/system-overview.mmd",
        "docs/diagrams/ocr-workflow.mmd"
    ]
    
    success_count = 0
    
    for mermaid_file in diagram_files:
        print(f"\n🔄 변환 중: {mermaid_file}")
        
        if mermaid_to_jpg(mermaid_file):
            success_count += 1
        else:
            print(f"❌ 변환 실패: {mermaid_file}")
    
    print(f"\n📊 변환 완료: {success_count}/{len(diagram_files)} 파일")
    
    if success_count > 0:
        print("\n📂 생성된 파일들:")
        output_dir = Path("docs/diagrams")
        for jpg_file in output_dir.glob("*.jpg"):
            print(f"   📄 {jpg_file}")
        for png_file in output_dir.glob("*.png"):
            print(f"   📄 {png_file}")


if __name__ == "__main__":
    main()