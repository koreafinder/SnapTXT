"""Common OCR pipeline service that wraps legacy engines."""

from __future__ import annotations

import logging
import time

from dataclasses import dataclass, asdict, replace
from pathlib import Path
from typing import Any, Dict, Optional, Union

from snaptxt.postprocess import Stage2Config, Stage3Config, run_pipeline as run_postprocess

from . import multi_engine
from .logging import get_json_logger, log_event


PathLike = Union[str, Path]


@dataclass(slots=True)
class OCRPipelineConfig:
    """Runtime configuration for the shared OCR service."""

    languages: tuple[str, ...] = ("ko", "en")
    preprocessing_level: int = 1
    enable_postprocess: bool = True
    stage2_config: Optional[Stage2Config] = None
    stage3_config: Optional[Stage3Config] = None
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
        self.logger = logging.getLogger(__name__)
        self.audit_logger = get_json_logger("snaptxt.backend.pipeline")

    def process_path(self, file_path: PathLike) -> PipelineResult:
        """Process a single image path and return structured output."""

        normalized_path = str(Path(file_path))
        start_time = time.perf_counter()
        engine_settings = self._build_engine_settings()
        log_event(
            self.audit_logger,
            "pipeline.process.start",
            source=normalized_path,
            languages=list(self.config.languages),
            preprocessing_level=self.config.preprocessing_level,
            enable_postprocess=self.config.enable_postprocess,
        )
        raw_text = self._engine.process_file(normalized_path, engine_settings)
        final_text = self._apply_postprocess(raw_text)
        success = self._infer_success(final_text)
        metadata = {
            "engine_settings": engine_settings,
            "config": asdict(self.config),
            "postprocess": {"enabled": self.config.enable_postprocess},
        }
        log_event(
            self.audit_logger,
            "pipeline.process.complete",
            source=normalized_path,
            success=success,
            text_length=len(final_text),
            duration=round(time.perf_counter() - start_time, 3),
        )
        return PipelineResult(
            success=success,
            text=final_text,
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

    def _apply_postprocess(self, text: str) -> str:
        if not self.config.enable_postprocess:
            return text

        stage2_cfg = self._resolve_stage2_config()
        stage3_cfg = self._resolve_stage3_config()
        return run_postprocess(text, stage2_config=stage2_cfg, stage3_config=stage3_cfg, logger=self.logger)

    def _resolve_stage2_config(self) -> Stage2Config:
        base = self.config.stage2_config or Stage2Config()
        return replace(base, logger=self.logger)

    def _resolve_stage3_config(self) -> Stage3Config:
        base = self.config.stage3_config or Stage3Config()
        return replace(base, logger=self.logger)


def run_pipeline(source: PathLike, config: Optional[OCRPipelineConfig] = None) -> PipelineResult:
    """Convenience wrapper to process a path with the default pipeline."""

    pipeline = OCRPipeline(config=config)
    return pipeline.process_path(source)
