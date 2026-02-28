and postprocessing logic for every SnapTXT entrypoint.
"""Common OCR pipeline service that wraps legacy engines."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Union

from . import multi_engine


PathLike = Union[str, Path]


@dataclass(slots=True)
class OCRPipelineConfig:
    """Runtime configuration for the shared OCR service."""

    languages: tuple[str, ...] = ("ko", "en")
    preprocessing_level: int = 1
    enable_postprocess: bool = True
    extra_engine_settings: Optional[Dict[str, Any]] = None


@dataclass(slots=True)
class PipelineResult:
    """Standardized response object returned by OCRPipeline."""

    success: bool
    text: str
    source: str
    metadata: Dict[str, Any]


class OCRPipeline:
    """High-level orchestrator that reuses the existing MultiOCRProcessor."""

    def __init__(self, config: Optional[OCRPipelineConfig] = None):
        self.config = config or OCRPipelineConfig()
        self._engine = multi_engine.load_default_engine()

    def process_path(self, file_path: PathLike) -> PipelineResult:
        """Process a single image path and return structured output."""

        normalized_path = str(Path(file_path))
        engine_settings = self._build_engine_settings()
        raw_text = self._engine.process_file(normalized_path, engine_settings)
        success = self._infer_success(raw_text)
        metadata = {
            "engine_settings": engine_settings,
            "config": asdict(self.config),
        }
        return PipelineResult(
            success=success,
            text=raw_text,
            source=normalized_path,
            metadata=metadata,
        )

    def _build_engine_settings(self) -> Dict[str, Any]:
        base_settings = {
            "language": "+".join(self.config.languages),
            "preprocessing_level": self.config.preprocessing_level,
        }
        if self.config.extra_engine_settings:
            base_settings.update(self.config.extra_engine_settings)
        return base_settings

    @staticmethod
    def _infer_success(text: str) -> bool:
        if not isinstance(text, str):
            return False
        stripped = text.strip()
        if not stripped:
            return False
        return not stripped.startswith("❌")


def run_pipeline(source: PathLike, config: Optional[OCRPipelineConfig] = None) -> PipelineResult:
    """Convenience wrapper to process a path with the default pipeline."""

    pipeline = OCRPipeline(config=config)
    return pipeline.process_path(source)
