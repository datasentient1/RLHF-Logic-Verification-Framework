#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from verifier_guided_reasoning.datasets import build_demo_rows
from verifier_guided_reasoning.generation import (
    GenerationConfig,
    build_hf_generator,
    build_mock_generator,
    generate_candidates,
)
from verifier_guided_reasoning.review import build_review_records, write_review_jsonl


def _read_prompt_rows(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate verifier-scored review batches from prompts.")
    parser.add_argument("--input", type=str, default=None, help="Input prompt JSONL (id/sample_id + question [+ answer]).")
    parser.add_argument("--output", type=str, required=True, help="Output review JSONL path.")
    parser.add_argument("--model", type=str, default="sshleifer/tiny-gpt2", help="HF model name for generation.")
    parser.add_argument("--num-candidates", type=int, default=3, help="Candidates to generate per prompt.")
    parser.add_argument("--split", type=str, default="train")
    parser.add_argument(
        "--backend",
        type=str,
        choices=["mock", "hf"],
        default="mock",
        help="Generation backend. 'mock' is deterministic and dependency-light.",
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-new-tokens", type=int, default=220)
    args = parser.parse_args()

    rows = _read_prompt_rows(args.input) if args.input else build_demo_rows()

    config = GenerationConfig(
        model_name=args.model,
        num_candidates=args.num_candidates,
        max_new_tokens=args.max_new_tokens,
        seed=args.seed,
    )
    if args.backend == "hf":
        generator = build_hf_generator(config)
    else:
        generator = build_mock_generator()

    candidates = generate_candidates(
        rows=rows,
        generator=generator,
        model_name=config.model_name,
        split=args.split,
    )
    records = build_review_records(candidates, model_name=config.model_name, split=args.split)
    write_review_jsonl(records, args.output)

    print(
        json.dumps(
            {
                "num_prompts": len(rows),
                "num_candidates": len(candidates),
                "output": args.output,
                "backend": args.backend,
                "model": args.model,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
