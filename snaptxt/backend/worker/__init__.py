"""Worker package placeholder for EasyOCR and other engines."""

from .easyocr_worker import main as run_easyocr_worker, process_image_easyocr

__all__ = [
	"process_image_easyocr",
	"run_easyocr_worker",
]
