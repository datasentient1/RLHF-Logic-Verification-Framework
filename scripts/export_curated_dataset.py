#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from verifier_guided_reasoning.datasets import write_jsonl
from verifier_guided_reasoning.review import (
    export_preference_pairs,
    export_sft_examples,
    read_review_jsonl,
    summarize_review_metrics,
)


def _parse_actions(raw: str) -> set[str]:
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export curated SFT and preference datasets from reviewed candidates.")
    parser.add_argument("--input", type=str, required=True, help="Annotated review JSONL path.")
    parser.add_argument("--sft-output", type=str, required=True, help="Output JSONL for accepted SFT examples.")
    parser.add_argument("--preference-output", type=str, required=True, help="Output JSONL for chosen/rejected pairs.")
    parser.add_argument("--metrics-output", type=str, default=None, help="Optional JSON metrics output path.")
    parser.add_argument("--accepted-actions", type=str, default="accept,correct,fix")
    parser.add_argument("--rejected-actions", type=str, default="reject")
    parser.add_argument("--min-margin", type=float, default=0.0)
    args = parser.parse_args()

    accepted_actions = _parse_actions(args.accepted_actions)
    rejected_actions = _parse_actions(args.rejected_actions)

    records = read_review_jsonl(args.input)
    sft_examples = export_sft_examples(records, accepted_actions=accepted_actions)
    preference_pairs = export_preference_pairs(
        records,
        accepted_actions=accepted_actions,
        rejected_actions=rejected_actions,
        min_margin=args.min_margin,
    )

    write_jsonl(sft_examples, args.sft_output)
    write_jsonl([pair.to_dict() for pair in preference_pairs], args.preference_output)

    metrics = summarize_review_metrics(
        records,
        accepted_actions=accepted_actions,
        rejected_actions=rejected_actions,
    )
    metrics.update(
        {
            "num_sft_examples": float(len(sft_examples)),
            "num_preference_pairs": float(len(preference_pairs)),
        }
    )

    if args.metrics_output:
        with open(args.metrics_output, "w", encoding="utf-8") as handle:
            json.dump(metrics, handle, indent=2)

    print(
        json.dumps(
            {
                "num_review_records": len(records),
                "num_sft_examples": len(sft_examples),
                "num_preference_pairs": len(preference_pairs),
                "sft_output": args.sft_output,
                "preference_output": args.preference_output,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
