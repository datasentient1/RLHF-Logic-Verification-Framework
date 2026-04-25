from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .generation import GeneratedCandidate
from .preferences import build_preference_pair
from .schemas import PreferencePair, ReviewRecord, TraceRecord

_DEFAULT_ACCEPTED_ACTIONS = {"accept", "accepted", "correct", "fix"}
_DEFAULT_REJECTED_ACTIONS = {"reject", "rejected"}


def build_review_record(candidate: GeneratedCandidate, model_name: str, split: str) -> ReviewRecord:
    """Convert one generated candidate into a review-ready record."""

    record = ReviewRecord(
        review_id=f"{candidate.prompt_id}:{candidate.candidate_id}",
        prompt_id=candidate.prompt_id,
        prompt=candidate.prompt,
        source_dataset=candidate.trace.source_dataset,
        split=split,
        model_name=model_name,
        candidate_id=candidate.candidate_id,
        raw_output=candidate.raw_output,
        trace=candidate.trace.to_dict(),
        verifier_results=[result.to_dict() for result in candidate.verifier_results],
        verifier_pass=candidate.verifier_pass,
        verifier_score=candidate.verifier_score,
        metadata={"gold_answer": candidate.gold_answer},
    )
    record.validate()
    return record


def build_review_records(
    candidates: Iterable[GeneratedCandidate],
    model_name: str,
    split: str = "train",
) -> list[ReviewRecord]:
    return [build_review_record(candidate, model_name=model_name, split=split) for candidate in candidates]


def write_review_jsonl(records: Iterable[ReviewRecord], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=True))
            handle.write("\n")


def read_review_jsonl(input_path: str | Path) -> list[ReviewRecord]:
    records: list[ReviewRecord] = []
    with Path(input_path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            records.append(ReviewRecord.from_dict(json.loads(line)))
    return records


def summarize_review_metrics(
    records: Iterable[ReviewRecord],
    accepted_actions: set[str] | None = None,
    rejected_actions: set[str] | None = None,
) -> dict[str, float]:
    accepted_actions = accepted_actions or _DEFAULT_ACCEPTED_ACTIONS
    rejected_actions = rejected_actions or _DEFAULT_REJECTED_ACTIONS

    review_list = list(records)
    reviewed = [record for record in review_list if record.curator_action]
    accepted = [record for record in reviewed if record.curator_action and record.curator_action.lower() in accepted_actions]
    rejected = [record for record in reviewed if record.curator_action and record.curator_action.lower() in rejected_actions]

    disagreements = 0
    for record in reviewed:
        action = (record.curator_action or "").lower()
        curator_accept = action in accepted_actions
        if curator_accept != record.verifier_pass:
            disagreements += 1

    return {
        "num_candidates": float(len(review_list)),
        "num_reviewed": float(len(reviewed)),
        "acceptance_rate": float(len(accepted) / len(reviewed)) if reviewed else 0.0,
        "rejection_rate": float(len(rejected) / len(reviewed)) if reviewed else 0.0,
        "curator_verifier_disagreement_rate": float(disagreements / len(reviewed)) if reviewed else 0.0,
    }


def export_sft_examples(
    records: Iterable[ReviewRecord],
    accepted_actions: set[str] | None = None,
) -> list[dict[str, Any]]:
    accepted_actions = accepted_actions or _DEFAULT_ACCEPTED_ACTIONS
    exported: list[dict[str, Any]] = []

    for record in records:
        action = (record.curator_action or "").lower()
        if action not in accepted_actions:
            continue
        trace = TraceRecord.from_dict(record.trace)
        exported.append(
            {
                "sample_id": trace.sample_id,
                "question": trace.question,
                "answer": record.raw_output,
                "final_answer": trace.final_answer,
                "gold_answer": trace.gold_answer,
                "steps": [step.to_dict() for step in trace.steps],
                "source": "curated_review",
                "metadata": {
                    "review_id": record.review_id,
                    "model_name": record.model_name,
                    "verifier_score": record.verifier_score,
                    "curator_action": record.curator_action,
                    "curator_score": record.curator_score,
                },
            }
        )
    return exported


def export_preference_pairs(
    records: Iterable[ReviewRecord],
    accepted_actions: set[str] | None = None,
    rejected_actions: set[str] | None = None,
    min_margin: float = 0.0,
) -> list[PreferencePair]:
    accepted_actions = accepted_actions or _DEFAULT_ACCEPTED_ACTIONS
    rejected_actions = rejected_actions or _DEFAULT_REJECTED_ACTIONS

    grouped: dict[str, list[ReviewRecord]] = defaultdict(list)
    for record in records:
        grouped[record.prompt_id].append(record)

    pairs: list[PreferencePair] = []
    for prompt_id_records in grouped.values():
        accepted_records = [
            record
            for record in prompt_id_records
            if record.curator_action and record.curator_action.lower() in accepted_actions
        ]
        rejected_records = [
            record
            for record in prompt_id_records
            if record.curator_action and record.curator_action.lower() in rejected_actions
        ]
        if not accepted_records or not rejected_records:
            continue

        chosen = max(accepted_records, key=lambda record: record.verifier_score)
        rejected = min(rejected_records, key=lambda record: record.verifier_score)
        margin = chosen.verifier_score - rejected.verifier_score
        if margin < min_margin:
            continue

        pair = build_preference_pair(
            prompt=chosen.prompt,
            chosen_trace=TraceRecord.from_dict(chosen.trace),
            rejected_trace=TraceRecord.from_dict(rejected.trace),
            verifier_margin=margin,
            pair_source="curator+verifier",
        )
        pairs.append(pair)

    return pairs
