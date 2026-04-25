#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from verifier_guided_reasoning.training import SFTConfig, run_sft_training


def _read_jsonl(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small SFT training pass on curated examples.")
    parser.add_argument("--input", type=str, required=True, help="SFT JSONL created by export_curated_dataset.py")
    parser.add_argument("--model", type=str, required=True, help="Base model name, e.g. Qwen/Qwen2.5-0.5B")
    parser.add_argument("--output-dir", type=str, required=True)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=384)
    parser.add_argument("--tracker-root", type=str, default="mlruns")
    args = parser.parse_args()

    examples = _read_jsonl(args.input)
    config = SFTConfig(
        model_name=args.model,
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        max_length=args.max_length,
    )
    result = run_sft_training(examples=examples, config=config, tracker_root=args.tracker_root)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
