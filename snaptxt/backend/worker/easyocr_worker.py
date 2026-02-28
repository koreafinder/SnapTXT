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
    cfg = Stage3Config(
        enable_spacing_normalization=True,
        enable_character_fixes=True,
        enable_ending_normalization=True,
        enable_paragraph_formatting=True,  # 문단 나누기 활성화
        logger=_STAGE3_LOGGER,
    )
    return apply_stage3_rules(text, cfg)


def advanced_korean_text_processor(text: str) -> str:
    """Stage 2 + Stage 3 파이프라인을 실행하고 기본 정리를 적용한다."""

    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _run_stage2(text)
    text = _run_stage3(text)
    
    # 추가적인 직접 수정
    import re
    text = re.sub(r'을\s*컷\s*고', '올랐고', text)
    text = re.sub(r'WW\s+www\.\s*untetheredsoul\.\s*com', 'www.untetheredsoul.com', text)
    text = re.sub(r'두\s*엇\s*던', '두었던', text)
    text = re.sub(r'자아\s*을', '자아를', text) 
    text = re.sub(r'이후세속적인', '이후 세속적인', text)
    text = re.sub(r'젓이다', '것이다', text)  # 핵심 패턴
    text = re.sub(r'수앍게', '수 있게', text)
    text = re.sub(r'되므로이', '되므로 이', text)
    text = re.sub(r'일지률', '일지를', text)
    text = re.sub(r'일지롭다', '일지를 다', text)
    
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


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
    return advanced_korean_text_processor(joined)


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