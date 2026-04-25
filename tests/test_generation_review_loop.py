from verifier_guided_reasoning.generation import build_mock_generator, generate_candidates
from verifier_guided_reasoning.review import (
    build_review_records,
    export_preference_pairs,
    export_sft_examples,
    summarize_review_metrics,
)


def test_generation_builds_candidates_with_verifier_scores() -> None:
    rows = [
        {
            "id": "q1",
            "question": "Lena has 1 marble and gets 1 more. How many marbles now?",
            "answer": "2",
        }
    ]

    candidates = generate_candidates(
        rows=rows,
        generator=build_mock_generator(),
        model_name="mock-model",
        split="train",
    )

    assert len(candidates) == 3
    assert candidates[0].candidate_id == "q1-c1"
    assert all(candidate.trace.sample_id == "q1" for candidate in candidates)


def test_review_export_creates_sft_examples_and_preference_pairs() -> None:
    rows = [
        {
            "id": "q1",
            "question": "Lena has 1 marble and gets 1 more. How many marbles now?",
            "answer": "2",
        }
    ]
    candidates = generate_candidates(
        rows=rows,
        generator=build_mock_generator(),
        model_name="mock-model",
        split="train",
    )
    reviews = build_review_records(candidates, model_name="mock-model", split="train")

    reviews[0].curator_action = "accept"
    reviews[1].curator_action = "reject"
    reviews[2].curator_action = "reject"

    sft_examples = export_sft_examples(reviews)
    preference_pairs = export_preference_pairs(reviews, min_margin=0.0)
    metrics = summarize_review_metrics(reviews)

    assert len(sft_examples) == 1
    assert sft_examples[0]["metadata"]["curator_action"] == "accept"

    assert len(preference_pairs) == 1
    assert preference_pairs[0].prompt == reviews[0].prompt

    assert metrics["num_reviewed"] == 3.0
    assert metrics["acceptance_rate"] == 1 / 3
