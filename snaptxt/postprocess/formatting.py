"""Whitespace, punctuation, and safe special-character cleanup helpers."""

from __future__ import annotations

import logging
import re
from typing import Iterable


_ZERO_WIDTH_TRANSLATION = dict.fromkeys(
    map(ord, ["\u200b", "\u200c", "\u200d", "\ufeff"]),
    None,
)

_UNICODE_SPACE_REPLACEMENTS = {
    "\u00a0": " ",  # non-breaking space → regular space
}

_SYMBOL_REPLACEMENTS = {
    "⋅": "·",
    "•": "·",
    "‧": "·",
    "“": '"',
    "”": '"',
    "„": '"',
    "‟": '"',
    "‘": "'",
    "’": "'",
    "‚": "'",
    "‛": "'",
}

_PUNCT_NEED_SPACE_AFTER = ",;:?!."  # do not include middot/em dash to preserve layout


def _normalize_unicode_spaces(text: str) -> str:
    for src, dest in _UNICODE_SPACE_REPLACEMENTS.items():
        text = text.replace(src, dest)
    return text.translate(_ZERO_WIDTH_TRANSLATION)


def _replace_symbols(text: str) -> str:
    for src, dest in _SYMBOL_REPLACEMENTS.items():
        text = text.replace(src, dest)
    return text


def _tidy_line(line: str) -> str:
    if not line:
        return ""

    line = line.replace("\t", " ")
    line = re.sub(r"\s{2,}", " ", line)
    line = re.sub(r'\s+([,;:?!\.])', r"\1", line)
    line = re.sub(r'([,;:?!\.])(?!\s|[\'\"\n])', r"\1 ", line)
    line = re.sub(r'\s+([\)\]\}])', r"\1", line)
    line = re.sub(r'([\(\[\{])(?=\S)', r"\1", line)
    return line.strip()


def _collapse_blank_lines(lines: Iterable[str]) -> str:
    compacted: list[str] = []
    blank = False
    for line in lines:
        if line:
            compacted.append(line)
            blank = False
            continue
        if not blank and compacted:
            compacted.append("")
        blank = True
    return "\n".join(compacted).strip()


def clean_special_characters(
    text: str,
    *,
    logger: logging.Logger | None = None,
) -> str:
    """Remove zero-width chars, normalize punctuation, and collapse spaces safely."""

    log = logger or logging.getLogger(__name__)

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _normalize_unicode_spaces(normalized)
    normalized = _replace_symbols(normalized)

    lines = [_tidy_line(line) for line in normalized.split("\n")]
    result = _collapse_blank_lines(lines)

    if result != text:
        log.debug("Formatting: special-character cleanup applied (%d→%d chars)", len(text), len(result))

    return result


def finalize_output(
    text: str,
    *,
    logger: logging.Logger | None = None,
) -> str:
    """Apply final whitespace cleanup and lightweight TTS-friendly shaping."""

    log = logger or logging.getLogger(__name__)
    cleaned = clean_special_characters(text, logger=log)

    paragraphs = [line.strip() for line in cleaned.split("\n")]
    final_text = _collapse_blank_lines(paragraphs)

    if final_text != text:
        log.debug("Formatting: paragraph shaping applied (%d→%d chars)", len(text), len(final_text))

    return final_text
