"""Generate OCR quality samples by running the shared pipeline over sample specs."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from snaptxt.backend.ocr_pipeline import OCRPipeline

REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OCR pipeline against predefined samples")
    parser.add_argument(
        "--spec",
        default="experiments/samples/quality_samples.json",
        help="Path to the quality sample definition file (JSON)",
    )
    parser.add_argument(
        "--output",
        default="experiments/results/quality_samples.json",
        help="Destination file for the generated sample results",
    )
    parser.add_argument(
        "--include-text",
        action="store_true",
        help="Store raw text output inside the result file (useful for debugging, increases file size)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-sample console logs",
    )
    return parser.parse_args()


def load_sample_spec(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Sample spec not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Sample spec must be a JSON array")
    if not data:
        raise ValueError("Sample spec is empty; add at least one entry")
    return data


def _compute_length_score(text_length: int, expected_length: Any) -> float | None:
    if text_length is None:
        return None
    try:
        expected = int(expected_length)
    except (TypeError, ValueError):
        return None
    if expected <= 0:
        return None
    ratio = text_length / expected
    return max(0.0, min(ratio, 1.0))


def _compute_keyword_score(text: str, keywords: Sequence[str] | None) -> Tuple[float | None, List[str]]:
    if not keywords:
        return None, []
    normalized = text or ""
    tokens = [kw for kw in keywords if isinstance(kw, str) and kw.strip()]
    if not tokens:
        return None, []
    hits = [kw for kw in tokens if kw in normalized]
    score = len(hits) / len(tokens)
    missing = sorted(set(tokens) - set(hits))
    return score, missing


def _evaluate_quality_components(text: str, text_length: int, spec: Dict[str, Any]) -> Tuple[float | None, Dict[str, float], List[str]]:
    components: Dict[str, float] = {}
    missing_keywords: List[str] = []

    expected_length = spec.get("expected_length")
    length_score = _compute_length_score(text_length, expected_length)
    if length_score is not None:
        components["length_ratio"] = round(length_score, 3)

    keyword_score, missing = _compute_keyword_score(text, spec.get("keywords"))
    if keyword_score is not None:
        components["keyword_hit_rate"] = round(keyword_score, 3)
        missing_keywords = missing

    confidence: float | None = None
    if components:
        confidence = round(sum(components.values()) / len(components), 3)

    if confidence is None:
        confidence = 1.0 if text_length > 0 else 0.0

    return confidence, components, missing_keywords


def run_samples(samples: List[Dict[str, Any]], include_text: bool, quiet: bool) -> List[Dict[str, Any]]:
    pipeline = OCRPipeline()
    results: List[Dict[str, Any]] = []

    for entry in samples:
        sample_id = entry.get("id") or "unknown"
        rel_path = entry.get("path")
        if not rel_path:
            raise ValueError(f"Sample '{sample_id}' is missing the 'path' field")
        source_path = (REPO_ROOT / rel_path).resolve()
        start = time.perf_counter()
        success = False
        text = ""
        error_message = None

        try:
            pipeline_result = pipeline.process_path(str(source_path))
            success = pipeline_result.success
            text = pipeline_result.text or ""
        except Exception as exc:  # pragma: no cover - defensive logging
            success = False
            error_message = str(exc)

        duration = round(time.perf_counter() - start, 3)
        confidence, quality_components, missing_keywords = _evaluate_quality_components(text, len(text), entry)

        record: Dict[str, Any] = {
            "sample_id": sample_id,
            "source": rel_path,
            "success": success,
            "processing_time": duration,
            "text_length": len(text),
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        if entry.get("expected_length") is not None:
            record["expected_length"] = entry.get("expected_length")
        if entry.get("tags"):
            record["tags"] = entry["tags"]
        if entry.get("description"):
            record["description"] = entry["description"]
        if confidence is not None:
            record["confidence"] = confidence
        if quality_components:
            record["quality_components"] = quality_components
        if missing_keywords:
            record["missing_keywords"] = missing_keywords

        min_conf = entry.get("min_confidence")
        if min_conf is not None and confidence is not None:
            try:
                threshold = float(min_conf)
            except (TypeError, ValueError):
                threshold = None
            if threshold is not None:
                record["quality_gate"] = {
                    "threshold": threshold,
                    "passed": confidence >= threshold,
                }
        if include_text and text:
            record["text"] = text
        if error_message:
            record["error"] = error_message

        if not quiet:
            status = "OK" if success else "FAIL"
            print(
                f"[{sample_id}] {status} len={record['text_length']} conf={record.get('confidence', 'n/a')} time={duration}s",
                file=sys.stderr,
            )

        results.append(record)

    return results


def write_results(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "samples": records,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    spec_path = (REPO_ROOT / args.spec).resolve()
    output_path = (REPO_ROOT / args.output).resolve()

    samples = load_sample_spec(spec_path)
    records = run_samples(samples, include_text=args.include_text, quiet=args.quiet)
    write_results(output_path, records)


if __name__ == "__main__":
    main()
