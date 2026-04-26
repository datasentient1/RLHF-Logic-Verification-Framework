from __future__ import annotations

import json
from pathlib import Path

from .datasets import build_logic_demo_rows, normalize_folio_record
from .logic_evaluation import summarize_logic_benchmark
from .tracking import ExperimentTracker


def load_logic_demo_traces() -> list:
    return [normalize_folio_record(row, split="demo") for row in build_logic_demo_rows()]


def run_logic_demo(output_path: str | None = None, tracker_root: str = "mlruns") -> dict[str, object]:
    traces = load_logic_demo_traces()
    summary = summarize_logic_benchmark(traces)

    tracker = ExperimentTracker(root_dir=tracker_root, experiment_name="verifier_guided_reasoning_logic_demo")
    with tracker.start_run("logic_demo") as run:
        run.log_params(
            {
                "num_traces": len(traces),
                "sources": ",".join(sorted({trace.source_dataset for trace in traces})),
                "task_type": "logic_entailment",
            }
        )
        run.log_metrics(
            {
                "logic_label_accuracy": float(summary["logic_label_accuracy"]),
                "pass_rate": float(summary["pass_rate"]),
            }
        )
        run.log_json("logic_summary.json", summary)

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return summary
