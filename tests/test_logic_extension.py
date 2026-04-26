from verifier_guided_reasoning.datasets import build_logic_demo_rows, normalize_folio_record
from verifier_guided_reasoning.logic import LogicTraceVerifier, infer_logic_label
from verifier_guided_reasoning.logic_evaluation import summarize_logic_benchmark


def test_infer_logic_label_forward_chaining_entailment() -> None:
    label = infer_logic_label(
        premises=["if alex studies then alex passes", "alex studies"],
        hypothesis="alex passes",
    )
    assert label == "entailment"


def test_logic_trace_verifier_flags_mismatch() -> None:
    trace = normalize_folio_record(
        {
            "id": "logic-mismatch",
            "premises": ["if alex studies then alex passes", "alex studies"],
            "hypothesis": "alex passes",
            "label": "entailment",
            "prediction": "contradiction",
        },
        split="test",
    )
    results = LogicTraceVerifier().verify(trace)
    assert results[0].error_type == "logic_label_mismatch"
    assert results[-1].error_type == "final_answer_mismatch"


def test_summarize_logic_benchmark_outputs_accuracy() -> None:
    traces = [normalize_folio_record(row, split="demo") for row in build_logic_demo_rows()]
    summary = summarize_logic_benchmark(traces)
    assert summary["task_type"] == "logic_entailment"
    assert summary["num_traces"] == 3
    assert 0.0 <= summary["logic_label_accuracy"] <= 1.0
