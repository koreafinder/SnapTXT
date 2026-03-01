#!/usr/bin/env python3
"""EasyOCR 워커 - Stage2/Stage3 모듈을 호출하는 경량 프로세스 분리 스크립트."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Iterable, List

import easyocr

from snaptxt.postprocess.stage2 import Stage2Config, apply_stage2_rules
from snaptxt.postprocess.stage3 import Stage3Config, apply_stage3_rules


LOGGER = logging.getLogger("snaptxt.backend.worker.easyocr")
_STAGE2_LOGGER = LOGGER.getChild("stage2")
_STAGE3_LOGGER = LOGGER.getChild("stage3")

__all__ = ["process_image_easyocr", "main", "advanced_korean_text_processor"]


def setup_environment() -> bool:
    """Ensure PyTorch DLL 경로가 subprocess에서도 올바르게 등록되도록 한다."""

    try:
        torch_dir = Path(sys.executable).parent / "Lib" / "site-packages" / "torch" / "lib"
        if torch_dir.exists():
            current = os.environ.get("PATH", "")
            torch_path = str(torch_dir)
            if torch_path not in current:
                os.environ["PATH"] = f"{torch_path}{os.pathsep}{current}"
                LOGGER.info("PATH에 torch DLL 경로 추가: %s", torch_path)
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(torch_path)
        return True
    except Exception as exc:  # pragma: no cover - 환경 의존
        LOGGER.warning("PyTorch DLL 경로 설정 경고: %s", exc)
        return False


def _parse_languages(arg: str | None) -> List[str]:
    if not arg:
        return ["ko", "en"]
    for delimiter in ("+", ","):
        if delimiter in arg:
            return [token.strip() for token in arg.split(delimiter) if token.strip()]
    return [arg.strip()]


def _run_stage2(text: str) -> str:
    cfg = Stage2Config(logger=_STAGE2_LOGGER)
    return apply_stage2_rules(text, cfg)


def _run_stage3(text: str) -> str:
    """안전한 Stage3: paragraph_formatting만 비활성화한 버전"""
    cfg = Stage3Config(
        enable_spacing_normalization=True,    # ✅ 안전
        enable_character_fixes=True,          # ✅ 안전  
        enable_ending_normalization=True,     # ✅ 안전
        enable_paragraph_formatting=False,    # 🚨 비활성화 - 텍스트 삭제 방지
        enable_spellcheck_enhancement=True,   # ✅ 안전
        enable_punctuation_normalization=True, # ✅ 안전
        logger=_STAGE3_LOGGER,
    )
    return apply_stage3_rules(text, cfg)


def advanced_korean_text_processor(text: str) -> str:
    """안전한 Stage2 + Stage3 파이프라인 (paragraph_formatting 비활성화)"""

    if not text:
        print(f"🔍 [DEBUG] 빈 텍스트 입력", file=sys.stderr)
        return ""

    print(f"🔍 [DEBUG] 처리 전: {len(text)}자", file=sys.stderr)
    
    # 기본 정규화
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Stage2 실행
    stage2_result = _run_stage2(text)
    print(f"🔍 [DEBUG] Stage2 후: {len(stage2_result)}자", file=sys.stderr)
    
    # 안전한 Stage3 실행 (paragraph_formatting 비활성화)
    stage3_result = _run_stage3(stage2_result)
    print(f"🔍 [DEBUG] 안전한 Stage3 후: {len(stage3_result)}자", file=sys.stderr)
    
    # 라인 정리
    lines = [line.strip() for line in stage3_result.split("\n") if line.strip()]
    result = "\n".join(lines)
    print(f"🔍 [DEBUG] 최종 결과: {len(result)}자", file=sys.stderr)
    
    return result


def normalize_spacing_overseparation(text: str) -> str:
    cfg = Stage3Config(
        enable_spacing_normalization=True,
        enable_character_fixes=False,
        enable_ending_normalization=False,
        enable_spellcheck_enhancement=False,
        enable_punctuation_normalization=False,
        logger=_STAGE3_LOGGER,
    )
    return apply_stage3_rules(text, cfg)


def fix_clear_character_errors(text: str) -> str:
    cfg = Stage3Config(
        enable_spacing_normalization=False,
        enable_character_fixes=True,
        enable_ending_normalization=False,
        enable_spellcheck_enhancement=False,
        enable_punctuation_normalization=False,
        logger=_STAGE3_LOGGER,
    )
    return apply_stage3_rules(text, cfg)


def normalize_korean_endings(text: str) -> str:
    cfg = Stage3Config(
        enable_spacing_normalization=False,
        enable_character_fixes=False,
        enable_ending_normalization=True,
        enable_spellcheck_enhancement=False,
        enable_punctuation_normalization=False,
        logger=_STAGE3_LOGGER,
    )
    return apply_stage3_rules(text, cfg)


def _build_reader(languages: Iterable[str]) -> easyocr.Reader:
    return easyocr.Reader(list(languages), gpu=False, verbose=False)


def _postprocess_blocks(blocks: Iterable[str]) -> str:
    joined = "\n".join(block.strip() for block in blocks if isinstance(block, str) and block.strip())
    print(f"🔍 [DEBUG] joined text 길이: {len(joined)}", file=sys.stderr)
    print(f"🔍 [DEBUG] joined text 미리보기: {joined[:100]}...", file=sys.stderr)
    
    # 안전한 Stage2 + Stage3 후처리 (paragraph_formatting 비활성화)
    processed = advanced_korean_text_processor(joined)
    print(f"🔍 [DEBUG] 후처리 완료: {len(processed)}자", file=sys.stderr)
    print(f"🔍 [DEBUG] 후처리 결과 미리보기: {processed[:100]}...", file=sys.stderr)
    
    return processed


def process_image_easyocr(image_path: str, languages: List[str] | None = None) -> dict:
    """EasyOCR 결과를 Stage2/Stage3 후처리까지 거쳐 JSON 호환 dict로 반환한다."""

    image = Path(image_path)
    if not image.exists():
        return {
            "success": False,
            "error": f"이미지 파일을 찾을 수 없습니다: {image_path}",
            "engine": "easyocr",
        }

    langs = languages or ["ko", "en"]
    start = time.time()

    try:
        reader = _build_reader(langs)
        raw_blocks = reader.readtext(
            str(image),
            detail=0,
            paragraph=True,
            width_ths=0.9,
            height_ths=0.9,
            x_ths=0.3,
            y_ths=0.3,
        )
        cleaned_text = _postprocess_blocks(raw_blocks)
        return {
            "success": True,
            "text": cleaned_text,
            "details": raw_blocks,
            "total_blocks": len(raw_blocks),
            "engine": "easyocr",
            "execution_time": round(time.time() - start, 3),
        }
    except Exception as exc:  # pragma: no cover - easyocr 내부 오류
        LOGGER.error("EasyOCR 처리 실패: %s", exc)
        return {
            "success": False,
            "error": f"EasyOCR 처리 실패: {exc}",
            "engine": "easyocr",
        }


def main() -> None:
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": "사용법: python easyocr_worker.py <image_path> [languages]",
                },
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    setup_environment()

    image_path = sys.argv[1]
    languages = _parse_languages(sys.argv[2] if len(sys.argv) > 2 else None)

    result = process_image_easyocr(image_path, languages)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()