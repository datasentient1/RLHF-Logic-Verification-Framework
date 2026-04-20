from verifier_guided_reasoning.datasets import gate_trace_record, normalize_calc_svamp_record, normalize_gsm8k_record


def test_normalize_gsm8k_record_extracts_steps_and_final_answer() -> None:
    record = normalize_gsm8k_record(
        {
            "id": "gsm8k-demo",
            "question": "Lena has 3 marbles and finds 2 more. How many marbles does she have?",
            "answer": "Lena has 3 + 2 = <<3+2=5>>5 marbles.\n#### 5",
        },
        split="train",
    )
    assert record.final_answer == "5"
    assert record.steps[0].expression == "3+2"


def test_normalize_calc_svamp_record_extracts_chain() -> None:
    record = normalize_calc_svamp_record(
        {
            "id": "calc-demo",
            "question": "If a class has 10 desks and adds 4 more, how many desks are there?",
            "chain": "<gadget>10 + 4</gadget><output>14</output><result>14</result>",
            "answer": "14",
        },
        split="train",
    )
    assert record.steps[0].expression == "10 + 4"
    assert record.gold_answer == "14"


def test_quality_gate_accepts_consistent_trace() -> None:
    record = normalize_gsm8k_record(
        {
            "id": "good-demo",
            "question": "Lena has 3 marbles and finds 2 more. How many marbles does she have?",
            "answer": "Lena has 3 + 2 = <<3+2=5>>5 marbles.\n#### 5",
        },
        split="train",
    )
    gate = gate_trace_record(record)
    assert gate.schema_valid is True
    assert gate.verifier_agreement is True
    assert gate.accepted is True
