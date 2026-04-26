#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from verifier_guided_reasoning.publishing import build_artifact_manifest, reproducibility_gate, write_dataset_card


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a dataset card with artifact hashes and release notes.")
    parser.add_argument("--output", required=True, help="Output markdown path for the dataset card.")
    parser.add_argument("--title", default="Verifier-Guided Curated Arithmetic + Logic Dataset")
    parser.add_argument("--overview", required=True, help="Short overview paragraph for the dataset card.")
    parser.add_argument("--metrics", default="{}", help="JSON object string of metrics.")
    parser.add_argument("--artifact", action="append", default=[], help="Artifact path to include. Repeat for multiple.")
    parser.add_argument("--note", action="append", default=[], help="Release note bullet. Repeat for multiple.")
    args = parser.parse_args()

    try:
        metrics = json.loads(args.metrics)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid --metrics JSON: {exc}")

    manifest = build_artifact_manifest(args.artifact)
    passed, issues = reproducibility_gate(manifest)

    notes = list(args.note)
    if passed:
        notes.insert(0, "Reproducibility gate passed: all required artifacts exist and have hashes.")
    else:
        notes.insert(0, "Reproducibility gate failed: fix missing/empty artifacts before publication.")
        notes.extend(issues)

    output = write_dataset_card(
        output_path=args.output,
        title=args.title,
        overview=args.overview,
        metrics={str(k): float(v) if isinstance(v, (int, float)) else v for k, v in metrics.items()},
        manifest=manifest,
        release_notes=notes,
    )

    print(json.dumps({"output": str(output), "reproducible": passed, "issues": issues}, indent=2))


if __name__ == "__main__":
    main()
