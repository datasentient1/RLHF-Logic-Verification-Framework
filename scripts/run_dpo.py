#!/usr/bin/env python3
"""Run DPO training on verifier-derived preference pairs."""

import argparse
import json
from pathlib import Path

from verifier_guided_reasoning.preferences import PreferencePair
from verifier_guided_reasoning.training import DPOConfig, run_dpo_training


def main():
    parser = argparse.ArgumentParser(description="Run DPO training")
    parser.add_argument("--pairs-file", type=Path, required=True, help="Preference pairs JSONL file")
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct", help="Base model to fine-tune")
    parser.add_argument("--output-dir", type=Path, default="artifacts/models/dpo", help="Output directory")
    parser.add_argument("--num-epochs", type=float, default=1.0, help="Number of training epochs")
    parser.add_argument("--learning-rate", type=float, default=5e-7, help="Learning rate")
    parser.add_argument("--batch-size", type=int, default=2, help="Batch size")
    parser.add_argument("--beta", type=float, default=0.1, help="DPO beta parameter")
    parser.add_argument("--tracker-root", default="mlruns", help="MLflow tracker root")

    args = parser.parse_args()

    # Load preference pairs
    pairs = []
    with open(args.pairs_file) as f:
        for line in f:
            data = json.loads(line.strip())
            pairs.append(PreferencePair.from_dict(data))

    # Convert to dict format for training
    pair_dicts = [pair.to_dict() for pair in pairs]

    # Configure DPO
    config = DPOConfig(
        model_name=args.model,
        output_dir=str(args.output_dir),
        num_train_epochs=args.num_epochs,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        beta=args.beta,
    )

    # Run training
    result = run_dpo_training(pair_dicts, config, tracker_root=args.tracker_root)

    print("DPO training completed:")
    print(f"  Model: {result['model_name']}")
    print(f"  Pairs: {result['num_pairs']}")
    print(f"  Output: {result['output_dir']}")
    print(f"  Metrics: {result['train_metrics']}")


if __name__ == "__main__":
    main()