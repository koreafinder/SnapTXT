"""Postprocessing package scaffolding."""

from .stage2 import apply_stage2_rules
from .stage3 import apply_stage3_rules
from .formatting import finalize_output

__all__ = [
    "apply_stage2_rules",
    "apply_stage3_rules",
    "finalize_output",
    "run_pipeline",
]


def run_pipeline(text: str) -> str:
    """Run placeholder postprocessing stages sequentially."""
    stage2 = apply_stage2_rules(text)
    stage3 = apply_stage3_rules(stage2)
    final_text = finalize_output(stage3)
    return final_text
