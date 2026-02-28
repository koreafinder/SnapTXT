"""Utility to compute basic OCR quality metrics from saved experiment artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, List


@dataclass(slots=True)
class SampleMetrics:
    success: bool
    confidence: float | None
    text_length: int | None
    processing_time: float | None
    tags: tuple[str, ...] = ()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate OCR quality metrics and emit a JSON report",
    )
    parser.add_argument(
        "--samples",
        default="experiments/results/ocr_test_results.json",
        help="Path to a JSON/JSONL file that stores experiment output",
    )
    parser.add_argument(
        "--output",
        default="reports/quality_suite_report.json",
        help="Destination path for the aggregated JSON report",
    )
    parser.add_argument(
        "--min-quality",
        type=float,
        default=None,
        help="Optional gate: fail the run when the overall quality score is below this value",
    )
    parser.add_argument(
        "--tag-threshold",
        action="append",
        default=None,
        help="Optional per-tag gates in the form tag=value (e.g., --tag-threshold article=0.9)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress human-readable summary output",
    )
    return parser.parse_args()


def parse_tag_thresholds(entries: List[str] | None) -> dict[str, float]:
    thresholds: dict[str, float] = {}
    if not entries:
        return thresholds
    for entry in entries:
        if not entry:
            continue
        if "=" not in entry:
            raise ValueError(f"Invalid tag threshold '{entry}'. Use tag=value format.")
        tag, value = entry.split("=", 1)
        tag = tag.strip()
        try:
            thresholds[tag] = float(value)
        except ValueError as exc:  # pragma: no cover
            raise ValueError(f"Invalid threshold value for tag '{tag}': {value}") from exc
    return thresholds


def load_samples(path: Path) -> list[Any]:
    if not path.exists():
        raise FileNotFoundError(f"Samples file not found: {path}")

    raw_text = path.read_text(encoding="utf-8").strip()
    if not raw_text:
        raise ValueError(f"Samples file is empty: {path}")

    data: Any
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        data = [json.loads(line) for line in raw_text.splitlines() if line.strip()]

    if isinstance(data, dict):
        if "detailed_results" in data:
            return list(data["detailed_results"])
        if "samples" in data:
            return list(data["samples"])
    if isinstance(data, list):
        return list(data)

    raise ValueError("Unsupported samples payload. Expecting list, JSONL, or dict with 'detailed_results'/'samples'.")


def normalize_confidence(value: float | None) -> float | None:
    if value is None:
        return None
    if value > 1.0:
        # Treat as percentage when detector emits 0-100 range
        value = value / 100.0
    return max(0.0, min(1.0, value))


def extract_metrics(record: Any) -> SampleMetrics:
    success = record.get("success") if isinstance(record, dict) else None
    confidence: float | None = record.get("confidence") if isinstance(record, dict) else None
    text_length: int | None = record.get("text_length") if isinstance(record, dict) else None
    processing_time: float | None = record.get("processing_time") if isinstance(record, dict) else None
    tags: tuple[str, ...] = ()

    if isinstance(record, dict) and "ultimate" in record:
        ultimate = record["ultimate"] or {}
        success = ultimate.get("success") if success is None else success
        confidence = ultimate.get("confidence") if confidence is None else confidence
        if text_length is None:
            text_length = ultimate.get("text_length")
            if text_length is None and ultimate.get("text"):
                text_length = len(ultimate["text"])
        processing_time = ultimate.get("processing_time") if processing_time is None else processing_time

    if text_length is None and isinstance(record, dict) and record.get("text"):
        text_length = len(record["text"])

    if isinstance(record, dict) and record.get("tags"):
        raw_tags = record.get("tags")
        if isinstance(raw_tags, (list, tuple)):
            tags = tuple(str(tag) for tag in raw_tags if isinstance(tag, str) and tag.strip())

    return SampleMetrics(
        success=bool(success),
        confidence=confidence if confidence is not None else None,
        text_length=text_length,
        processing_time=processing_time,
        tags=tags,
    )


def summarize_samples(samples: List[SampleMetrics]) -> dict[str, Any]:
    if not samples:
        raise ValueError("No samples detected; unable to compute quality metrics.")

    success_count = sum(1 for sample in samples if sample.success)
    success_rate = success_count / len(samples)

    confidence_values = [normalize_confidence(sample.confidence) for sample in samples if sample.confidence is not None]
    confidence_values = [value for value in confidence_values if value is not None]
    avg_confidence = mean(confidence_values) if confidence_values else 0.0

    text_lengths = [sample.text_length for sample in samples if sample.text_length is not None]
    avg_text_length = mean(text_lengths) if text_lengths else 0.0

    durations = [sample.processing_time for sample in samples if sample.processing_time is not None]
    avg_processing_time = mean(durations) if durations else 0.0

    overall_quality = round((success_rate + avg_confidence) / 2, 3)

    return {
        "samples": len(samples),
        "success_rate": round(success_rate, 3),
        "average_confidence": round(avg_confidence, 3),
        "average_text_length": round(avg_text_length, 1),
        "average_processing_time": round(avg_processing_time, 3),
        "overall_quality": overall_quality,
        "success_count": success_count,
        "failure_count": len(samples) - success_count,
    }


def aggregate_metrics(records: Iterable[SampleMetrics], tag_thresholds: dict[str, float]) -> dict[str, Any]:
    samples: List[SampleMetrics] = list(records)
    if not samples:
        raise ValueError("No samples detected; unable to compute quality metrics.")

    timestamp = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    overall_summary = summarize_samples(samples)
    overall_summary["timestamp"] = timestamp

    tag_buckets: dict[str, List[SampleMetrics]] = {}
    for sample in samples:
        for tag in sample.tags:
            tag_buckets.setdefault(tag, []).append(sample)

    tag_summaries: dict[str, Any] = {
        tag: summarize_samples(bucket)
        for tag, bucket in sorted(tag_buckets.items())
    }

    if tag_summaries:
        overall_summary["tag_summaries"] = tag_summaries

    if tag_thresholds:
        tag_gates: dict[str, dict[str, Any]] = {}
        for tag, threshold in tag_thresholds.items():
            summary = tag_summaries.get(tag)
            if not summary:
                tag_gates[tag] = {
                    "threshold": threshold,
                    "passed": False,
                    "reason": "no-samples",
                }
                continue
            tag_gates[tag] = {
                "threshold": threshold,
                "passed": summary["overall_quality"] >= threshold,
                "observed": summary["overall_quality"],
            }
        overall_summary["tag_quality_gates"] = tag_gates

    return overall_summary


def main() -> None:
    args = parse_args()
    samples_path = Path(args.samples)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records = load_samples(samples_path)
    tag_thresholds = parse_tag_thresholds(args.tag_threshold)
    metrics = aggregate_metrics((extract_metrics(record) for record in records), tag_thresholds=tag_thresholds)
    metrics["source"] = str(samples_path)

    if args.min_quality is not None and metrics["overall_quality"] < args.min_quality:
        metrics["quality_gate"] = {
            "threshold": args.min_quality,
            "passed": False,
        }
    elif args.min_quality is not None:
        metrics["quality_gate"] = {
            "threshold": args.min_quality,
            "passed": True,
        }

    output_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    if not args.quiet:
        print(f"Quality Suite Summary\n  Samples: {metrics['samples']}\n  Success Rate: {metrics['success_rate']:.3f}\n  Avg Confidence: {metrics['average_confidence']:.3f}\n  Overall Quality: {metrics['overall_quality']:.3f}")
        if "quality_gate" in metrics:
            gate = metrics["quality_gate"]
            state = "PASSED" if gate["passed"] else "FAILED"
            print(f"  Quality Gate: {state} (threshold={gate['threshold']})")

    any_failed = args.min_quality is not None and metrics["quality_gate"]["passed"] is False

    if "tag_quality_gates" in metrics:
        for info in metrics["tag_quality_gates"].values():
            if info.get("passed") is False:
                any_failed = True

    if any_failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
