"""경량 EasyOCR 워커용 후처리 하네스.

PC 앱의 EasyOCR 워커는 점진적으로 이 모듈을 통해 공통 Stage 2/3 파이프라인을
호출하도록 전환할 예정이다. 현재는 smoke test와 실험 선행 검증에 사용한다.
"""

from __future__ import annotations

import logging

from snaptxt.postprocess import (
    Stage2Config,
    Stage3Config,
    apply_stage2_rules,
    apply_stage3_rules,
    finalize_output,
)


_DEFAULT_LOGGER = logging.getLogger(__name__)


def run_easyocr_postprocess(
    text: str,
    *,
    stage2_config: Stage2Config | None = None,
    stage3_config: Stage3Config | None = None,
    logger: logging.Logger | None = None,
) -> str:
    """Run Stage 2 + Stage 3 + formatting to mirror the PC EasyOCR worker."""

    log = logger or _DEFAULT_LOGGER
    stage2 = apply_stage2_rules(text, stage2_config or Stage2Config(logger=log))
    stage3 = apply_stage3_rules(stage2, stage3_config or Stage3Config(logger=log))
    return finalize_output(stage3, logger=log)
