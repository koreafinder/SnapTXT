#!/usr/bin/env python3
"""
Multi OCR Processor - 다중 OCR 엔진 통합 처리기
EasyOCR, Tesseract, PaddleOCR 등을 통합하여 최고의 텍스트 추출 결과 제공
"""

"""Compatibility shim for the relocated MultiOCRProcessor module."""

from __future__ import annotations

from snaptxt.backend.multi_engine import MultiOCRProcessor, load_default_engine

__all__ = ["MultiOCRProcessor", "load_default_engine"]


def main() -> None:
    """Mirror the legacy CLI behavior after relocating the class."""

    processor = MultiOCRProcessor()
    print("🔍 사용 가능한 OCR 엔진:")
    engine_info = processor.get_engine_info()
    for engine, available in engine_info.items():
        status = "✅" if available else "❌"
        print(f"  {status} {engine}")

    test_settings = {'language': 'ko,en'}
    _ = test_settings  # Legacy placeholder to preserve previous side effects
    print("\n✅ MultiOCRProcessor 초기화 완료!")


if __name__ == "__main__":
    main()