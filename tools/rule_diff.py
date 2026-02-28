"""Compare Stage 2/3 YAML rule files and emit a structured diff report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover - safety guard
    raise SystemExit("PyYAML is required to run tools/rule_diff.py") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate rule diff summaries for Stage 2/3 YAML files")
    parser.add_argument("--stage2-base", dest="stage2_base", help="Baseline Stage 2 YAML path", default=None)
    parser.add_argument("--stage2-compare", dest="stage2_compare", help="Comparison Stage 2 YAML path", default=None)
    parser.add_argument("--stage3-base", dest="stage3_base", help="Baseline Stage 3 YAML path", default=None)
    parser.add_argument("--stage3-compare", dest="stage3_compare", help="Comparison Stage 3 YAML path", default=None)
    parser.add_argument("--output", dest="output", default="reports/rule_diff_report.json", help="Where to write the diff report")
    return parser.parse_args()


def load_yaml(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    yaml_path = Path(path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"Cannot read YAML file: {yaml_path}")
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    return data or {}


def flatten(prefix: str, value: Any, accumulator: Dict[str, Any]) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            flatten(next_prefix, nested, accumulator)
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            next_prefix = f"{prefix}[{index}]"
            flatten(next_prefix, nested, accumulator)
        return
    accumulator[prefix] = value


def summarize_changes(base: dict[str, Any] | None, target: dict[str, Any] | None) -> dict[str, Any]:
    if base is None or target is None:
        return {"skipped": True, "reason": "Missing base or comparison file"}

    flat_base: Dict[str, Any] = {}
    flat_target: Dict[str, Any] = {}
    flatten("", base, flat_base)
    flatten("", target, flat_target)

    base_keys = set(flat_base)
    target_keys = set(flat_target)

    added = sorted(target_keys - base_keys)
    removed = sorted(base_keys - target_keys)
    modified = sorted(key for key in base_keys & target_keys if flat_base[key] != flat_target[key])

    summary = {
        "added": added,
        "removed": removed,
        "modified": [
            {
                "key": key,
                "base": flat_base[key],
                "target": flat_target[key],
            }
            for key in modified
        ],
        "counts": {
            "added": len(added),
            "removed": len(removed),
            "modified": len(modified),
        },
    }
    return summary


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "stage2": summarize_changes(load_yaml(args.stage2_base), load_yaml(args.stage2_compare)),
        "stage3": summarize_changes(load_yaml(args.stage3_base), load_yaml(args.stage3_compare)),
    }

    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rule diff report written to {output_path}")


if __name__ == "__main__":
    main()
