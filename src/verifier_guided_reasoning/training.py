from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .tracking import ExperimentTracker


@dataclass(slots=True)
class SFTConfig:
    """Minimal SFT configuration for small-model Colab runs."""

    model_name: str
    output_dir: str
    max_length: int = 384
    num_train_epochs: float = 1.0
    learning_rate: float = 2e-5
    per_device_train_batch_size: int = 2


def _format_sft_text(row: dict[str, Any]) -> str:
    question = str(row.get("question", "")).strip()
    answer = str(row.get("answer", "")).strip()
    return f"Question: {question}\nAnswer:\n{answer}".strip()


def run_sft_training(
    examples: list[dict[str, Any]],
    config: SFTConfig,
    tracker_root: str = "mlruns",
) -> dict[str, Any]:
    """Run a small causal-LM SFT pass on curated examples."""

    if not examples:
        raise ValueError("No SFT examples were provided.")

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
    except ImportError as exc:
        raise ImportError(
            "transformers and torch are required for run_sft_training. Install with the 'colab' extra."
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(config.model_name)

    texts = [_format_sft_text(example) for example in examples]
    encoded = tokenizer(
        texts,
        padding="max_length",
        truncation=True,
        max_length=config.max_length,
        return_tensors="pt",
    )

    class _TensorDataset(torch.utils.data.Dataset):
        def __len__(self) -> int:
            return int(encoded["input_ids"].shape[0])

        def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
            item = {key: value[idx] for key, value in encoded.items()}
            item["labels"] = item["input_ids"].clone()
            return item

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=config.num_train_epochs,
        learning_rate=config.learning_rate,
        per_device_train_batch_size=config.per_device_train_batch_size,
        logging_steps=5,
        save_strategy="no",
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=_TensorDataset(),
        tokenizer=tokenizer,
    )

    train_result = trainer.train()
    metrics = train_result.metrics

    tracker = ExperimentTracker(root_dir=tracker_root, experiment_name="verifier_guided_reasoning_sft")
    with tracker.start_run("sft_curated") as run:
        run.log_params(
            {
                "model_name": config.model_name,
                "num_examples": len(examples),
                "max_length": config.max_length,
                "num_train_epochs": config.num_train_epochs,
                "learning_rate": config.learning_rate,
                "per_device_train_batch_size": config.per_device_train_batch_size,
            }
        )
        run.log_metrics(
            {key: float(value) for key, value in metrics.items() if isinstance(value, (int, float))}
        )

    trainer.save_model(str(output_dir / "model"))
    tokenizer.save_pretrained(str(output_dir / "model"))

    return {
        "num_examples": len(examples),
        "model_name": config.model_name,
        "output_dir": str(output_dir),
        "train_metrics": {key: float(value) for key, value in metrics.items() if isinstance(value, (int, float))},
    }
