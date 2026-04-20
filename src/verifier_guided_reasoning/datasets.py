from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from .arithmetic import ArithmeticTraceVerifier
from .schemas import QualityGateResult, StepRecord, TraceRecord

_GSM8K_STEP_PATTERN = re.compile(r"<<\s*(?P<expression>[^=<>]+)=(?P<result>[^<>]+)\s*>>")
_CALC_TAG_PATTERN = re.compile(r"<(?P<tag>gadget|output|result)>(?P<value>.*?)</(?P=tag)>")


def parse_gsm8k_answer(answer: str) -> tuple[list[StepRecord], str | None]:
    steps: list[StepRecord] = []
    final_answer: str | None = None

    for index, raw_line in enumerate(answer.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("####"):
            final_answer = line.replace("####", "", 1).strip()
            continue
        match = _GSM8K_STEP_PATTERN.search(line)
        if match:
            expression = match.group("expression").strip()
            result = match.group("result").strip()
            text = _GSM8K_STEP_PATTERN.sub(result, line).strip()
            steps.append(
                StepRecord(
                    step_id=f"s{index}",
                    text=text,
                    operation="arithmetic",
                    expression=expression,
                    computed_value=result,
                    depends_on=[],
                )
            )
        else:
            steps.append(
                StepRecord(
                    step_id=f"s{index}",
                    text=line,
                    operation="explanation",
                    expression=None,
                    computed_value=None,
                    depends_on=[],
                )
            )
    return steps, final_answer


def normalize_gsm8k_record(row: dict[str, Any], split: str = "train") -> TraceRecord:
    question = row.get("question", "").strip()
    answer = row.get("answer", "").strip()
    steps, final_answer = parse_gsm8k_answer(answer)
    gold_answer = final_answer
    return TraceRecord(
        sample_id=str(row.get("sample_id") or row.get("id") or hash(question)),
        source_dataset="openai/gsm8k",
        question=question,
        steps=steps,
        final_answer=final_answer,
        gold_answer=gold_answer,
        split=split,
        metadata={"source_format": "gsm8k"},
    )


def parse_calc_svamp_chain(chain: str) -> tuple[list[StepRecord], str | None]:
    matches = list(_CALC_TAG_PATTERN.finditer(chain))
    steps: list[StepRecord] = []
    final_answer: str | None = None
    gadget_expression: str | None = None

    step_number = 1
    for match in matches:
        tag = match.group("tag")
        value = match.group("value").strip()
        if tag == "gadget":
            gadget_expression = value
        elif tag == "output":
            steps.append(
                StepRecord(
                    step_id=f"s{step_number}",
                    text=f"Compute {gadget_expression} -> {value}",
                    operation="calculator",
                    expression=gadget_expression,
                    computed_value=value,
                    depends_on=[],
                )
            )
            step_number += 1
        elif tag == "result":
            final_answer = value
    return steps, final_answer


def normalize_calc_svamp_record(row: dict[str, Any], split: str = "train") -> TraceRecord:
    question = row.get("question", "").strip()
    chain = row.get("chain", "").strip()
    final_answer = str(row.get("answer") or row.get("result") or "").strip() or None

    steps, chain_final = parse_calc_svamp_chain(chain)
    gold_answer = final_answer or chain_final

    return TraceRecord(
        sample_id=str(row.get("sample_id") or row.get("id") or hash(question)),
        source_dataset="MU-NLPC/Calc-svamp",
        question=question,
        steps=steps or [
            StepRecord(
                step_id="s1",
                text="No parseable chain found in source row.",
                operation="missing_chain",
                expression=None,
                computed_value=None,
                depends_on=[],
            )
        ],
        final_answer=gold_answer,
        gold_answer=gold_answer,
        split=split,
        metadata={"source_format": "calc_svamp", "equation": row.get("equation")},
    )


def gate_trace_record(trace: TraceRecord, verifier: ArithmeticTraceVerifier | None = None) -> QualityGateResult:
    verifier = verifier or ArithmeticTraceVerifier()
    reasons: list[str] = []

    try:
        trace.validate()
        schema_valid = True
    except Exception as exc:
        return QualityGateResult(
            sample_id=getattr(trace, "sample_id", "unknown"),
            schema_valid=False,
            verifier_agreement=False,
            accepted=False,
            reasons=[str(exc)],
        )

    verifier_results = verifier.verify(trace)
    failures = [result for result in verifier_results if result.status == "fail"]
    verifier_agreement = not failures
    if failures:
        reasons.extend(result.error_type or "unknown_error" for result in failures)

    return QualityGateResult(
        sample_id=trace.sample_id,
        schema_valid=schema_valid,
        verifier_agreement=verifier_agreement,
        accepted=schema_valid and verifier_agreement,
        reasons=reasons,
    )


def write_jsonl(records: Iterable[dict[str, Any]], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True))
            handle.write("\n")


def read_trace_jsonl(input_path: str | Path) -> list[TraceRecord]:
    traces: list[TraceRecord] = []
    with Path(input_path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            traces.append(TraceRecord.from_dict(json.loads(line)))
    return traces


def build_demo_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": "demo-good-1",
            "question": "A baker makes 12 muffins in the morning and 8 muffins in the afternoon. How many muffins does the baker make in total?",
            "answer": "The baker makes 12 + 8 = <<12+8=20>>20 muffins in total.\n#### 20",
        },
        {
            "id": "demo-bad-1",
            "question": "Maya saves $10 on Monday and $5 on Tuesday. How much money has Maya saved in total?",
            "answer": "Maya saves 10 - 5 = <<10-5=15>>15 dollars.\n#### 15",
        },
    ]
