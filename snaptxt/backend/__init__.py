"""Backend scaffolding for OCR pipelines and workers."""

from .ocr_pipeline import OCRPipeline, OCRPipelineConfig, PipelineResult, run_pipeline
from .multi_engine import MultiOCRProcessor, load_default_engine

__all__ = [
    "OCRPipeline",
    "OCRPipelineConfig",
    "PipelineResult",
    "run_pipeline",
    "MultiOCRProcessor",
    "load_default_engine",
]
