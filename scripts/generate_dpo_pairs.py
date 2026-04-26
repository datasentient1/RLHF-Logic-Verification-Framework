#!/usr/bin/env python3
"""Generate preference pairs from verifier-scored candidates for DPO training."""

import argparse
import json
from pathlib import Path

from verifier_guided_reasoning.datasets import load_gsm8k_subset
from verifier_guided_reasoning.generation import generate_candidates, GenerationConfig
from verifier_guided_reasoning.preferences import mine_preference_pairs


def main():
    parser = argparse.ArgumentParser(description="Generate DPO preference pairs")
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct", help="Model for candidate generation")
    parser.add_argument("--num-candidates", type=int, default=4, help="Candidates per prompt")
    parser.add_argument("--num-prompts", type=int, default=100, help="Number of prompts to process")
    parser.add_argument("--min-margin", type=float, default=0.2, help="Minimum verifier margin for pairs")
    parser.add_argument("--output", type=Path, default="data/processed/dpo_pairs.jsonl", help="Output file")
    parser.add_argument("--tracker-root", default="mlruns", help="MLflow tracker root")

    args = parser.parse_args()

    # Load prompts
    prompts = load_gsm8k_subset(num_samples=args.num_prompts)

    # Generate candidates
    config = GenerationConfig(
        model_name=args.model,
        num_candidates=args.num_candidates,
    )

    all_candidates = []
    for prompt_data in prompts:
        candidates = generate_candidates(
            prompts=[prompt_data["question"]],
            config=config,
            tracker_root=args.tracker_root,
        )
        all_candidates.extend(candidates)

    # Group by prompt
    prompt_groups = {}
    for cand in all_candidates:
        prompt_groups.setdefault(cand.prompt, []).append((cand.trace, cand.verifier_score))

    # Mine preference pairs
    pairs = mine_preference_pairs(prompt_groups.values(), min_margin=args.min_margin)

    # Save pairs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        for pair in pairs:
            f.write(json.dumps(pair.to_dict()) + "\n")

    print(f"Generated {len(pairs)} preference pairs from {len(prompt_groups)} prompts")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()