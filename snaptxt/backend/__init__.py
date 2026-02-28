"""Backend scaffolding for OCR pipelines and workers."""

from .ocr_pipeline import OCRPipeline, OCRPipelineConfig, PipelineResult, run_pipeline

__all__ = [
    "OCRPipeline",
    "OCRPipelineConfig",
    "PipelineResult",
    "run_pipeline",
]
