from verifier_guided_reasoning.arithmetic import ArithmeticTraceVerifier
from verifier_guided_reasoning.schemas import StepRecord, TraceRecord


def _build_trace(step: StepRecord, final_answer: str = "7", gold_answer: str = "7") -> TraceRecord:
    return TraceRecord(
        sample_id="sample-1",
        source_dataset="unit-test",
        question="A shopper buys 4 apples and then buys 3 more apples. How many apples are there in total?",
        steps=[step],
        final_answer=final_answer,
        gold_answer=gold_answer,
        split="test",
        metadata={},
    )


def test_passes_numeric_consistency() -> None:
    verifier = ArithmeticTraceVerifier()
    trace = _build_trace(
        StepRecord(
            step_id="s1",
            text="4 apples + 3 apples = 7 apples",
            operation="add",
            expression="4 + 3",
            computed_value="7",
            depends_on=[],
        )
    )
    results = verifier.verify(trace)
    assert all(result.status == "pass" for result in results)


def test_flags_unit_mismatch() -> None:
    verifier = ArithmeticTraceVerifier()
    trace = _build_trace(
        StepRecord(
            step_id="s1",
            text="4 apples + 3 oranges = 7 apples",
            operation="add",
            expression="4 + 3",
            computed_value="7",
            depends_on=[],
        )
    )
    results = verifier.verify(trace)
    assert results[0].error_type == "unit_mismatch"


def test_flags_sign_error() -> None:
    verifier = ArithmeticTraceVerifier()
    trace = _build_trace(
        StepRecord(
            step_id="s1",
            text="4 apples + 3 apples = 1 apple",
            operation="add",
            expression="4 + 3",
            computed_value="1",
            depends_on=[],
        ),
        final_answer="1",
        gold_answer="7",
    )
    results = verifier.verify(trace)
    assert results[0].error_type in {"numeric_inconsistency", "sign_error"}
    assert results[-1].error_type == "final_answer_mismatch"


def test_detects_skipped_step_without_expression() -> None:
    verifier = ArithmeticTraceVerifier()
    trace = _build_trace(
        StepRecord(
            step_id="s1",
            text="The total is 12 apples.",
            operation="jump",
            expression=None,
            computed_value="12",
            depends_on=[],
        ),
        final_answer="12",
        gold_answer="7",
    )
    results = verifier.verify(trace)
    assert results[0].error_type == "skipped_step"


def test_flags_final_answer_mismatch() -> None:
    verifier = ArithmeticTraceVerifier()
    trace = _build_trace(
        StepRecord(
            step_id="s1",
            text="4 apples + 3 apples = 7 apples",
            operation="add",
            expression="4 + 3",
            computed_value="7",
            depends_on=[],
        ),
        final_answer="8",
        gold_answer="7",
    )
    results = verifier.verify(trace)
    assert results[-1].error_type == "final_answer_mismatch"
