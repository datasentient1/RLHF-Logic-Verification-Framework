#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from verifier_guided_reasoning.logic_pipeline import run_logic_demo


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the logic-extension verifier demo.")
    parser.add_argument("--output", default="artifacts/eval/logic_summary.json", help="JSON summary output path.")
    parser.add_argument("--tracker-root", default="mlruns", help="MLflow or local tracker root.")
    args = parser.parse_args()

    summary = run_logic_demo(output_path=args.output, tracker_root=args.tracker_root)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
