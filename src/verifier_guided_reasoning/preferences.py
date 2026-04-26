from __future__ import annotations

from typing import Iterable

from .schemas import PreferencePair, TraceRecord


def build_preference_pair(
    prompt: str,
    chosen_trace: TraceRecord,
    rejected_trace: TraceRecord,
    verifier_margin: float,
    pair_source: str = "verifier_margin",
) -> PreferencePair:
    pair = PreferencePair(
        prompt=prompt,
        chosen_trace=chosen_trace.to_dict(),
        rejected_trace=rejected_trace.to_dict(),
        pair_source=pair_source,
        verifier_margin=verifier_margin,
    )
    pair.validate()
    return pair


def build_preference_pair_from_responses(
    prompt: str,
    chosen_response: str,
    rejected_response: str,
    pair_source: str = "user_selected",
) -> PreferencePair:
    """Build a preference pair from raw response strings (for dataset pairs)."""
    # Create minimal trace records from responses
    chosen_trace = TraceRecord(
        sample_id=f"user_chosen_{hash(chosen_response)}",
        source_dataset="user_selected",
        question=prompt,
        steps=[],
        final_answer=chosen_response,
        gold_answer=None,
        split="train",
        metadata={"response": chosen_response},
    )
    
    rejected_trace = TraceRecord(
        sample_id=f"user_rejected_{hash(rejected_response)}",
        source_dataset="user_selected",
        question=prompt,
        steps=[],
        final_answer=rejected_response,
        gold_answer=None,
        split="train",
        metadata={"response": rejected_response},
    )
    
    return build_preference_pair(
        prompt=prompt,
        chosen_trace=chosen_trace,
        rejected_trace=rejected_trace,
        verifier_margin=0.0,  # No verifier margin for user selections
        pair_source=pair_source,
    )


def mine_preference_pairs(
    candidate_groups: Iterable[list[tuple[TraceRecord, float]]],
    min_margin: float = 0.2,
) -> list[PreferencePair]:
    pairs: list[PreferencePair] = []
    for group in candidate_groups:
        if len(group) < 2:
            continue
        sorted_group = sorted(group, key=lambda item: item[1], reverse=True)
        chosen_trace, chosen_score = sorted_group[0]
        rejected_trace, rejected_score = sorted_group[-1]
        margin = chosen_score - rejected_score
        if margin < min_margin:
            continue
        pairs.append(
            build_preference_pair(
                prompt=chosen_trace.question,
                chosen_trace=chosen_trace,
                rejected_trace=rejected_trace,
                verifier_margin=margin,
            )
        )
    return pairs
