"""Postprocessing package scaffolding."""

import logging

from .stage2 import Stage2Config, apply_stage2_rules
from .stage3 import Stage3Config, apply_stage3_rules
from .formatting import clean_special_characters, finalize_output
from .patterns.stage2_rules import reload_replacements as reload_stage2_rules
from .patterns.stage3_rules import reload_rules as reload_stage3_rules

__all__ = [
    "Stage2Config",
    "Stage3Config",
    "apply_stage2_rules",
    "apply_stage3_rules",
    "finalize_output",
    "clean_special_characters",
    "reload_stage2_rules",
    "reload_stage3_rules",
    "run_pipeline",
]


def run_pipeline(
    text: str,
    *,
    stage2_config: Stage2Config | None = None,
    stage3_config: Stage3Config | None = None,
    logger: logging.Logger | None = None,
) -> str:
    """Run postprocessing stages sequentially with optional configs/logging."""

    log = logger or logging.getLogger(__name__)
    stage2_cfg = stage2_config or Stage2Config(logger=log)
    stage3_cfg = stage3_config or Stage3Config(logger=log)

    log.info("Starting Stage 2 postprocessing")
    stage2 = apply_stage2_rules(text, stage2_cfg)
    log.info("Starting Stage 3 postprocessing")
    stage3 = apply_stage3_rules(stage2, stage3_cfg)
    final_text = finalize_output(stage3, logger=log)
    return final_text
