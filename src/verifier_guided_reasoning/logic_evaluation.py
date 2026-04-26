from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Iterable

from .logic import LogicTraceVerifier
from .schemas import TraceRecord, VerifierResult


def summarize_logic_results(results: Iterable[VerifierResult]) -> dict[str, object]:
    result_list = list(results)
    statuses = Counter(result.status for result in result_list)
    errors = Counter(result.error_type for result in result_list if result.error_type)
    pass_rate = mean(result.score for result in result_list) if result_list else 0.0
    return {
        "num_results": len(result_list),
        "status_counts": dict(statuses),
        "error_counts": dict(errors),
        "pass_rate": round(pass_rate, 4),
    }


def summarize_logic_benchmark(traces: Iterable[TraceRecord], verifier: LogicTraceVerifier | None = None) -> dict[str, object]:
    verifier = verifier or LogicTraceVerifier()
    trace_list = list(traces)
    per_trace: list[dict[str, object]] = []
    all_results: list[VerifierResult] = []
    final_passes = 0

    for trace in trace_list:
        results = verifier.verify(trace)
        all_results.extend(results)
        final_result = next(result for result in results if result.step_id == "final")
        if final_result.status == "pass":
            final_passes += 1

        per_trace.append(
            {
                "sample_id": trace.sample_id,
                "source_dataset": trace.source_dataset,
                "final_status": final_result.status,
                "expected_label": final_result.expected,
                "predicted_label": final_result.observed,
                "num_failures": sum(result.status == "fail" for result in results),
                "error_types": [result.error_type for result in results if result.error_type],
            }
        )

    summary = summarize_logic_results(all_results)
    summary["task_type"] = "logic_entailment"
    summary["num_traces"] = len(trace_list)
    summary["logic_label_accuracy"] = round(final_passes / len(trace_list), 4) if trace_list else 0.0
    summary["traces"] = per_trace
    return summary
