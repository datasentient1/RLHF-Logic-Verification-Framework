from __future__ import annotations

from pathlib import Path

from .datasets import build_demo_rows, normalize_gsm8k_record, read_trace_jsonl
from .evaluation import summarize_benchmark
from .reporting import write_report_files
from .tracking import ExperimentTracker


def load_demo_traces():
    return [normalize_gsm8k_record(row, split="demo") for row in build_demo_rows()]


def run_small_demo(
    input_path: str | None = None,
    output_path: str | None = None,
    report_markdown_path: str | None = None,
    tracker_root: str = "mlruns",
) -> dict[str, object]:
    traces = read_trace_jsonl(input_path) if input_path else load_demo_traces()
    summary = summarize_benchmark(traces)

    tracker = ExperimentTracker(root_dir=tracker_root, experiment_name="verifier_guided_reasoning_demo")
    with tracker.start_run("small_demo") as run:
        run.log_params(
            {
                "num_traces": len(traces),
                "sources": ",".join(sorted({trace.source_dataset for trace in traces})),
            }
        )
        run.log_metrics(
            {
                "final_accuracy": float(summary["final_accuracy"]),
                "pass_rate": float(summary["pass_rate"]),
            }
        )
        run.log_json("summary.json", summary)

    if output_path:
        write_report_files(summary, output_path, report_markdown_path)

    return summary


def ensure_parent(path: str | None) -> None:
    if path is None:
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
