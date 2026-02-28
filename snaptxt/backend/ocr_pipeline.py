"""Common OCR pipeline placeholders.

This module will eventually orchestrate preprocessing, engine calls,
and postprocessing logic for every SnapTXT entrypoint.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class OCRPipelineConfig:
    """Minimal configuration placeholder for future expansion."""

    languages: tuple[str, ...] = ("ko", "en")
    enable_postprocess: bool = True


def run_pipeline(source: Any, config: Optional[OCRPipelineConfig] = None) -> Dict[str, Any]:
    """Placeholder pipeline entrypoint to be implemented in upcoming stages."""
    if config is None:
        config = OCRPipelineConfig()
    raise NotImplementedError(
        f"Pipeline stub reached for source={type(source)!r} with config={config}"
    )
