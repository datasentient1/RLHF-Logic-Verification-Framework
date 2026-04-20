from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from verifier_guided_reasoning.pipeline import run_small_demo


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the verifier-guided arithmetic demo.")
    parser.add_argument("--input", help="Optional trace JSONL input file.")
    parser.add_argument("--output", default="artifacts/eval/demo_summary.json", help="JSON summary output path.")
    parser.add_argument("--report-md", default="artifacts/eval/demo_report.md", help="Markdown report output path.")
    parser.add_argument("--tracker-root", default="mlruns", help="MLflow or local tracker root.")
    args = parser.parse_args()

    run_small_demo(
        input_path=args.input,
        output_path=args.output,
        report_markdown_path=args.report_md,
        tracker_root=args.tracker_root,
    )


if __name__ == "__main__":
    main()
